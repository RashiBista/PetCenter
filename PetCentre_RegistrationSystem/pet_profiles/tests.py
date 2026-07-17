from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from .models import MedicalRecord, MedicalSummary, Pet


class PetProfileTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        # role defaults to User.Role.USER on the model, matching what
        # @role_required(User.Role.USER) on every pet_profiles view expects.
        self.owner = user_model.objects.create_user(
            username="owner", password="test-pass-123",
        )
        self.other_owner = user_model.objects.create_user(
            username="other", password="test-pass-123",
        )
        self.pet = Pet.objects.create(
            owner=self.owner,
            name="Milo",
            species=Pet.Species.DOG,
            breed="Golden Retriever",
            date_of_birth=date.today() - timedelta(days=365 * 3),
            gender=Pet.Gender.MALE,
            weight_kg="30.50",
        )
        MedicalSummary.objects.create(pet=self.pet)
        self.client.force_login(self.owner)

    def test_owner_can_open_pet_profile(self):
        response = self.client.get(
            reverse("pet_profiles:detail", kwargs={"pk": self.pet.pk})
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Milo")

    def test_owner_cannot_open_someone_elses_pet(self):
        foreign_pet = Pet.objects.create(
            owner=self.other_owner, name="Luna", species=Pet.Species.CAT,
        )
        response = self.client.get(
            reverse("pet_profiles:detail", kwargs={"pk": foreign_pet.pk})
        )
        self.assertEqual(response.status_code, 404)

    def test_edit_pet_details(self):
        response = self.client.post(
            reverse("pet_profiles:edit", kwargs={"pk": self.pet.pk}),
            {
                "name": "Milo Updated", "species": Pet.Species.DOG,
                "breed": "Golden Retriever",
                "date_of_birth": self.pet.date_of_birth.isoformat(),
                "gender": Pet.Gender.MALE, "weight_kg": "31.20",
                "care_notes": "Friendly",
            },
        )
        self.assertRedirects(
            response, reverse("pet_profiles:detail", kwargs={"pk": self.pet.pk}),
        )
        self.pet.refresh_from_db()
        self.assertEqual(self.pet.name, "Milo Updated")

    def test_edit_medical_summary(self):
        response = self.client.post(
            reverse("pet_profiles:medical_summary_edit", kwargs={"pk": self.pet.pk}),
            {"current_conditions": "Seasonal allergies", "emergency_notes": "Call owner first"},
        )
        self.assertEqual(response.status_code, 302)
        self.pet.medical_summary.refresh_from_db()
        self.assertEqual(self.pet.medical_summary.current_conditions, "Seasonal allergies")

    def test_add_medical_record(self):
        response = self.client.post(
            reverse("pet_profiles:record_add", kwargs={"pk": self.pet.pk}),
            {
                "record_date": date.today().isoformat(),
                "record_type": MedicalRecord.RecordType.CHECKUP,
                "title": "Annual checkup", "description": "Healthy",
                "veterinarian": "Dr. Test",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(MedicalRecord.objects.filter(pet=self.pet, title="Annual checkup").exists())

    def test_photo_upload(self):
        tiny_gif = (
            b"GIF87a\x01\x00\x01\x00\x80\x01\x00\x00\x00\x00"
            b"ccc,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;"
        )
        upload = SimpleUploadedFile("pet.gif", tiny_gif, content_type="image/gif")
        response = self.client.post(
            reverse("pet_profiles:photo_edit", kwargs={"pk": self.pet.pk}),
            {"photo": upload},
        )
        self.assertEqual(response.status_code, 302)