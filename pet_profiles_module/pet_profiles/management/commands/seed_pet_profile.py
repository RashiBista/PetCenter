from datetime import date, datetime, timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone

from pet_profiles.models import (
    Appointment,
    MedicalRecord,
    MedicalSummary,
    Medication,
    Pet,
    VaccinationRecord,
)


class Command(BaseCommand):
    help = "Create demo pet profile data for local development."

    def handle(self, *args, **options):
        user_model = get_user_model()
        owner, _ = user_model.objects.get_or_create(username="demo_pet_owner")

        pet, _ = Pet.objects.get_or_create(
            owner=owner,
            name="Pet A",
            defaults={
                "species": Pet.Species.DOG,
                "breed": "Golden Retriever",
                "date_of_birth": date.today() - timedelta(days=365 * 3),
                "gender": Pet.Gender.MALE,
                "weight_kg": "32.00",
            },
        )

        summary, _ = MedicalSummary.objects.get_or_create(pet=pet)
        summary.current_conditions = (
            "Mild seasonal allergies (pollen). Managed with prescribed "
            "antihistamines during spring."
        )
        summary.save()

        Medication.objects.get_or_create(
            pet=pet,
            name="Apoquel",
            dosage="16 mg",
            defaults={"frequency": "Daily", "is_active": True},
        )

        VaccinationRecord.objects.get_or_create(
            pet=pet,
            vaccine_name="Rabies (1 Yr)",
            defaults={
                "administered_on": date.today() - timedelta(days=180),
                "next_due_on": date.today() + timedelta(days=185),
            },
        )
        VaccinationRecord.objects.get_or_create(
            pet=pet,
            vaccine_name="DHPP",
            defaults={
                "administered_on": date.today() - timedelta(days=330),
                "next_due_on": date.today() + timedelta(days=20),
            },
        )

        MedicalRecord.objects.get_or_create(
            pet=pet,
            title="Annual wellness exam",
            record_date=date.today() - timedelta(days=30),
            defaults={
                "record_type": MedicalRecord.RecordType.CHECKUP,
                "description": "Routine examination. Pet is healthy.",
                "veterinarian": "Dr. Sarah Jenkins",
            },
        )

        local_now = timezone.localtime()
        future = local_now + timedelta(days=14)
        Appointment.objects.get_or_create(
            pet=pet,
            title="Annual Wellness Exam",
            defaults={
                "starts_at": future.replace(hour=10, minute=30, second=0, microsecond=0),
                "veterinarian": "Dr. Sarah Jenkins",
                "location": "PetPro Veterinary Clinic",
            },
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"Demo profile ready. Open /pets/{pet.pk}/"
            )
        )
