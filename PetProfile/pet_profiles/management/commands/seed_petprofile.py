from datetime import datetime, time, timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone

from pet_profiles.models import Appointment, MedicalRecord, MedicalSummary, Pet, Prescription, Vaccination


class Command(BaseCommand):
    help = "Create a complete demo pet profile."

    def add_arguments(self, parser):
        parser.add_argument(
            "--username",
            help="Assign the demo pet to this existing Django username.",
        )

    def handle(self, *args, **options):
        owner = None
        username = options.get("username")
        if username:
            User = get_user_model()
            try:
                owner = User.objects.get(username=username)
            except User.DoesNotExist:
                self.stderr.write(self.style.ERROR(f"User '{username}' does not exist."))
                return

        today = timezone.localdate()
        try:
            birth_date = today.replace(year=today.year - 3)
        except ValueError:
            birth_date = today.replace(year=today.year - 3, day=28)
        pet, _ = Pet.objects.get_or_create(
            owner=owner,
            name="Pet A",
            defaults={
                "species": Pet.Species.DOG,
                "breed": "Golden Retriever",
                "date_of_birth": birth_date,
                "gender": Pet.Gender.MALE,
                "weight_kg": 32,
                "microchip_number": "DEMO-001",
            },
        )

        summary, _ = MedicalSummary.objects.get_or_create(pet=pet)
        summary.current_conditions = (
            "Mild seasonal allergies caused by pollen. Managed with prescribed "
            "antihistamines during spring."
        )
        summary.allergies = "Pollen"
        summary.medical_notes = "Monitor scratching and watery eyes during seasonal changes."
        summary.save()

        Prescription.objects.get_or_create(
            pet=pet,
            medicine_name="Apoquel",
            dosage="16 mg",
            defaults={
                "frequency": "Daily",
                "start_date": today - timedelta(days=30),
                "instructions": "Give with food.",
                "active": True,
            },
        )

        Vaccination.objects.get_or_create(
            pet=pet,
            name="Rabies (1 Yr)",
            defaults={
                "administered_date": today - timedelta(days=170),
                "due_date": today + timedelta(days=195),
                "administered_by": "Dr. Sarah Jenkins",
            },
        )
        Vaccination.objects.get_or_create(
            pet=pet,
            name="DHPP",
            defaults={
                "administered_date": today - timedelta(days=335),
                "due_date": today + timedelta(days=20),
                "administered_by": "Dr. Sarah Jenkins",
            },
        )

        MedicalRecord.objects.get_or_create(
            pet=pet,
            title="Annual wellness check",
            record_date=today - timedelta(days=160),
            defaults={
                "record_type": MedicalRecord.RecordType.CHECKUP,
                "description": "Routine examination. Weight and vital signs were normal.",
                "veterinarian": "Sarah Jenkins",
            },
        )
        MedicalRecord.objects.get_or_create(
            pet=pet,
            title="Seasonal allergy consultation",
            record_date=today - timedelta(days=45),
            defaults={
                "record_type": MedicalRecord.RecordType.PRESCRIPTION,
                "description": "Apoquel prescribed for seasonal itching.",
                "veterinarian": "Sarah Jenkins",
            },
        )

        appointment_date = today + timedelta(days=28)
        appointment_dt = timezone.make_aware(datetime.combine(appointment_date, time(10, 30)))
        Appointment.objects.get_or_create(
            pet=pet,
            title="Annual Wellness Exam",
            defaults={
                "start_datetime": appointment_dt,
                "veterinarian": "Sarah Jenkins",
                "clinic": "PetCentre Veterinary Clinic",
                "notes": "Bring vaccination documents.",
                "status": Appointment.Status.UPCOMING,
            },
        )

        self.stdout.write(self.style.SUCCESS(f"Demo profile created for {pet.name} with ID {pet.pk}."))
