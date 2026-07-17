from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from myapp.models import User


class APIRegisterAndLoginTests(APITestCase):
    """
    Exercises the actual REST API layer (myapp's DRF/JWT views) —
    separate from the session-based web UI tested elsewhere. Uses
    DRF's APIClient, which sends real HTTP requests through the full
    view/serializer stack, same as a real API consumer would.
    """

    def test_register_user_creates_account(self):
        url = reverse('register_user')
        response = self.client.post(url, {
            'username': 'api_new_user',
            'email': 'api_new_user@example.com',
            'password': 'RealPass123!',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(User.objects.filter(username='api_new_user').exists())

    def test_register_rejects_duplicate_username(self):
        User.objects.create_user(username='taken', email='taken@example.com', password='pass123!')
        url = reverse('register_user')
        response = self.client.post(url, {
            'username': 'taken',
            'email': 'different@example.com',
            'password': 'RealPass123!',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_token_obtain_and_use_on_protected_endpoint(self):
        User.objects.create_user(
            username='api_login_test', email='api_login_test@example.com',
            password='RealPass123!', role=User.Role.USER,
        )

        token_response = self.client.post(reverse('token_obtain_pair'), {
            'username': 'api_login_test', 'password': 'RealPass123!',
        }, format='json')
        self.assertEqual(token_response.status_code, status.HTTP_200_OK)
        self.assertIn('access', token_response.data)

        access_token = token_response.data['access']

        # Protected endpoint — should fail without a token...
        unauthenticated = self.client.get(reverse('dashboard_user'))
        self.assertEqual(unauthenticated.status_code, status.HTTP_401_UNAUTHORIZED)

        # ...and succeed with one.
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
        authenticated = self.client.get(reverse('dashboard_user'))
        self.assertEqual(authenticated.status_code, status.HTTP_200_OK)

    def test_wrong_password_rejected_at_token_endpoint(self):
        User.objects.create_user(
            username='api_wrong_pass', email='api_wrong_pass@example.com',
            password='RealPass123!', role=User.Role.USER,
        )
        response = self.client.post(reverse('token_obtain_pair'), {
            'username': 'api_wrong_pass', 'password': 'WrongPassword',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)