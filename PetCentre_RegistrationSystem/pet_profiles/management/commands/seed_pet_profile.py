from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from pet_profiles.models import MedicalRecord, MedicalSummary, Medication, Pet, VaccinationRecord


class Command(BaseCommand):
    help = "Create demo pet profile data (medical records, vaccinations, etc.) for an existing pet owner."

    def add_arguments(self, parser):
        parser.add_argument(
            '--owner', type=str, default='demo_owner_lisa',
            help="Username of an existing pet-owner account to attach demo medical data to.",
        )

    def handle(self, *args, **options):
        user_model = get_user_model()
        try:
            owner = user_model.objects.get(username=options['owner'])
        except user_model.DoesNotExist:
            self.stdout.write(self.style.ERROR(
                f"User '{options['owner']}' not found — run seed_demo_data first, or pass --owner <username>."
            ))
            return

        pet = Pet.objects.filter(owner=owner).first()
        if not pet:
            self.stdout.write(self.style.ERROR(f"'{owner.username}' has no pets yet."))
            return

        summary, _ = MedicalSummary.objects.get_or_create(pet=pet)
        summary.current_conditions = "Mild seasonal allergies (pollen). Managed with prescribed antihistamines during spring."
        summary.save()

        Medication.objects.get_or_create(
            pet=pet, name="Apoquel", dosage="16 mg",
            defaults={"frequency": "Daily", "is_active": True},
        )

        VaccinationRecord.objects.get_or_create(
            pet=pet, vaccine_name="Rabies (1 Yr)",
            defaults={
                "administered_on": date.today() - timedelta(days=180),
                "next_due_on": date.today() + timedelta(days=185),
            },
        )
        VaccinationRecord.objects.get_or_create(
            pet=pet, vaccine_name="DHPP",
            defaults={
                "administered_on": date.today() - timedelta(days=330),
                "next_due_on": date.today() + timedelta(days=20),
            },
        )

        MedicalRecord.objects.get_or_create(
            pet=pet, title="Annual wellness exam", record_date=date.today() - timedelta(days=30),
            defaults={
                "record_type": MedicalRecord.RecordType.CHECKUP,
                "description": "Routine examination. Pet is healthy.",
                "veterinarian": "Dr. Sarah Jenkins",
            },
        )

        self.stdout.write(self.style.SUCCESS(f"Demo medical data ready for {pet.name}. Open /pets/{pet.pk}/"))