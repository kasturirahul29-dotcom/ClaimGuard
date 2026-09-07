from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """
    Custom user model.

    Why a role field instead of Django groups/permissions:
    The system has exactly two roles with clear, static semantics —
    'customer' and 'admin'. Django's groups/permissions framework is
    designed for fine-grained, per-object permission matrices. Using
    a simple role CharField makes the authorization logic readable
    in one place (common/permissions.py) and avoids the overhead of
    permission lookups that aren't needed here. If the system ever
    needs per-object or per-action permissions at a fine-grained level,
    migrating to groups would be the right call at that point.

    email is set unique=True explicitly — AbstractUser does NOT enforce
    this by default, and the registration endpoint uses email as a
    recoverable identifier.
    """

    ROLE_CUSTOMER = 'customer'
    ROLE_ADMIN = 'admin'

    ROLE_CHOICES = [
        (ROLE_CUSTOMER, 'Customer'),
        (ROLE_ADMIN, 'Admin'),
    ]

    email = models.EmailField(unique=True)

    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default=ROLE_CUSTOMER,
    )

    class Meta:
        db_table = 'accounts_user'

    def __str__(self):
        return f'{self.username} ({self.role})'
