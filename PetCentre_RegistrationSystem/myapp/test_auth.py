from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from myapp.models import IPLoginAttempt, LoginAttempt, User


class LoginLockoutTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="lockout_test", email="lockout@example.com",
            password="RealPass123!", role=User.Role.USER,
        )

    def _attempt_login(self, password):
        return self.client.post(reverse("core:pet_owner_login"), {
            "email": "lockout_test", "password": password,
        })

    def test_correct_password_logs_in(self):
        response = self._attempt_login("RealPass123!")
        self.assertEqual(response.status_code, 302)

    def test_five_failures_locks_account_even_with_correct_password(self):
        for _ in range(5):
            self._attempt_login("wrong-password")
        self.assertEqual(LoginAttempt.objects.filter(user=self.user).count(), 5)

        response = self._attempt_login("RealPass123!")  # correct, but should still be blocked
        self.assertContains(response, "Too many failed attempts")

    def test_lockout_is_per_account_not_global(self):
        other_user = User.objects.create_user(
            username="other_account", email="other@example.com",
            password="OtherPass123!", role=User.Role.USER,
        )
        for _ in range(5):
            self._attempt_login("wrong-password")  # locks lockout_test only

        response = self.client.post(reverse("core:pet_owner_login"), {
            "email": "other_account", "password": "OtherPass123!",
        })
        self.assertEqual(response.status_code, 302)  # other_account is unaffected

    def test_ip_lockout_blocks_different_accounts_from_same_ip(self):
        # 5 failures against 5 DIFFERENT accounts, same client (same IP)
        for i in range(5):
            User.objects.create_user(
                username=f"target_{i}", email=f"target_{i}@example.com",
                password="Whatever123!", role=User.Role.USER,
            )
            self.client.post(reverse("core:pet_owner_login"), {
                "email": f"target_{i}", "password": "wrong-password",
            })
        self.assertGreaterEqual(IPLoginAttempt.objects.count(), 5)

        # Even a genuinely valid, never-before-attempted account should
        # now be blocked, since the block is IP-based here.
        response = self._attempt_login("RealPass123!")
        self.assertContains(response, "Too many failed attempts")

    def test_exempt_ip_bypasses_ip_lockout(self):
        from django.test import override_settings

        with override_settings(EXEMPT_LOGIN_IPS=["127.0.0.1"]):
            for i in range(5):
                User.objects.create_user(
                    username=f"exempt_target_{i}", email=f"exempt_target_{i}@example.com",
                    password="Whatever123!", role=User.Role.USER,
                )
                self.client.post(reverse("core:pet_owner_login"), {
                    "email": f"exempt_target_{i}", "password": "wrong-password",
                })
            # IP is exempt, so this account's own login should still work fine
            response = self._attempt_login("RealPass123!")
            self.assertEqual(response.status_code, 302)