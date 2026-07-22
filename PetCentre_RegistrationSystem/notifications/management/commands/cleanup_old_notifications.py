from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from notifications.models import Notification

# Notifications are meant to surface recent activity, not serve as a
# permanent log — keeping them capped stops the table (and the "view
# more" pagination on the notifications page) from growing forever.
RETENTION_DAYS = 14


class Command(BaseCommand):
    """
    Deletes notifications older than RETENTION_DAYS.

    Run daily via a scheduled task (Render cron job — see render.yaml).

    Usage:
        python manage.py cleanup_old_notifications
    """
    help = f"Delete notifications older than {RETENTION_DAYS} days."

    def handle(self, *args, **options):
        cutoff = timezone.now() - timedelta(days=RETENTION_DAYS)
        deleted_count, _ = Notification.objects.filter(created_at__lt=cutoff).delete()
        self.stdout.write(self.style.SUCCESS(
            f"Deleted {deleted_count} notification(s) older than {RETENTION_DAYS} days."
        ))
