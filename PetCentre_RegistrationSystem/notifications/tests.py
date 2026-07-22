from datetime import timedelta
from io import StringIO

from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone

from myapp.models import User
from notifications.models import Notification


class CleanupOldNotificationsTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="notif_owner", email="notif_owner@example.com",
            password="pass123!", role=User.Role.USER,
        )

    def _make_notification(self, age_days):
        notification = Notification.objects.create(
            recipient=self.user,
            recipient_role=Notification.RecipientRole.CLIENT,
            notification_type=Notification.NotificationType.GENERAL,
            title="Test",
            message="Test message",
        )
        # created_at is auto_now_add, so it can only be backdated via a
        # queryset update (a second write), not passed at creation time.
        Notification.objects.filter(pk=notification.pk).update(
            created_at=timezone.now() - timedelta(days=age_days)
        )
        return notification

    def test_deletes_only_notifications_older_than_retention_window(self):
        old = self._make_notification(age_days=15)
        recent = self._make_notification(age_days=13)

        call_command("cleanup_old_notifications", stdout=StringIO())

        self.assertFalse(Notification.objects.filter(pk=old.pk).exists())
        self.assertTrue(Notification.objects.filter(pk=recent.pk).exists())


class NotificationsViewPaginationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="notif_page_owner", email="notif_page@example.com",
            password="pass123!", role=User.Role.USER,
        )
        for i in range(20):
            Notification.objects.create(
                recipient=self.user,
                recipient_role=Notification.RecipientRole.CLIENT,
                notification_type=Notification.NotificationType.GENERAL,
                title=f"Notification {i}",
                message="Test message",
            )
        self.client.force_login(self.user)

    def test_first_page_shows_only_first_batch_with_view_more(self):
        response = self.client.get("/notifications/")
        self.assertEqual(len(response.context["notifications"]), 15)
        self.assertTrue(response.context["has_more"])
        self.assertContains(response, "View more")

    def test_second_page_shows_all_with_no_view_more(self):
        response = self.client.get("/notifications/?page=2")
        self.assertEqual(len(response.context["notifications"]), 20)
        self.assertFalse(response.context["has_more"])
        self.assertNotContains(response, "View more")
