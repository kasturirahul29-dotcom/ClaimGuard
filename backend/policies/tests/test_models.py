"""
Phase 1 model-level tests for Policy and User.

These tests verify DB-level constraints and ORM behaviors that must hold
regardless of any API layer: uniqueness enforcement, PROTECT/SET_NULL
cascades, and Decimal precision round-trips.
"""
import datetime
from decimal import Decimal

from django.test import TestCase
from django.db import IntegrityError
from django.db.models.deletion import ProtectedError

from accounts.models import User
from policies.models import Policy


def make_user(username='testuser', role='customer'):
    return User.objects.create_user(
        username=username,
        email=f'{username}@test.com',
        password='TestPass123!',
        role=role,
    )


def make_policy(user, policy_type='auto', coverage=Decimal('10000.00'), status=Policy.STATUS_ACTIVE):
    return Policy.objects.create(
        user=user,
        policy_type=policy_type,
        coverage_amount=coverage,
        premium=Decimal('150.00'),
        start_date=datetime.date.today(),
        status=status,
    )


class PolicyNumberUniquenessTest(TestCase):
    """policy_number must be unique at the DB level."""

    def test_duplicate_policy_number_raises_integrity_error(self):
        user = make_user()
        p = make_policy(user)
        # Attempt to force a duplicate policy_number via update (bypasses save())
        with self.assertRaises(IntegrityError):
            Policy.objects.create(
                user=user,
                policy_number=p.policy_number,  # same number
                policy_type='health',
                coverage_amount=Decimal('5000.00'),
                premium=Decimal('80.00'),
                start_date=datetime.date.today(),
                status=Policy.STATUS_ACTIVE,
            )

    def test_policy_number_auto_generated_on_save(self):
        user = make_user()
        p = make_policy(user)
        self.assertTrue(p.policy_number.startswith('POL-'))
        self.assertEqual(len(p.policy_number), 9)  # 'POL-00001'

    def test_sequential_policies_have_unique_numbers(self):
        user = make_user()
        p1 = make_policy(user, policy_type='auto')
        p2 = make_policy(user, policy_type='health')
        self.assertNotEqual(p1.policy_number, p2.policy_number)


class PolicyProtectOnUserDeleteTest(TestCase):
    """Deleting a User who owns a Policy must raise ProtectedError."""

    def test_delete_user_with_policy_raises_protected_error(self):
        user = make_user()
        make_policy(user)
        with self.assertRaises(ProtectedError):
            user.delete()


class PolicyProtectOnClaimExistsTest(TestCase):
    """Deleting a Policy with existing Claims must raise ProtectedError."""

    def test_delete_policy_with_claim_raises_protected_error(self):
        from claims.models import Claim

        user = make_user()
        policy = make_policy(user)
        Claim.objects.create(
            policy=policy,
            submitted_by=user,
            claim_amount=Decimal('500.00'),
            description='Test claim',
            status=Claim.STATUS_PENDING,
        )
        with self.assertRaises(ProtectedError):
            policy.delete()


class ReviewedBySetNullTest(TestCase):
    """
    Deleting the admin who reviewed a claim must succeed and set
    reviewed_by to NULL (confirms SET_NULL behavior on that FK).
    """

    def test_delete_reviewer_sets_reviewed_by_null(self):
        from claims.models import Claim
        from django.utils import timezone

        customer = make_user('customer1')
        admin = make_user('admin1', role='admin')
        policy = make_policy(customer)
        claim = Claim.objects.create(
            policy=policy,
            submitted_by=customer,
            claim_amount=Decimal('500.00'),
            description='Reviewed claim',
            status=Claim.STATUS_APPROVED,
            reviewed_by=admin,
            reviewed_at=timezone.now(),
        )
        admin.delete()
        claim.refresh_from_db()
        self.assertIsNone(claim.reviewed_by)


class DecimalPrecisionTest(TestCase):
    """Decimal values must survive a DB round-trip without float rounding."""

    def test_claim_amount_decimal_precision(self):
        from claims.models import Claim

        user = make_user()
        policy = make_policy(user, coverage=Decimal('9999999.99'))
        claim = Claim.objects.create(
            policy=policy,
            submitted_by=user,
            claim_amount=Decimal('1234567.89'),
            description='Precision test',
        )
        reloaded = Claim.objects.get(pk=claim.pk)
        self.assertEqual(reloaded.claim_amount, Decimal('1234567.89'))

    def test_coverage_amount_decimal_precision(self):
        user = make_user()
        policy = make_policy(user, coverage=Decimal('99999.99'))
        reloaded = Policy.objects.get(pk=policy.pk)
        self.assertEqual(reloaded.coverage_amount, Decimal('99999.99'))
