from rest_framework import serializers
from rest_framework.exceptions import PermissionDenied
from django.utils import timezone
from .models import Claim
from policies.models import Policy


class ClaimCustomerSerializer(serializers.ModelSerializer):
    """
    Customer-facing claim serializer.
    NEVER includes fraud_reason — customers are not told why a claim
    was flagged, only that it was. The field is excluded at the
    serializer level (not via a view filter) so it cannot accidentally
    leak if the serializer is reused elsewhere.
    """

    policy_number = serializers.CharField(source='policy.policy_number', read_only=True)

    class Meta:
        model = Claim
        fields = (
            'id',
            'policy',
            'policy_number',
            'claim_amount',
            'description',
            'date_filed',
            'status',
            'fraud_flag',
            # fraud_reason intentionally excluded
        )
        read_only_fields = (
            'id', 'policy', 'policy_number', 'date_filed',
            'status',         # only set via /review/
            'fraud_flag',     # set by fraud service, never by caller
        )


class ClaimAdminSerializer(serializers.ModelSerializer):
    """
    Admin-facing claim serializer — includes fraud_reason and review metadata.
    """

    policy_number = serializers.CharField(source='policy.policy_number', read_only=True)
    submitted_by_username = serializers.CharField(source='submitted_by.username', read_only=True)
    reviewed_by_username = serializers.SerializerMethodField()

    class Meta:
        model = Claim
        fields = (
            'id',
            'policy',
            'policy_number',
            'submitted_by',
            'submitted_by_username',
            'claim_amount',
            'description',
            'date_filed',
            'status',
            'fraud_flag',
            'fraud_reason',
            'reviewed_by',
            'reviewed_by_username',
            'reviewed_at',
        )
        read_only_fields = (
            'id', 'policy', 'policy_number', 'submitted_by', 'submitted_by_username',
            'date_filed', 'status', 'fraud_flag', 'fraud_reason',
            'reviewed_by', 'reviewed_by_username', 'reviewed_at',
        )

    def get_reviewed_by_username(self, obj):
        return obj.reviewed_by.username if obj.reviewed_by else None


class ClaimCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for POST /api/v1/claims/.
    Runs Phase 3 validation before the fraud check in the view.

    Validation order:
      1. Policy must be active (not pending_activation/expired/cancelled)
      2. claim_amount must not exceed coverage_amount (hard cap)
      3. Submitter must own the policy, unless they are an admin (BOLA check)

    Mass-assignment protection: submitted_by, status, fraud_flag,
    fraud_reason are all in read_only_fields — they cannot be set via
    the request body regardless of what the caller sends.
    """

    class Meta:
        model = Claim
        fields = (
            'id',
            'policy',
            'claim_amount',
            'description',
            'date_filed',
            'status',
            'fraud_flag',
            'submitted_by',
        )
        read_only_fields = (
            'id',
            'date_filed',
            'status',        # always starts as 'pending'
            'fraud_flag',    # set by fraud service after save
            'submitted_by',  # always set from request.user in view
        )

    def validate(self, attrs):
        request = self.context.get('request')
        policy = attrs.get('policy')

        # ── Validation 1: Policy must be active ──────────────────────────────
        if policy.status != Policy.STATUS_ACTIVE:
            raise serializers.ValidationError(
                f"Cannot file a claim against a policy with status '{policy.status}'."
            )

        # ── Validation 2: Coverage cap ────────────────────────────────────────
        if attrs.get('claim_amount') > policy.coverage_amount:
            raise serializers.ValidationError(
                f"claim_amount ({attrs['claim_amount']}) exceeds policy coverage_amount "
                f"({policy.coverage_amount})."
            )

        # ── Validation 3: Ownership / BOLA check ─────────────────────────────
        # This is enforced here in the serializer, not the view, so it applies
        # regardless of how the serializer is invoked. Without this check, any
        # authenticated customer could file a claim against any policy by
        # simply including a different policy ID in the request body.
        if request and request.user.role != 'admin':
            if policy.user != request.user:
                raise PermissionDenied(
                    "You do not own this policy and cannot file a claim against it."
                )

        return attrs


class ClaimReviewSerializer(serializers.Serializer):
    """
    Used by PATCH /api/v1/claims/<id>/review/ — admin only.
    Accepts only 'approved' or 'rejected'; any other value is rejected with 400.
    """

    STATUS_CHOICES = [Claim.STATUS_APPROVED, Claim.STATUS_REJECTED]

    status = serializers.ChoiceField(choices=STATUS_CHOICES)
