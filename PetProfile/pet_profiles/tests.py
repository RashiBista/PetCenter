from datetime import date, timedelta

from django.test import TestCase
from django.urls import reverse

from .models import MedicalSummary, Pet


class PetProfileTests(TestCase):
    def setUp(self):
        self.pet = Pet.objects.create(
            name="Pet A",
            species=Pet.Species.DOG,
            breed="Golden Retriever",
            date_of_birth=date.today() - timedelta(days=365 * 3),
            gender=Pet.Gender.MALE,
            weight_kg=32,
        )

    def test_summary_created_automatically(self):
        self.assertTrue(MedicalSummary.objects.filter(pet=self.pet).exists())

    def test_dashboard_loads(self):
        response = self.client.get(reverse("pet_profiles:dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Pet A")

    def test_edit_pet(self):
        response = self.client.post(
            reverse("pet_profiles:edit", args=[self.pet.pk]),
            {
                "name": "Bruno",
                "species": Pet.Species.DOG,
                "breed": "Golden Retriever",
                "date_of_birth": self.pet.date_of_birth.isoformat(),
                "gender": Pet.Gender.MALE,
                "weight_kg": "33.00",
                "microchip_number": "",
                "notes": "",
            },
        )
        self.assertRedirects(response, reverse("pet_profiles:detail", args=[self.pet.pk]))
        self.pet.refresh_from_db()
        self.assertEqual(self.pet.name, "Bruno")
