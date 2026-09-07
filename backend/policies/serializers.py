from rest_framework import serializers
from .models import Policy


class PolicySerializer(serializers.ModelSerializer):
    """
    Full policy serializer — used for both customers and admins on reads.

    Mass-assignment protection via read_only_fields:
    - policy_number: auto-generated, never caller-controlled
    - user: always set from request.user (or admin-specified user, handled in view)
    - created_at: auto timestamp
    - status: customers cannot set this (handled in get_serializer_class
      in the view; only admins get PolicyAdminCreateSerializer which
      allows status on create)
    """

    user_username = serializers.CharField(source='user.username', read_only=True)

    class Meta:
        model = Policy
        fields = (
            'id',
            'user',
            'user_username',
            'policy_number',
            'policy_type',
            'coverage_amount',
            'premium',
            'start_date',
            'status',
            'created_at',
        )
        read_only_fields = ('id', 'user', 'user_username', 'policy_number', 'status', 'created_at')


class PolicyCreateSerializer(serializers.ModelSerializer):
    """
    Used when a customer creates a new policy request.
    - 'user' is set from request.user in the view's perform_create
    - 'status' is locked to pending_activation by the view
    - 'policy_number' is auto-generated
    """

    class Meta:
        model = Policy
        fields = ('id', 'policy_number', 'policy_type', 'coverage_amount', 'premium', 'start_date', 'status', 'created_at')
        read_only_fields = ('id', 'policy_number', 'status', 'created_at')


class PolicyAdminCreateSerializer(serializers.ModelSerializer):
    """
    Used when an admin creates a policy — allows specifying user and status.
    """

    class Meta:
        model = Policy
        fields = ('id', 'user', 'policy_number', 'policy_type', 'coverage_amount', 'premium', 'start_date', 'status', 'created_at')
        read_only_fields = ('id', 'policy_number', 'created_at')


class PolicyActivateSerializer(serializers.ModelSerializer):
    """Used by the /activate/ action — transitions pending_activation → active."""

    class Meta:
        model = Policy
        fields = ('id', 'status')
        read_only_fields = ('id',)
