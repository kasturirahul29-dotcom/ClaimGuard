from rest_framework import viewsets, mixins, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend

from common.permissions import IsAdminOrOwner, IsAdminUser
from .models import Policy
from .serializers import (
    PolicySerializer,
    PolicyCreateSerializer,
    PolicyAdminCreateSerializer,
    PolicyActivateSerializer,
)


class PolicyViewSet(
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.ListModelMixin,
    viewsets.GenericViewSet,
):
    """
    Policy CRUD viewset.

    GET  /api/v1/policies/          — list (scoped by role)
    POST /api/v1/policies/          — create
    GET  /api/v1/policies/<id>/     — retrieve (owner or admin)
    PATCH /api/v1/policies/<id>/activate/ — admin only
    """

    permission_classes = [IsAdminOrOwner]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['status', 'policy_type']

    def get_queryset(self):
        """
        Customers see only their own policies.
        Admins see all; filter by ?user_id= optionally.
        The queryset-level filter is the primary access control —
        IsAdminOrOwner.has_object_permission is the secondary guard.
        """
        qs = Policy.objects.select_related('user')
        if self.request.user.role == 'admin':
            user_id = self.request.query_params.get('user_id')
            if user_id:
                qs = qs.filter(user_id=user_id)
            return qs
        return qs.filter(user=self.request.user)

    def get_serializer_class(self):
        if self.action == 'create':
            if self.request.user.role == 'admin':
                return PolicyAdminCreateSerializer
            return PolicyCreateSerializer
        if self.action == 'activate':
            return PolicyActivateSerializer
        return PolicySerializer

    def retrieve(self, request, *args, **kwargs):
        """
        Return 404 (not 403) when a non-owner tries to access a policy.
        Do not reveal that the policy ID exists.
        """
        try:
            instance = self.get_queryset().get(pk=kwargs['pk'])
        except Policy.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        serializer = PolicySerializer(instance, context={'request': request})
        return Response(serializer.data)

    def perform_create(self, serializer):
        if self.request.user.role == 'admin':
            # Admin can specify user; status defaults to pending_activation
            # unless explicitly set in the body
            serializer.save()
        else:
            # Customer: user is always self, status always pending_activation
            serializer.save(user=self.request.user, status=Policy.STATUS_PENDING)

    @action(detail=True, methods=['patch'], permission_classes=[IsAdminUser], url_path='activate')
    def activate(self, request, pk=None):
        """
        PATCH /api/v1/policies/<id>/activate/
        Admin-only: transitions pending_activation → active.
        Returns 400 if the policy is not in pending_activation state.
        """
        try:
            policy = Policy.objects.get(pk=pk)
        except Policy.DoesNotExist:
            return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)

        if policy.status != Policy.STATUS_PENDING:
            return Response(
                {'detail': f"Policy is '{policy.status}', not 'pending_activation'. Cannot activate."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        policy.status = Policy.STATUS_ACTIVE
        policy.save(update_fields=['status'])
        return Response(PolicySerializer(policy, context={'request': request}).data)
