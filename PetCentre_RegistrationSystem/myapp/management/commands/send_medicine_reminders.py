from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from myapp.models import Prescription, User
from notifications.services import create_notification


def _recipient_role_for(user):
    return 'vet' if user.role == User.Role.VET else 'client'


class Command(BaseCommand):
    """
    Sends "Your pet's Medicine" reminder emails the day before a
    prescription's reminder_date (set by the vet or pharmacy via the
    pharmacy dashboard). Run daily via a scheduled task, same pattern
    as send_appointment_reminders.

    Usage:
        python manage.py send_medicine_reminders
    """
    help = "Send day-before medicine reminders for prescriptions with a reminder_date set."

    def handle(self, *args, **options):
        tomorrow = timezone.localdate() + timedelta(days=1)

        due = Prescription.objects.filter(
            reminder_date=tomorrow,
            reminder_sent=False,
        ).select_related('pet', 'pet__owner')

        sent_count = 0
        for rx in due:
            owner = rx.pet.owner
            create_notification(
                recipient=owner,
                recipient_role=_recipient_role_for(owner),
                notification_type='medicine',
                title="Medicine Reminder",
                message=(
                    f"Reminder: {rx.pet.name}'s {rx.medicine_name}"
                    f"{f' ({rx.dosage})' if rx.dosage else ''} is due tomorrow, "
                    f"{rx.reminder_date:%b %d, %Y}."
                ),
                action_url="/dashboard/pet-owner/",
            )
            rx.reminder_sent = True
            rx.save(update_fields=['reminder_sent'])
            sent_count += 1

        self.stdout.write(self.style.SUCCESS(f"Sent {sent_count} medicine reminder(s)."))