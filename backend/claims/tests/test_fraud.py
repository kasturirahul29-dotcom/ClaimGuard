"""
Phase 2 — Tests for check_fraud() service function.

Each test focuses on exactly one rule or one boundary condition.
Tests are ordered: Rule 1 (with cold-start), Rule 2 (with boundary),
Rule 3 (with boundary), multi-rule, and clean-claim.
"""
import datetime
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from accounts.models import User
from policies.models import Policy
from claims.models import Claim
from claims.services.fraud import (
    check_fraud,
    FRAUD_MIN_HISTORY_SAMPLE,
    FRAUD_EARLY_CLAIM_DAYS,
)


def make_user(username='u', role='customer'):
    return User.objects.create_user(
        username=username, email=f'{username}@t.com', password='Pass123!', role=role
    )


def make_policy(user, policy_type='auto', coverage=Decimal('50000.00'), start_days_ago=30):
    start = datetime.date.today() - datetime.timedelta(days=start_days_ago)
    return Policy.objects.create(
        user=user,
        policy_type=policy_type,
        coverage_amount=coverage,
        premium=Decimal('100.00'),
        start_date=start,
        status=Policy.STATUS_ACTIVE,
    )


def make_saved_claim(policy, user, amount, days_ago=0):
    """Create and save a claim with date_filed set to today."""
    return Claim.objects.create(
        policy=policy,
        submitted_by=user,
        claim_amount=amount,
        description='Test',
    )


class FraudRule1HighAmountTest(TestCase):
    """Rule 1: claim_amount > 3 × historical average, with ≥5 prior claims."""

    def setUp(self):
        self.user = make_user('r1user')
        self.policy = make_policy(self.user, policy_type='auto', coverage=Decimal('999999.00'))

    def _seed_history(self, count, amount_each):
        """Create `count` historical claims all with the same amount."""
        for i in range(count):
            make_saved_claim(self.policy, self.user, amount_each)

    def test_rule1_fires_with_sufficient_history(self):
        """
        5 prior claims averaging $100 → threshold = $300.
        A new claim of $301 should fire the high-amount rule.
        """
        self._seed_history(FRAUD_MIN_HISTORY_SAMPLE, Decimal('100.00'))
        # Build an unsaved claim to test with
        new_claim = Claim(
            policy=self.policy,
            submitted_by=self.user,
            claim_amount=Decimal('301.00'),
            description='Should flag',
        )
        fraud_flag, fraud_reason = check_fraud(new_claim)
        self.assertTrue(fraud_flag)
        self.assertIn('high-amount', fraud_reason)

    def test_rule1_does_not_fire_below_threshold(self):
        """
        5 prior claims averaging $100 → threshold = $300.
        A claim of exactly $300 (not strictly greater) should not fire.
        """
        self._seed_history(FRAUD_MIN_HISTORY_SAMPLE, Decimal('100.00'))
        new_claim = Claim(
            policy=self.policy,
            submitted_by=self.user,
            claim_amount=Decimal('300.00'),
            description='Exactly at threshold',
        )
        fraud_flag, fraud_reason = check_fraud(new_claim)
        # Rule 1 condition is STRICTLY greater than — $300 does not fire
        self.assertNotIn('high-amount', fraud_reason)


class FraudRule1ColdStartTest(TestCase):
    """
    Rule 1 cold-start guard: rule must NOT fire when fewer than
    FRAUD_MIN_HISTORY_SAMPLE prior claims exist, even if the amount
    would exceed the average of a tiny sample.
    """

    def test_cold_start_with_zero_history(self):
        user = make_user('cold0')
        policy = make_policy(user, policy_type='health', coverage=Decimal('999999.00'))
        new_claim = Claim(
            policy=policy,
            submitted_by=user,
            claim_amount=Decimal('1000000.00'),  # astronomically high
            description='Cold start — no history',
        )
        fraud_flag, fraud_reason = check_fraud(new_claim)
        self.assertNotIn('high-amount', fraud_reason)

    def test_cold_start_with_fewer_than_minimum_history(self):
        """4 prior claims is still below the threshold of 5."""
        user = make_user('cold4')
        policy = make_policy(user, policy_type='property', coverage=Decimal('999999.00'))
        # Seed 4 claims (one less than FRAUD_MIN_HISTORY_SAMPLE=5)
        for _ in range(FRAUD_MIN_HISTORY_SAMPLE - 1):
            make_saved_claim(policy, user, Decimal('50.00'))
        new_claim = Claim(
            policy=policy,
            submitted_by=user,
            claim_amount=Decimal('99999.00'),  # far above any average
            description='4 prior — still cold start',
        )
        fraud_flag, fraud_reason = check_fraud(new_claim)
        self.assertNotIn('high-amount', fraud_reason)

    def test_exactly_minimum_history_enables_rule(self):
        """Exactly 5 prior claims — rule becomes active."""
        user = make_user('exact5')
        policy = make_policy(user, policy_type='auto', coverage=Decimal('999999.00'))
        for _ in range(FRAUD_MIN_HISTORY_SAMPLE):
            make_saved_claim(policy, user, Decimal('100.00'))
        new_claim = Claim(
            policy=policy,
            submitted_by=user,
            claim_amount=Decimal('999.00'),  # > 3×100
            description='5 prior — rule active',
        )
        fraud_flag, fraud_reason = check_fraud(new_claim)
        self.assertIn('high-amount', fraud_reason)


