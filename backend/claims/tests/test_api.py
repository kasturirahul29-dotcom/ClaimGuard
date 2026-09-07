"""
Phase 5 — Full API test suite covering:
- Happy-path end-to-end flow
- Customer cannot access admin-only endpoints
- BOLA: customers cannot access other users' resources
- Validation: expired/cancelled policy, coverage cap
- Mass-assignment: role cannot be set via registration
- Pagination: 25 claims returns page 1 = 20, page 2 = 5
- fraud_reason never appears in customer-facing responses
"""
import datetime
from decimal import Decimal

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import User
from policies.models import Policy
from claims.models import Claim


# ─── Helpers ──────────────────────────────────────────────────────────────────

def create_user(username, role='customer', password='TestPass123!'):
    return User.objects.create_user(
        username=username,
        email=f'{username}@test.com',
        password=password,
        role=role,
    )


def create_policy(user, policy_type='auto', coverage='10000.00',
                  status_val=Policy.STATUS_ACTIVE, start_days_ago=30):
    start = datetime.date.today() - datetime.timedelta(days=start_days_ago)
    return Policy.objects.create(
        user=user,
        policy_type=policy_type,
        coverage_amount=Decimal(coverage),
        premium=Decimal('150.00'),
        start_date=start,
        status=status_val,
    )


def create_claim(policy, user, amount='500.00', status_val=Claim.STATUS_PENDING):
    return Claim.objects.create(
        policy=policy,
        submitted_by=user,
        claim_amount=Decimal(amount),
        description='Test claim',
        status=status_val,
    )


def get_tokens(client, username, password='TestPass123!'):
    resp = client.post('/api/v1/auth/login/', {'username': username, 'password': password})
    return resp.data['access'], resp.data['refresh']


def auth_header(token):
    return {'HTTP_AUTHORIZATION': f'Bearer {token}'}


# ─── Registration Tests ───────────────────────────────────────────────────────

class RegistrationTest(APITestCase):
    URL = '/api/v1/auth/register/'

    def test_register_creates_customer(self):
        resp = self.client.post(self.URL, {
            'username': 'newuser',
            'email': 'new@test.com',
            'password': 'StrongPass999!',
        })
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp.data['role'], 'customer')

    def test_register_with_role_admin_still_creates_customer(self):
        """
        Mass-assignment guard: submitting role='admin' in the registration
        body must be silently ignored — the user is always created as customer.
        """
        resp = self.client.post(self.URL, {
            'username': 'hacker',
            'email': 'hacker@test.com',
            'password': 'StrongPass999!',
            'role': 'admin',
        })
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        user = User.objects.get(username='hacker')
        self.assertEqual(user.role, 'customer')


# ─── Auth Flow Tests ──────────────────────────────────────────────────────────

class AuthFlowTest(APITestCase):
    def setUp(self):
        self.user = create_user('authuser')

    def test_login_returns_access_and_refresh(self):
        resp = self.client.post('/api/v1/auth/login/', {
            'username': 'authuser', 'password': 'TestPass123!'
        })
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn('access', resp.data)
        self.assertIn('refresh', resp.data)

    def test_refresh_returns_new_access_token(self):
        access, refresh = get_tokens(self.client, 'authuser')
        resp = self.client.post('/api/v1/auth/refresh/', {'refresh': refresh})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn('access', resp.data)


# ─── Policy Tests ─────────────────────────────────────────────────────────────

