from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from .models import User


class RegisterSerializer(serializers.ModelSerializer):
    """
    Serializer for the registration endpoint.

    Mass-assignment protection: `role` is NOT in the fields list and
    is always forced to 'customer' in create(). Even if a caller sends
    {"role": "admin"} in the request body, it will be silently ignored
    because the serializer only processes fields it declares, and create()
    explicitly overrides it.
    """

    password = serializers.CharField(
        write_only=True,
        required=True,
        validators=[validate_password],
    )

    class Meta:
        model = User
        # 'role' is included READ-ONLY in the response so clients can read what
        # they were assigned, but it is not a writable field — setting it in
        # the request body is silently ignored because create() hardcodes
        # role=ROLE_CUSTOMER. The password field is write_only=True above.
        fields = ('id', 'username', 'email', 'password', 'role')
        read_only_fields = ('id', 'role')

    def create(self, validated_data):
        return User.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            password=validated_data['password'],
            role=User.ROLE_CUSTOMER,  # Always customer — never trust the caller
        )


class UserSerializer(serializers.ModelSerializer):
    """Read-only user representation used in embedded responses."""

    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'role')
        read_only_fields = ('id', 'username', 'email', 'role')

from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        # Add custom claims
        token['username'] = user.username
        token['email'] = user.email
        token['role'] = user.role
        return token

