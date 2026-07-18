from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from myapp.models import Appointment, User
from notifications.services import create_notification


def _recipient_role_for(user):
    return 'vet' if user.role == User.Role.VET else 'client'


class Command(BaseCommand):
    """
    Sends a reminder notification+email to BOTH the pet owner and the
    vet for any confirmed appointment happening ~24 hours from now.
    `reminder_sent` prevents this from firing more than once per
    appointment, however many times this command runs.

    Run daily via a scheduled task (cron, Docker sidecar, hosting
    platform's scheduled jobs, etc.) — same pattern as
    cleanup_orphaned_signup_photos.

    Usage:
        python manage.py send_appointment_reminders
    """
    help = "Send day-before reminders for confirmed appointments happening tomorrow."

    def handle(self, *args, **options):
        now = timezone.now()
        window_start = now + timedelta(hours=23)
        window_end = now + timedelta(hours=25)

        due = Appointment.objects.filter(
            status=Appointment.Status.CONFIRMED,
            scheduled_time__gte=window_start,
            scheduled_time__lte=window_end,
            reminder_sent=False,
        ).select_related('pet', 'pet__owner', 'vet')

        sent_count = 0
        for appt in due:
            owner = appt.pet.owner
            vet = appt.vet
            # scheduled_time comes back from the DB UTC-aware — strftime
            # formats in whatever tzinfo is attached (UTC), not
            # settings.TIME_ZONE, so it needs an explicit conversion.
            local_scheduled = timezone.localtime(appt.scheduled_time)

            create_notification(
                recipient=owner,
                recipient_role=_recipient_role_for(owner),
                notification_type='appointment',
                title="Appointment reminder",
                message=(
                    f"Reminder: {appt.pet.name}'s appointment with "
                    f"Dr. {vet.get_full_name() or vet.username} is tomorrow, "
                    f"{local_scheduled:%b %d, %Y at %I:%M %p}."
                ),
                action_url="/dashboard/pet-owner/",
            )
            create_notification(
                recipient=vet,
                recipient_role=_recipient_role_for(vet),
                notification_type='appointment',
                title="Appointment reminder",
                message=(
                    f"Reminder: you have an appointment with {appt.pet.name} "
                    f"(owner: {owner.get_full_name() or owner.username}) tomorrow, "
                    f"{local_scheduled:%b %d, %Y at %I:%M %p}."
                ),
                action_url="/dashboard/veterinary/appointments/",
            )

            appt.reminder_sent = True
            appt.save(update_fields=['reminder_sent'])
            sent_count += 1

        self.stdout.write(self.style.SUCCESS(f"Sent reminders for {sent_count} appointment(s)."))