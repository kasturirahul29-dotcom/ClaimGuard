"""
Fraud detection service for insurance claims.

Why a service function rather than a model method or a save() override:
- Unit-testable in isolation: the function takes a Claim object and
  returns a tuple — you can call it with an unsaved Claim() built in
  memory without needing a full Django test database for the rule logic
  itself (only Rule 1 needs a DB query for the historical average).
- Business logic stays out of the data layer: hiding fraud detection
  inside save() would make it impossible to skip or mock in tests, and
  would run silently on any admin bulk-update.
- The return value (fraud_flag, fraud_reason) is explicit — the caller
  (the claim creation view) decides when and how to persist those values.
  This keeps the audit trail legible: "create claim, run fraud check,
  write both together in one atomic save."

Fraud rules (all three are evaluated independently — any can fire):

  Rule 1 — high-amount:
    flag if claim_amount > 3 × avg(claim_amount) across ALL previously
    filed claims sharing the same policy_type (system-wide, not per-policy).
    COLD-START GUARD: the rule is skipped when fewer than FRAUD_MIN_HISTORY_SAMPLE
    prior claims exist for that policy_type. The guard exists because a
    two-claim "average" of $50 would flag almost anything as suspicious —
    the rule only becomes meaningful once there is real distributional
    history to anchor the threshold.

  Rule 2 — early-claim:
    flag if the claim is filed within 7 days of the policy's start_date.
    (days_filed_since_start < 7, i.e. same day = 0 days = fires; day 7 = does NOT fire)

  Rule 3 — near-total-payout:
    flag if claim_amount >= 90% of the policy's coverage_amount.
    Uses Decimal("0.9") — never float 0.9 — to avoid float/Decimal TypeError.
"""

from decimal import Decimal
from django.db.models import Avg, Count
from django.utils import timezone

# Named constant so the threshold is visible and tunable without hunting
# through query logic.
FRAUD_MIN_HISTORY_SAMPLE = 5

# Multiplier for Rule 1: flag if amount > this × historical average
FRAUD_HIGH_AMOUNT_MULTIPLIER = Decimal('3')

# Rule 3 threshold: flag if claim_amount >= this fraction of coverage
FRAUD_NEAR_TOTAL_PAYOUT_RATIO = Decimal('0.9')

# Rule 2 threshold: flag if claim filed within this many days of policy start
FRAUD_EARLY_CLAIM_DAYS = 7


def check_fraud(claim) -> tuple:
    """
    Evaluate fraud rules against the given claim.

    Returns:
        (fraud_flag: bool, fraud_reason: str)
        fraud_reason is "" (empty string, not None) when fraud_flag is False.

    Does NOT mutate or save the claim — the caller is responsible for
    persisting the returned values on the claim instance.

    Can be called on both saved and unsaved Claim instances; Rule 1 will
    exclude the claim's own pk if it is already saved.
    """
    # Local import to avoid circular imports between claims.models and this service
    from claims.models import Claim as ClaimModel

    fired_rules = []

    # ─── Rule 1: High-Amount ──────────────────────────────────────────────────
    policy_type = claim.policy.policy_type

    # Build historical queryset: all claims of the same policy_type,
    # excluding the current claim if it already has a pk (re-check scenario).
    historical_qs = ClaimModel.objects.filter(policy__policy_type=policy_type)
    if claim.pk:
        historical_qs = historical_qs.exclude(pk=claim.pk)

    agg = historical_qs.aggregate(count=Count('id'), avg_amount=Avg('claim_amount'))
    historical_count = agg['count'] or 0
    avg_amount = agg['avg_amount']

    if historical_count >= FRAUD_MIN_HISTORY_SAMPLE and avg_amount is not None:
        # Both sides are Decimal-compatible (Decimal × Decimal is fine)
        threshold = Decimal(str(avg_amount)) * FRAUD_HIGH_AMOUNT_MULTIPLIER
        if claim.claim_amount > threshold:
            fired_rules.append('high-amount')
    # If historical_count < FRAUD_MIN_HISTORY_SAMPLE, this rule does not fire —
    # the sample isn't large enough to produce a meaningful average.

    # ─── Rule 2: Early-Claim ──────────────────────────────────────────────────
    # claim.date_filed is auto_now_add (a DateField), so on an unsaved claim
    # it will be None — fall back to today's date.
    filed_date = claim.date_filed if claim.date_filed else timezone.now().date()
    days_since_start = (filed_date - claim.policy.start_date).days
    # Rule fires if strictly less than 7 days; day 7 itself does NOT fire.
    if days_since_start < FRAUD_EARLY_CLAIM_DAYS:
        fired_rules.append('early-claim')

    # ─── Rule 3: Near-Total-Payout ────────────────────────────────────────────
    # Use Decimal("0.9") — mixing Python float 0.9 with a Decimal raises TypeError.
    coverage = claim.policy.coverage_amount
    if coverage > 0 and claim.claim_amount >= FRAUD_NEAR_TOTAL_PAYOUT_RATIO * coverage:
        fired_rules.append('near-total-payout')

    # ─── Compose result ───────────────────────────────────────────────────────
    fraud_flag = len(fired_rules) > 0
    fraud_reason = f"Flagged: {', '.join(fired_rules)}" if fraud_flag else ''

    return fraud_flag, fraud_reason