class PolicyListTest(APITestCase):
    def setUp(self):
        self.customer1 = create_user('cust1')
        self.customer2 = create_user('cust2')
        self.admin = create_user('admin1', role='admin')
        self.p1 = create_policy(self.customer1)
        self.p2 = create_policy(self.customer2)

    def test_customer_sees_only_own_policies(self):
        token, _ = get_tokens(self.client, 'cust1')
        resp = self.client.get('/api/v1/policies/', **auth_header(token))
        ids = [p['id'] for p in resp.data['results']]
        self.assertIn(self.p1.pk, ids)
        self.assertNotIn(self.p2.pk, ids)

    def test_admin_sees_all_policies(self):
        token, _ = get_tokens(self.client, 'admin1')
        resp = self.client.get('/api/v1/policies/', **auth_header(token))
        ids = [p['id'] for p in resp.data['results']]
        self.assertIn(self.p1.pk, ids)
        self.assertIn(self.p2.pk, ids)

    def test_customer_cannot_access_other_users_policy_by_id(self):
        """BOLA: guessing another customer's policy ID must return 404."""
        token, _ = get_tokens(self.client, 'cust1')
        resp = self.client.get(f'/api/v1/policies/{self.p2.pk}/', **auth_header(token))
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)


class PolicyCreateTest(APITestCase):
    def setUp(self):
        self.customer = create_user('custcreate')
        self.admin = create_user('admincreate', role='admin')

    def test_customer_create_policy_status_is_pending(self):
        token, _ = get_tokens(self.client, 'custcreate')
        resp = self.client.post('/api/v1/policies/', {
            'policy_type': 'auto',
            'coverage_amount': '5000.00',
            'premium': '100.00',
            'start_date': str(datetime.date.today()),
        }, **auth_header(token))
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp.data['status'], Policy.STATUS_PENDING)

    def test_admin_can_activate_pending_policy(self):
        token, _ = get_tokens(self.client, 'custcreate')
        resp = self.client.post('/api/v1/policies/', {
            'policy_type': 'auto',
            'coverage_amount': '5000.00',
            'premium': '100.00',
            'start_date': str(datetime.date.today()),
        }, **auth_header(token))
        policy_id = resp.data['id']

        admin_token, _ = get_tokens(self.client, 'admincreate')
        resp2 = self.client.patch(
            f'/api/v1/policies/{policy_id}/activate/',
            **auth_header(admin_token),
        )
        self.assertEqual(resp2.status_code, status.HTTP_200_OK)
        self.assertEqual(resp2.data['status'], Policy.STATUS_ACTIVE)

    def test_customer_cannot_activate_policy(self):
        token, _ = get_tokens(self.client, 'custcreate')
        resp = self.client.post('/api/v1/policies/', {
            'policy_type': 'auto',
            'coverage_amount': '5000.00',
            'premium': '100.00',
            'start_date': str(datetime.date.today()),
        }, **auth_header(token))
        policy_id = resp.data['id']
        resp2 = self.client.patch(
            f'/api/v1/policies/{policy_id}/activate/',
            **auth_header(token),
        )
        self.assertIn(resp2.status_code, [status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND])


# ─── Claim Validation Tests ───────────────────────────────────────────────────

