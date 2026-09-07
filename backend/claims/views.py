from rest_framework import viewsets, mixins, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.utils import timezone

from common.permissions import IsAdminOrOwner, IsAdminUser
from common.pagination import StandardResultsPagination
from .models import Claim
from .serializers import (
    ClaimCustomerSerializer,
    ClaimAdminSerializer,
    ClaimCreateSerializer,
    ClaimReviewSerializer,
)
from .services.fraud import check_fraud


class ClaimViewSet(
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.ListModelMixin,
    viewsets.GenericViewSet,
):
    """
    Claim viewset.

    GET  /api/v1/claims/              — list (scoped by role)
    POST /api/v1/claims/              — create (runs validation + fraud check)
    GET  /api/v1/claims/<id>/         — retrieve (owner or admin)
    PATCH /api/v1/claims/<id>/review/ — admin only
    GET  /api/v1/claims/flagged/      — admin only shortcut
    """

    permission_classes = [IsAdminOrOwner]
    pagination_class = StandardResultsPagination
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['status', 'fraud_flag']

    def get_queryset(self):
        """
        Customers: only their own claims.
        Admins: all claims, with optional ?status= and ?fraud_flag= filters.
        """
        qs = Claim.objects.select_related('policy', 'submitted_by', 'reviewed_by')
        if self.request.user.role == 'admin':
            return qs
        return qs.filter(submitted_by=self.request.user)

    def get_serializer_class(self):
        if self.action == 'create':
            return ClaimCreateSerializer
        if self.action == 'review':
            return ClaimReviewSerializer
        # Use admin serializer (includes fraud_reason) for admin users;
        # customer serializer (excludes fraud_reason) for everyone else.
        if self.request.user.role == 'admin':
            return ClaimAdminSerializer
        return ClaimCustomerSerializer

    def retrieve(self, request, *args, **kwargs):
        """Return 404 (not 403) when a non-owner tries to access a claim by ID."""
        try:
            instance = self.get_queryset().get(pk=kwargs['pk'])
        except Claim.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    def perform_create(self, serializer):
        """
        Create a claim:
        1. Save with submitted_by=request.user, status='pending'
        2. Run fraud check on the saved instance
        3. Persist fraud results
        All three steps happen atomically from the client's perspective.
        """
        claim = serializer.save(
            submitted_by=self.request.user,
            status=Claim.STATUS_PENDING,
        )
        # Run the fraud service now that the claim has a date_filed value
        fraud_flag, fraud_reason = check_fraud(claim)
        claim.fraud_flag = fraud_flag
        claim.fraud_reason = fraud_reason or None  # store None not "" when clean
        claim.save(update_fields=['fraud_flag', 'fraud_reason'])

    def create(self, request, *args, **kwargs):
        """
        Override create to return the correct role-aware serializer on 201,
        because perform_create uses ClaimCreateSerializer but the response
        should use the customer/admin read serializer.
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        claim = serializer.instance
        # Re-serialize with the read serializer for the response
        if request.user.role == 'admin':
            read_serializer = ClaimAdminSerializer(claim, context={'request': request})
        else:
            read_serializer = ClaimCustomerSerializer(claim, context={'request': request})
        return Response(read_serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['patch'], permission_classes=[IsAdminUser], url_path='review')
    def review(self, request, pk=None):
        """
        PATCH /api/v1/claims/<id>/review/
        Admin-only: approve or reject a pending claim.
        Returns 400 if the claim is not currently 'pending'.
        Returns 400 if status value is not 'approved' or 'rejected'.
        """
        try:
            claim = Claim.objects.select_related('policy', 'submitted_by').get(pk=pk)
        except Claim.DoesNotExist:
            return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)

        if claim.status != Claim.STATUS_PENDING:
            return Response(
                {'detail': f"Claim is '{claim.status}' and has already been reviewed."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = ClaimReviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        claim.status = serializer.validated_data['status']
        claim.reviewed_by = request.user
        claim.reviewed_at = timezone.now()
        claim.save(update_fields=['status', 'reviewed_by', 'reviewed_at'])

        return Response(ClaimAdminSerializer(claim, context={'request': request}).data)

    @action(detail=False, methods=['get'], permission_classes=[IsAdminUser], url_path='flagged')
    def flagged(self, request):
        """
        GET /api/v1/claims/flagged/
        Admin only: shortcut for fraud_flag=True AND status='pending'.
        """
        qs = Claim.objects.filter(
            fraud_flag=True,
            status=Claim.STATUS_PENDING,
        ).select_related('policy', 'submitted_by', 'reviewed_by')

        page = self.paginate_queryset(qs)
        if page is not None:
            serializer = ClaimAdminSerializer(page, many=True, context={'request': request})
            return self.get_paginated_response(serializer.data)

        serializer = ClaimAdminSerializer(qs, many=True, context={'request': request})
        return Response(serializer.data)
