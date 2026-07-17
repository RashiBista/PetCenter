from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from myapp.models import User
from notifications.services import create_notification
from pet_profiles.models import VaccinationRecord


def _recipient_role_for(user):
    return 'vet' if user.role == User.Role.VET else 'client'


class Command(BaseCommand):
    """
    Sends "Your pet's Medicine" (vaccination) reminder emails the day
    before a VaccinationRecord's next_due_on date. When a reminder
    fires, this ALSO automatically creates next year's VaccinationRecord
    (same vaccine, due exactly 365 days later) — so yearly injections
    keep renewing themselves without a vet needing to manually re-add
    them every year.

    Run daily via a scheduled task, same pattern as
    send_appointment_reminders / send_medicine_reminders.

    Usage:
        python manage.py send_vaccination_reminders
    """
    help = "Send day-before vaccination reminders and auto-schedule next year's dose."

    def handle(self, *args, **options):
        tomorrow = timezone.localdate() + timedelta(days=1)

        due = VaccinationRecord.objects.filter(
            next_due_on=tomorrow,
            reminder_sent=False,
        ).select_related('pet', 'pet__owner')

        sent_count = 0
        renewed_count = 0
        for vaccine in due:
            owner = vaccine.pet.owner
            create_notification(
                recipient=owner,
                recipient_role=_recipient_role_for(owner),
                notification_type='medicine',
                title="Your pet's Medicine",
                message=(
                    f"Reminder: {vaccine.pet.name}'s {vaccine.vaccine_name} "
                    f"vaccination is due tomorrow, {vaccine.next_due_on:%b %d, %Y}."
                ),
                action_url=f"/pets/{vaccine.pet.pk}/records/",
            )
            vaccine.reminder_sent = True
            vaccine.save(update_fields=['reminder_sent'])
            sent_count += 1

            # Auto-renew: schedule next year's dose now, so the yearly
            # cycle continues without anyone re-entering it by hand.
            next_year_due = vaccine.next_due_on + timedelta(days=365)
            created = VaccinationRecord.objects.get_or_create(
                pet=vaccine.pet,
                vaccine_name=vaccine.vaccine_name,
                next_due_on=next_year_due,
                defaults={
                    'veterinarian': vaccine.veterinarian,
                    'notes': 'Auto-scheduled from previous year\'s dose.',
                },
            )
            if created[1]:
                renewed_count += 1

        self.stdout.write(self.style.SUCCESS(
            f"Sent {sent_count} vaccination reminder(s), auto-scheduled {renewed_count} next-year dose(s)."
        ))