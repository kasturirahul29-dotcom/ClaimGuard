from django.db import models
from django.conf import settings
from policies.models import Policy


class Claim(models.Model):
    """
    Insurance claim filed against a policy.

    Lifecycle: pending → approved | rejected (via /review/ endpoint, admin only).
    Once reviewed, the status cannot change through this endpoint — a future
    audit-log override path would be needed for corrections.

    fraud_flag and fraud_reason are written by claims/services/fraud.py
    immediately after the claim is created, before it is committed.
    They are never set by client input.
    """

    STATUS_PENDING = 'pending'
    STATUS_APPROVED = 'approved'
    STATUS_REJECTED = 'rejected'

    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending'),
        (STATUS_APPROVED, 'Approved'),
        (STATUS_REJECTED, 'Rejected'),
    ]

    policy = models.ForeignKey(
        Policy,
        on_delete=models.PROTECT,
        related_name='claims',
    )
    submitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='submitted_claims',
    )
    claim_amount = models.DecimalField(max_digits=12, decimal_places=2)
    description = models.TextField()
    date_filed = models.DateField(auto_now_add=True)
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
        db_index=True,  # filtered on every list endpoint and /flagged/
    )
    fraud_flag = models.BooleanField(default=False)
    fraud_reason = models.TextField(null=True, blank=True)

    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        # SET_NULL not PROTECT: deactivating an admin account should not
        # block access to claim history — the claim record must survive.
        null=True,
        blank=True,
        related_name='reviewed_claims',
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'claims_claim'
        ordering = ['-date_filed']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['fraud_flag', 'status']),  # for /flagged/ query
        ]

    def __str__(self):
        return f'Claim #{self.pk} on {self.policy.policy_number} ({self.status})'