class FraudRule2EarlyClaimTest(TestCase):
    """Rule 2: filed within FRAUD_EARLY_CLAIM_DAYS days of policy start."""

    def test_rule2_fires_when_filed_same_day(self):
        user = make_user('early1')
        policy = make_policy(user, start_days_ago=0)  # started today
        claim = Claim(
            policy=policy,
            submitted_by=user,
            claim_amount=Decimal('100.00'),
            description='Same day',
            date_filed=datetime.date.today(),
        )
        _, reason = check_fraud(claim)
        self.assertIn('early-claim', reason)

    def test_rule2_fires_when_filed_6_days_after_start(self):
        user = make_user('early6')
        policy = make_policy(user, start_days_ago=6)
        claim = Claim(
            policy=policy,
            submitted_by=user,
            claim_amount=Decimal('100.00'),
            description='6 days',
            date_filed=datetime.date.today(),
        )
        _, reason = check_fraud(claim)
        self.assertIn('early-claim', reason)

    def test_rule2_does_not_fire_at_exactly_7_days(self):
        """
        Boundary test: rule is `< 7`, so exactly 7 days does NOT fire.
        """
        user = make_user('day7')
        policy = make_policy(user, start_days_ago=7)
        claim = Claim(
            policy=policy,
            submitted_by=user,
            claim_amount=Decimal('100.00'),
            description='Day 7 boundary',
            date_filed=datetime.date.today(),
        )
        _, reason = check_fraud(claim)
        self.assertNotIn('early-claim', reason)

    def test_rule2_does_not_fire_well_after_start(self):
        user = make_user('late')
        policy = make_policy(user, start_days_ago=365)
        claim = Claim(
            policy=policy,
            submitted_by=user,
            claim_amount=Decimal('100.00'),
            description='1 year later',
            date_filed=datetime.date.today(),
        )
        _, reason = check_fraud(claim)
        self.assertNotIn('early-claim', reason)


class FraudRule3NearTotalPayoutTest(TestCase):
    """Rule 3: claim_amount >= 90% of coverage_amount."""

    def test_rule3_fires_at_exactly_90_percent(self):
        """Boundary: exactly 90% must fire (>= not >)."""
        user = make_user('near1')
        policy = make_policy(user, coverage=Decimal('10000.00'), start_days_ago=30)
        claim = Claim(
            policy=policy,
            submitted_by=user,
            claim_amount=Decimal('9000.00'),  # exactly 90%
            description='Exactly 90%',
            date_filed=datetime.date.today(),
        )
        _, reason = check_fraud(claim)
        self.assertIn('near-total-payout', reason)

    def test_rule3_fires_above_90_percent(self):
        user = make_user('near2')
        policy = make_policy(user, coverage=Decimal('10000.00'), start_days_ago=30)
        claim = Claim(
            policy=policy,
            submitted_by=user,
            claim_amount=Decimal('9500.00'),
            description='95%',
            date_filed=datetime.date.today(),
        )
        _, reason = check_fraud(claim)
        self.assertIn('near-total-payout', reason)

    def test_rule3_does_not_fire_below_90_percent(self):
        user = make_user('near3')
        policy = make_policy(user, coverage=Decimal('10000.00'), start_days_ago=30)
        claim = Claim(
            policy=policy,
            submitted_by=user,
            claim_amount=Decimal('8999.99'),  # just below 90%
            description='89.99%',
            date_filed=datetime.date.today(),
        )
        _, reason = check_fraud(claim)
        self.assertNotIn('near-total-payout', reason)


class FraudMultipleRulesTest(TestCase):
    """A claim that triggers multiple rules must record all of them."""

    def test_multiple_rules_all_appear_in_reason(self):
        user = make_user('multi')
        # start_days_ago=0 → early-claim fires
        # coverage=100 and amount=91 → near-total-payout fires (91%)
        policy = make_policy(user, coverage=Decimal('100.00'), start_days_ago=0)
        # Seed 5 historical claims averaging $1 each → threshold $3
        for _ in range(FRAUD_MIN_HISTORY_SAMPLE):
            make_saved_claim(policy, user, Decimal('1.00'))
        # amount=91 > 3×1=3 → high-amount also fires
        claim = Claim(
            policy=policy,
            submitted_by=user,
            claim_amount=Decimal('91.00'),
            description='All three rules',
            date_filed=datetime.date.today(),
        )
        fraud_flag, reason = check_fraud(claim)
        self.assertTrue(fraud_flag)
        self.assertIn('high-amount', reason)
        self.assertIn('early-claim', reason)
        self.assertIn('near-total-payout', reason)


class FraudCleanClaimTest(TestCase):
    """A clean claim must not be flagged; fraud_reason must be empty string, not None."""

    def test_clean_claim_not_flagged(self):
        user = make_user('clean')
        policy = make_policy(user, coverage=Decimal('10000.00'), start_days_ago=30)
        claim = Claim(
            policy=policy,
            submitted_by=user,
            claim_amount=Decimal('100.00'),  # well below any threshold
            description='Clean claim',
            date_filed=datetime.date.today(),
        )
        fraud_flag, fraud_reason = check_fraud(claim)
        self.assertFalse(fraud_flag)
        # fraud_reason must be an empty string, not None, and not "Flagged: "
        self.assertEqual(fraud_reason, '')
        self.assertIsNotNone(fraud_reason)
