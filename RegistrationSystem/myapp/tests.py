from django.test import TestCase
from django.urls import reverse

from .models import User, UserProfile, VetProfile


class RegistrationTests(TestCase):
    def _payload(self, **overrides):
        data = {
            'username': 'testuser',
            'email': 'testuser@example.com',
            'password': 'SuperSecret123!',
            'password2': 'SuperSecret123!',
        }
        data.update(overrides)
        return data

    def test_user_registration_creates_user_profile(self):
        response = self.client.post(
            reverse('register_user'), self._payload(), content_type='application/json'
        )
        self.assertEqual(response.status_code, 201)
        user = User.objects.get(username='testuser')
        self.assertEqual(user.role, User.Role.USER)
        self.assertTrue(UserProfile.objects.filter(user=user).exists())
        self.assertFalse(VetProfile.objects.filter(user=user).exists())

    def test_vet_registration_creates_vet_profile(self):
        response = self.client.post(
            reverse('register_vet'),
            self._payload(username='vetuser', email='vet@example.com'),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 201)
        user = User.objects.get(username='vetuser')
        self.assertEqual(user.role, User.Role.VET)
        self.assertTrue(VetProfile.objects.filter(user=user).exists())
        self.assertFalse(UserProfile.objects.filter(user=user).exists())

    def test_password_mismatch_rejected(self):
        response = self.client.post(
            reverse('register_user'),
            self._payload(password2='Different123!'),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 400)

    def test_duplicate_username_rejected(self):
        self.client.post(reverse('register_user'), self._payload(), content_type='application/json')
        response = self.client.post(
            reverse('register_user'),
            self._payload(email='other@example.com'),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 400)

    def test_client_cannot_set_role_directly(self):
        """Role is determined by the endpoint, not by client-supplied data."""
        response = self.client.post(
            reverse('register_user'),
            self._payload(role='vet'),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 201)
        user = User.objects.get(username='testuser')
        self.assertEqual(user.role, User.Role.USER)


class LoginAndRoleAccessTests(TestCase):
    def setUp(self):
        self.client.post(
            reverse('register_user'),
            {
                'username': 'alice',
                'email': 'alice@example.com',
                'password': 'SuperSecret123!',
                'password2': 'SuperSecret123!',
            },
            content_type='application/json',
        )
        self.client.post(
            reverse('register_vet'),
            {
                'username': 'dr_bob',
                'email': 'bob@example.com',
                'password': 'SuperSecret123!',
                'password2': 'SuperSecret123!',
            },
            content_type='application/json',
        )

    def _login(self, username, password='SuperSecret123!'):
        response = self.client.post(
            reverse('auth_login'),
            {'username': username, 'password': password},
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)
        return response.json()['access']

    def test_login_returns_role(self):
        response = self.client.post(
            reverse('auth_login'),
            {'username': 'alice', 'password': 'SuperSecret123!'},
            content_type='application/json',
        )
        self.assertEqual(response.json()['user']['role'], 'user')

    def test_invalid_credentials_rejected(self):
        response = self.client.post(
            reverse('auth_login'),
            {'username': 'alice', 'password': 'WrongPassword'},
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 401)

    def test_user_can_access_user_dashboard_not_vet_dashboard(self):
        token = self._login('alice')
        auth_header = {'HTTP_AUTHORIZATION': f'Bearer {token}'}

        ok = self.client.get(reverse('dashboard_user'), **auth_header)
        self.assertEqual(ok.status_code, 200)

        forbidden = self.client.get(reverse('dashboard_vet'), **auth_header)
        self.assertEqual(forbidden.status_code, 403)

    def test_vet_can_access_vet_dashboard_not_user_dashboard(self):
        token = self._login('dr_bob')
        auth_header = {'HTTP_AUTHORIZATION': f'Bearer {token}'}

        ok = self.client.get(reverse('dashboard_vet'), **auth_header)
        self.assertEqual(ok.status_code, 200)

        forbidden = self.client.get(reverse('dashboard_user'), **auth_header)
        self.assertEqual(forbidden.status_code, 403)

    def test_unauthenticated_request_rejected(self):
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 401)