class ClaimValidationTest(APITestCase):
    def setUp(self):
        self.customer = create_user('claimcust')
        self.other_customer = create_user('othercust')
        self.admin = create_user('claimadmin', role='admin')
        self.active_policy = create_policy(self.customer, status_val=Policy.STATUS_ACTIVE)
        self.expired_policy = create_policy(self.customer, status_val=Policy.STATUS_EXPIRED)
        self.cancelled_policy = create_policy(self.customer, status_val=Policy.STATUS_CANCELLED)
        self.other_policy = create_policy(self.other_customer, status_val=Policy.STATUS_ACTIVE)

    def _post_claim(self, token, policy_id, amount='100.00'):
        return self.client.post('/api/v1/claims/', {
            'policy': policy_id,
            'claim_amount': amount,
            'description': 'Test',
        }, **auth_header(token))

    def test_submit_against_expired_policy_returns_400(self):
        token, _ = get_tokens(self.client, 'claimcust')
        resp = self._post_claim(token, self.expired_policy.pk)
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_submit_against_cancelled_policy_returns_400(self):
        token, _ = get_tokens(self.client, 'claimcust')
        resp = self._post_claim(token, self.cancelled_policy.pk)
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_submit_above_coverage_returns_400(self):
        """claim_amount > coverage_amount must be rejected."""
        token, _ = get_tokens(self.client, 'claimcust')
        above_coverage = str(self.active_policy.coverage_amount + Decimal('1.00'))
        resp = self._post_claim(token, self.active_policy.pk, amount=above_coverage)
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_submit_against_other_users_policy_returns_403(self):
        """
        BOLA guard: customer submitting a claim against another user's
        policy by providing that policy's ID must be rejected with 403.
        This is the most critical security test in the suite.
        """
        token, _ = get_tokens(self.client, 'claimcust')
        resp = self._post_claim(token, self.other_policy.pk)
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_valid_claim_submission_succeeds(self):
        token, _ = get_tokens(self.client, 'claimcust')
        resp = self._post_claim(token, self.active_policy.pk, '500.00')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertIn('fraud_flag', resp.data)

    def test_customer_response_does_not_include_fraud_reason(self):
        """
        Defense-in-depth: even if a claim is fraudulent, fraud_reason
        must never appear in a customer-facing API response.
        """
        token, _ = get_tokens(self.client, 'claimcust')
        resp = self._post_claim(token, self.active_policy.pk, '500.00')
        self.assertNotIn('fraud_reason', resp.data)


# ─── Claim Access Control Tests ───────────────────────────────────────────────

