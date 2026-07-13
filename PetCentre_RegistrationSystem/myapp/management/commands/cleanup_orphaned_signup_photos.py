import cloudinary.api
import cloudinary.uploader
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta


class Command(BaseCommand):
    """
    Deletes Cloudinary images tagged 'pending_signup' that are older
    than 24 hours — these are pet photos uploaded during step 1 of
    signup where the person never completed OTP verification, so the
    image was never actually attached to a real Pet record.

    Run manually or on a schedule (cron / a periodic task runner):
        python manage.py cleanup_orphaned_signup_photos
    """
    help = "Delete orphaned Cloudinary uploads from abandoned signups."

    def handle(self, *args, **options):
        cutoff = timezone.now() - timedelta(hours=24)
        deleted_count = 0

        # Cloudinary's admin API paginates; loop until no more results.
        next_cursor = None
        while True:
            response = cloudinary.api.resources(
                type='upload', prefix='pending_signups/', tags=True,
                max_results=100, next_cursor=next_cursor,
            )
            for resource in response.get('resources', []):
                if 'pending_signup' not in resource.get('tags', []):
                    continue
                created_at = timezone.datetime.fromisoformat(
                    resource['created_at'].replace('Z', '+00:00')
                )
                if created_at < cutoff:
                    cloudinary.uploader.destroy(resource['public_id'])
                    deleted_count += 1

            next_cursor = response.get('next_cursor')
            if not next_cursor:
                break

        self.stdout.write(self.style.SUCCESS(f"Deleted {deleted_count} orphaned signup photo(s)."))