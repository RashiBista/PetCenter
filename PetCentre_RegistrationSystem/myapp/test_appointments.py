from datetime import timedelta

from django.core import mail
from django.test import TestCase
from django.utils import timezone

from myapp.models import Appointment, User
from notifications.models import Notification
from pet_profiles.models import Pet, VaccinationRecord


class AppointmentFlowTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(
            username="test_owner", email="owner@example.com",
            password="pass123!", role=User.Role.USER,
        )
        self.vet = User.objects.create_user(
            username="test_vet", email="vet@example.com",
            password="pass123!", role=User.Role.VET,
        )
        self.pet = Pet.objects.create(owner=self.owner, name="Rex", species=Pet.Species.DOG)

    def test_vet_confirming_appointment_notifies_owner(self):
        appt = Appointment.objects.create(
            pet=self.pet, vet=self.vet,
            scheduled_time=timezone.now() + timedelta(days=1),
        )
        self.client.force_login(self.vet)
        with self.captureOnCommitCallbacks(execute=True):
            self.client.post(f"/appointments/{appt.id}/status/", {"status": "confirmed"})

        appt.refresh_from_db()
        self.assertEqual(appt.status, Appointment.Status.CONFIRMED)
        self.assertTrue(
            Notification.objects.filter(recipient=self.owner, notification_type="appointment").exists()
        )
        self.assertEqual(len(mail.outbox), 1)  # real email actually sent (console backend in tests)

    def test_vet_cannot_confirm_someone_elses_appointment(self):
        other_vet = User.objects.create_user(
            username="other_vet", email="other_vet@example.com",
            password="pass123!", role=User.Role.VET,
        )
        appt = Appointment.objects.create(
            pet=self.pet, vet=self.vet,
            scheduled_time=timezone.now() + timedelta(days=1),
        )
        self.client.force_login(other_vet)
        self.client.post(f"/appointments/{appt.id}/status/", {"status": "confirmed"})

        appt.refresh_from_db()
        self.assertEqual(appt.status, Appointment.Status.REQUESTED)  # unchanged


class VaccinationAutoRenewalTests(TestCase):
    """
    Covers the "yearly injections auto-schedule after the current
    year's is done" behavior — the core promise of
    send_vaccination_reminders.
    """
    def setUp(self):
        self.owner = User.objects.create_user(
            username="vax_owner", email="vax_owner@example.com",
            password="pass123!", role=User.Role.USER,
        )
        self.pet = Pet.objects.create(owner=self.owner, name="Buddy", species=Pet.Species.DOG)

    def test_reminder_command_sends_email_and_schedules_next_year(self):
        from django.core.management import call_command

        due_date = timezone.localdate() + timedelta(days=1)
        vaccine = VaccinationRecord.objects.create(
            pet=self.pet, vaccine_name="Rabies", next_due_on=due_date,
        )

        with self.captureOnCommitCallbacks(execute=True):
            call_command("send_vaccination_reminders")

        vaccine.refresh_from_db()
        self.assertTrue(vaccine.reminder_sent)
        self.assertEqual(len(mail.outbox), 1)

        next_year = VaccinationRecord.objects.filter(
            pet=self.pet, vaccine_name="Rabies", next_due_on=due_date + timedelta(days=365),
        )
        self.assertTrue(next_year.exists())

    def test_reminder_not_sent_twice(self):
        from django.core.management import call_command

        due_date = timezone.localdate() + timedelta(days=1)
        VaccinationRecord.objects.create(
            pet=self.pet, vaccine_name="DHPP", next_due_on=due_date,
        )
        with self.captureOnCommitCallbacks(execute=True):
            call_command("send_vaccination_reminders")
        with self.captureOnCommitCallbacks(execute=True):
            call_command("send_vaccination_reminders")  # run twice
        self.assertEqual(len(mail.outbox), 1)  # only sent once, not duplicated