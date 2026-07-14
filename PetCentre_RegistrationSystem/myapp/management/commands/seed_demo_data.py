from datetime import timedelta

from django.contrib.gis.geos import Point
from django.core.management.base import BaseCommand
from django.utils import timezone

from myapp.models import (
    Accessory, Appointment, Medicine, Pet, Prescription,
    User, UserProfile, VetProfile, PharmacyProfile,
)


class Command(BaseCommand):
    """
    Populates the database with demo data for test/demo purpose. Safe to run multiple times —
    uses get_or_create throughout, so re-running just confirms
    everything's still there instead of creating duplicates.

    Usage:
        python manage.py seed_demo_data
    """
    help = "Create demo users, pets, medicine, appointments, etc. for presentations."

    def handle(self, *args, **options):
        vets = self._create_vets()
        owners = self._create_owners_and_pets()
        pharmacy = self._create_pharmacy()
        medicines = self._create_medicines()
        self._create_accessories()
        self._create_appointments(owners, vets)
        self._create_prescriptions(owners, vets, medicines)

        self.stdout.write(self.style.SUCCESS("Demo data ready."))
        self.stdout.write(self.style.SUCCESS("Login as any of these (password: DemoPass123!):"))
        for u in User.objects.filter(username__startswith='demo_'):
            self.stdout.write(f"  {u.username} ({u.get_role_display()})")

    def _create_vets(self):
        vets_data = [
            ('demo_vet_amy', 'Amy', 'Chen', 'Small Animal Medicine', 27.7172, 85.3240),   # Kathmandu-ish
            ('demo_vet_raj', 'Raj', 'Sharma', 'Surgery', 27.6710, 85.4298),
        ]
        vets = []
        for username, first, last, specialization, lat, lng in vets_data:
            user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    'email': f'{username}@example.com', 'first_name': first, 'last_name': last,
                    'role': User.Role.VET,
                },
            )
            if created:
                user.set_password('DemoPass123!')
                user.save()
            VetProfile.objects.get_or_create(
                user=user,
                defaults={'specialization': specialization, 'location': Point(lng, lat, srid=4326)},
            )
            vets.append(user)
        return vets

    def _create_owners_and_pets(self):
        owners_data = [
            ('demo_owner_lisa', 'Lisa', 'Adams', [('Buddy', 'Dog', 'Golden Retriever'), ('Milo', 'Cat', 'Tabby')]),
            ('demo_owner_sam', 'Sam', 'Patel', [('Rex', 'Dog', 'German Shepherd')]),
        ]
        owners = []
        for username, first, last, pets in owners_data:
            user, created = User.objects.get_or_create(
                username=username,
                defaults={'email': f'{username}@example.com', 'first_name': first, 'last_name': last, 'role': User.Role.USER},
            )
            if created:
                user.set_password('DemoPass123!')
                user.save()
            UserProfile.objects.get_or_create(user=user)
            for name, species, breed in pets:
                Pet.objects.get_or_create(owner=user, name=name, defaults={'species': species, 'breed': breed})
            owners.append(user)
        return owners

    def _create_pharmacy(self):
        user, created = User.objects.get_or_create(
            username='demo_pharmacy_main',
            defaults={'email': 'demo_pharmacy_main@example.com', 'role': User.Role.PHARMACY},
        )
        if created:
            user.set_password('DemoPass123!')
            user.save()
        PharmacyProfile.objects.get_or_create(user=user, defaults={'pharmacy_name': 'Main Clinic Pharmacy'})
        return user

    def _create_medicines(self):
        medicines_data = [
            ('Amoxicillin', 'Antibiotics', '250mg tablets, twice daily for bacterial infections.', 8.50),
            ('Heartgard Plus', 'Heartworm Prevention', 'Monthly chewable, weight-based dosing.', 15.00),
            ('Rimadyl', 'Pain Relief', 'For post-surgical pain and arthritis in dogs.', 22.00),
        ]
        medicines = []
        for name, category, description, price in medicines_data:
            m, _ = Medicine.objects.get_or_create(
                name=name, defaults={'category': category, 'description': description, 'price': price},
            )
            medicines.append(m)
        return medicines

    def _create_accessories(self):
        accessories_data = [
            ('Adjustable Nylon Leash', 'Leashes', 'Durable 6ft leash, fits medium to large dogs.', 12.99),
            ('Stainless Steel Bowl Set', 'Feeding', 'Set of 2 non-slip bowls.', 9.50),
            ('Grooming Brush', 'Grooming', 'De-shedding brush for short and long fur.', 14.00),
        ]
        for name, category, description, price in accessories_data:
            Accessory.objects.get_or_create(
                name=name, defaults={'category': category, 'description': description, 'price': price},
            )

    def _create_appointments(self, owners, vets):
        now = timezone.now()
        pet1 = owners[0].pets.first()
        pet2 = owners[1].pets.first() if len(owners) > 1 else owners[0].pets.last()

        Appointment.objects.get_or_create(
            pet=pet1, vet=vets[0], scheduled_time=now + timedelta(days=1, hours=2),
            defaults={'reason': 'Annual wellness check', 'status': Appointment.Status.REQUESTED},
        )
        Appointment.objects.get_or_create(
            pet=pet2, vet=vets[1], scheduled_time=now + timedelta(days=2, hours=4),
            defaults={'reason': 'Limping on rear leg', 'status': Appointment.Status.CONFIRMED},
        )
        Appointment.objects.get_or_create(
            pet=pet1, vet=vets[0], scheduled_time=now - timedelta(days=5),
            defaults={'reason': 'Vaccination', 'status': Appointment.Status.COMPLETED},
        )

    def _create_prescriptions(self, owners, vets, medicines):
        pet1 = owners[0].pets.first()
        Prescription.objects.get_or_create(
            pet=pet1, vet=vets[0], medicine_name=medicines[0].name,
            defaults={'dosage': '250mg twice daily', 'status': Prescription.Status.PENDING},
        )
        Prescription.objects.get_or_create(
            pet=pet1, vet=vets[0], medicine_name=medicines[1].name,
            defaults={'dosage': 'Monthly', 'status': Prescription.Status.PENDING},
        )