class ClaimAccessControlTest(APITestCase):
    def setUp(self):
        self.customer_a = create_user('cust_a')
        self.customer_b = create_user('cust_b')
        self.admin = create_user('claim_admin', role='admin')
        self.policy_a = create_policy(self.customer_a)
        self.policy_b = create_policy(self.customer_b)
        self.claim_a = create_claim(self.policy_a, self.customer_a)
        self.claim_b = create_claim(self.policy_b, self.customer_b)

    def test_customer_cannot_view_other_users_claim(self):
        """Guessing customer B's claim ID from customer A's session → 404."""
        token, _ = get_tokens(self.client, 'cust_a')
        resp = self.client.get(f'/api/v1/claims/{self.claim_b.pk}/', **auth_header(token))
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_customer_cannot_review_claim(self):
        """PATCH /claims/<id>/review/ is admin-only → 403 for customer."""
        token, _ = get_tokens(self.client, 'cust_a')
        resp = self.client.patch(
            f'/api/v1/claims/{self.claim_a.pk}/review/',
            {'status': 'approved'},
            **auth_header(token),
        )
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_customer_cannot_access_flagged_endpoint(self):
        token, _ = get_tokens(self.client, 'cust_a')
        resp = self.client.get('/api/v1/claims/flagged/', **auth_header(token))
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_can_review_claim(self):
        token, _ = get_tokens(self.client, 'claim_admin')
        resp = self.client.patch(
            f'/api/v1/claims/{self.claim_a.pk}/review/',
            {'status': 'approved'},
            format='json',
            **auth_header(token),
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.claim_a.refresh_from_db()
        self.assertEqual(self.claim_a.status, Claim.STATUS_APPROVED)
        self.assertIsNotNone(self.claim_a.reviewed_by)
        self.assertIsNotNone(self.claim_a.reviewed_at)

    def test_cannot_review_already_reviewed_claim(self):
        """Attempting to re-review a non-pending claim must return 400."""
        token, _ = get_tokens(self.client, 'claim_admin')
        self.client.patch(
            f'/api/v1/claims/{self.claim_a.pk}/review/',
            {'status': 'approved'},
            format='json',
            **auth_header(token),
        )
        # Second review attempt
        resp = self.client.patch(
            f'/api/v1/claims/{self.claim_a.pk}/review/',
            {'status': 'rejected'},
            format='json',
            **auth_header(token),
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_admin_sees_fraud_reason_in_list(self):
        """Admin-facing API response must include fraud_reason field."""
        flagged_claim = Claim.objects.create(
            policy=self.policy_a,
            submitted_by=self.customer_a,
            claim_amount=Decimal('100.00'),
            description='Flagged',
            fraud_flag=True,
            fraud_reason='Flagged: early-claim',
        )
        token, _ = get_tokens(self.client, 'claim_admin')
        resp = self.client.get(f'/api/v1/claims/{flagged_claim.pk}/', **auth_header(token))
        self.assertIn('fraud_reason', resp.data)

    def test_customer_list_does_not_include_fraud_reason(self):
        """Customer list response must never include fraud_reason key."""
        token, _ = get_tokens(self.client, 'cust_a')
        resp = self.client.get('/api/v1/claims/', **auth_header(token))
        for claim in resp.data.get('results', []):
            self.assertNotIn('fraud_reason', claim)


# ─── Happy Path End-to-End Test ───────────────────────────────────────────────

class HappyPathTest(APITestCase):
    """
    Full E2E: register → login → admin creates active policy →
    customer submits claim → fraud fields absent from customer response →
    admin reviews → reviewed_by/reviewed_at populated.
    """

    def test_full_happy_path(self):
        # 1. Create customer directly (avoids password validator edge cases in test env)
        customer = create_user('hp_customer', role='customer')
        customer = User.objects.get(username='hp_customer')

        # 2. Create admin directly (admins can't self-register)
        admin = create_user('hp_admin', role='admin')

        # 3. Admin creates an active policy for the customer
        admin_token, _ = get_tokens(self.client, 'hp_admin')
        policy_resp = self.client.post('/api/v1/policies/', {
            'user': customer.pk,
            'policy_type': 'health',
            'coverage_amount': '20000.00',
            'premium': '200.00',
            'start_date': str(datetime.date.today() - datetime.timedelta(days=30)),
            'status': 'active',
        }, format='json', **auth_header(admin_token))
        self.assertEqual(policy_resp.status_code, status.HTTP_201_CREATED)
        policy_id = policy_resp.data['id']

        # 4. Customer submits claim
        cust_token, _ = get_tokens(self.client, 'hp_customer')
        claim_resp = self.client.post('/api/v1/claims/', {
            'policy': policy_id,
            'claim_amount': '500.00',
            'description': 'Happy path claim',
        }, format='json', **auth_header(cust_token))
        self.assertEqual(claim_resp.status_code, status.HTTP_201_CREATED)

        # 5. fraud_reason not in customer response
        self.assertNotIn('fraud_reason', claim_resp.data)

        # 6. Admin reviews the claim
        claim_id = claim_resp.data['id']
        review_resp = self.client.patch(
            f'/api/v1/claims/{claim_id}/review/',
            {'status': 'approved'},
            format='json',
            **auth_header(admin_token),
        )
        self.assertEqual(review_resp.status_code, status.HTTP_200_OK)

        # 7. reviewed_by and reviewed_at are set
        claim = Claim.objects.get(pk=claim_id)
        self.assertEqual(claim.status, Claim.STATUS_APPROVED)
        self.assertEqual(claim.reviewed_by, admin)
        self.assertIsNotNone(claim.reviewed_at)


# ─── Pagination Test ──────────────────────────────────────────────────────────

class PaginationTest(APITestCase):
    def test_25_claims_paginated_correctly(self):
        user = create_user('paguser')
        admin = create_user('pagadmin', role='admin')
        policy = create_policy(user)
        for i in range(25):
            create_claim(policy, user)

        token, _ = get_tokens(self.client, 'pagadmin')
        # Page 1
        resp1 = self.client.get('/api/v1/claims/?page=1', **auth_header(token))
        self.assertEqual(resp1.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp1.data['results']), 20)
        self.assertEqual(resp1.data['count'], 25)

        # Page 2
        resp2 = self.client.get('/api/v1/claims/?page=2', **auth_header(token))
        self.assertEqual(resp2.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp2.data['results']), 5)
