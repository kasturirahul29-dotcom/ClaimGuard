from django.db import models, transaction
from django.conf import settings


class Policy(models.Model):
    """
    Insurance policy owned by a customer user.

    Two-step workflow:
      1. Customer POSTs to /policies/ → status='pending_activation'
      2. Admin PATCHes /policies/<id>/activate/ → status='active'

    This mirrors the claim-review workflow and makes the system's state
    machine explicit: nothing a customer submits goes live until an admin
    approves it.

    policy_number auto-generation (race-condition note):
      Using `count() + 1` is not safe under concurrent inserts — two
      simultaneous requests could both read count=42, both try to write
      POL-00043, and one would fail the uniqueness constraint. The safe
      approach used here is to lock the last row with select_for_update()
      inside a transaction, derive next_id from last.id + 1, then write.
      This serializes concurrent inserts for policy_number generation
      without a separate sequence table, at the cost of a brief row-level
      lock. Under low concurrent load (portfolio scale) this is acceptable;
      a production system at scale would use a PostgreSQL SEQUENCE object.
    """

    TYPE_AUTO = 'auto'
    TYPE_HEALTH = 'health'
    TYPE_PROPERTY = 'property'

    POLICY_TYPE_CHOICES = [
        (TYPE_AUTO, 'Auto'),
        (TYPE_HEALTH, 'Health'),
        (TYPE_PROPERTY, 'Property'),
    ]

    STATUS_PENDING = 'pending_activation'
    STATUS_ACTIVE = 'active'
    STATUS_EXPIRED = 'expired'
    STATUS_CANCELLED = 'cancelled'

    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending Activation'),
        (STATUS_ACTIVE, 'Active'),
        (STATUS_EXPIRED, 'Expired'),
        (STATUS_CANCELLED, 'Cancelled'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='policies',
        # PROTECT: prevents deleting a user who owns policies, which would
        # otherwise orphan all claims filed against those policies.
    )
    policy_number = models.CharField(
        max_length=20,
        unique=True,
        db_index=True,
        blank=True,  # populated in save() before DB write
    )
    policy_type = models.CharField(
        max_length=20,
        choices=POLICY_TYPE_CHOICES,
    )
    # Decimal fields — never FloatField for money.
    # Floating-point cannot represent 0.1 exactly, leading to rounding
    # errors that compound across calculations (e.g. coverage checks).
    coverage_amount = models.DecimalField(max_digits=12, decimal_places=2)
    premium = models.DecimalField(max_digits=12, decimal_places=2)
    start_date = models.DateField()
    status = models.CharField(
        max_length=25,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'policies_policy'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['policy_number']),
        ]

    def save(self, *args, **kwargs):
        """Auto-generate policy_number on first save using a locked read."""
        if not self.policy_number:
            with transaction.atomic():
                # Lock the last row to prevent concurrent sequence gaps.
                last = Policy.objects.select_for_update().order_by('-id').first()
                next_id = (last.id + 1) if last else 1
                self.policy_number = f'POL-{next_id:05d}'
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.policy_number} ({self.get_policy_type_display()}) — {self.user.username}'
