import uuid
from datetime import timedelta

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


class Pet(models.Model):
    class Species(models.TextChoices):
        DOG = "dog", "Dog"
        CAT = "cat", "Cat"
        BIRD = "bird", "Bird"
        RABBIT = "rabbit", "Rabbit"
        OTHER = "other", "Other"

    class Gender(models.TextChoices):
        MALE = "male", "Male"
        FEMALE = "female", "Female"
        UNKNOWN = "unknown", "Unknown"

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="pets",
    )
    # Opaque public identifier used in every pet_profiles URL instead of
    # the sequential integer pk — otherwise a bookmarked/shared link like
    # /pets/13/ tells anyone who sees it there are (at least) 13 pets in
    # the whole system, and incrementing the number would probe for
    # others' (ownership-checked, so not viewable, but still guessable).
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    name = models.CharField(max_length=80)
    species = models.CharField(max_length=20, choices=Species.choices)
    breed = models.CharField(max_length=100, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    gender = models.CharField(
        max_length=20,
        choices=Gender.choices,
        default=Gender.UNKNOWN,
    )
    weight_kg = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True,
    )
    # NOTE: uses the project's global Cloudinary storage automatically
    # (DEFAULT_FILE_STORAGE in settings.py) — no per-field change needed.
    photo = models.ImageField(upload_to="pets/photos/", blank=True)
    care_notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name", "id"]
        indexes = [models.Index(fields=["owner", "name"])]

    def __str__(self):
        return f"{self.name} ({self.owner})"

    def clean(self):
        errors = {}
        today = timezone.localdate()
        if self.date_of_birth and self.date_of_birth > today:
            errors["date_of_birth"] = "Date of birth cannot be in the future."
        if self.weight_kg is not None and self.weight_kg <= 0:
            errors["weight_kg"] = "Weight must be greater than zero."
        if errors:
            raise ValidationError(errors)

    @property
    def age_display(self):
        if not self.date_of_birth:
            return "Age not set"

        today = timezone.localdate()
        years = today.year - self.date_of_birth.year
        birthday_passed = (today.month, today.day) >= (
            self.date_of_birth.month,
            self.date_of_birth.day,
        )
        if not birthday_passed:
            years -= 1

        if years <= 0:
            months = max(
                0,
                (today.year - self.date_of_birth.year) * 12
                + today.month
                - self.date_of_birth.month,
            )
            return f"{months} month" + ("s" if months != 1 else "")

        return f"{years} year" + ("s" if years != 1 else "")


class MedicalSummary(models.Model):
    pet = models.OneToOneField(
        Pet,
        on_delete=models.CASCADE,
        related_name="medical_summary",
    )
    current_conditions = models.TextField(blank=True)
    emergency_notes = models.TextField(blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "Medical summaries"

    def __str__(self):
        return f"Medical summary for {self.pet.name}"


class Medication(models.Model):
    pet = models.ForeignKey(
        Pet,
        on_delete=models.CASCADE,
        related_name="medications",
    )
    name = models.CharField(max_length=120)
    dosage = models.CharField(max_length=80, blank=True)
    frequency = models.CharField(max_length=100, blank=True)
    instructions = models.TextField(blank=True)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-is_active", "name"]

    def __str__(self):
        return f"{self.name} for {self.pet.name}"

    @property
    def label(self):
        parts = [self.name]
        if self.dosage:
            parts.append(self.dosage)
        return " ".join(parts)


class VaccinationRecord(models.Model):
    pet = models.ForeignKey(
        Pet,
        on_delete=models.CASCADE,
        related_name="vaccinations",
    )
    vaccine_name = models.CharField(max_length=120)
    administered_on = models.DateField(null=True, blank=True)
    next_due_on = models.DateField(null=True, blank=True)
    veterinarian = models.CharField(max_length=120, blank=True)
    notes = models.TextField(blank=True)
    reminder_sent = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["next_due_on", "-administered_on", "vaccine_name"]

    def __str__(self):
        return f"{self.vaccine_name} for {self.pet.name}"

    @property
    def status(self):
        if not self.next_due_on:
            return "valid"
        today = timezone.localdate()
        if self.next_due_on < today:
            return "overdue"
        if self.next_due_on <= today + timedelta(days=30):
            return "due_soon"
        return "valid"

    @property
    def status_label(self):
        return {
            "overdue": "Overdue",
            "due_soon": "Due Soon",
            "valid": "Valid",
        }[self.status]


class MedicalRecord(models.Model):
    class RecordType(models.TextChoices):
        CHECKUP = "checkup", "Checkup"
        TREATMENT = "treatment", "Treatment"
        LAB = "lab", "Lab result"
        SURGERY = "surgery", "Surgery"
        PRESCRIPTION = "prescription", "Prescription"
        OTHER = "other", "Other"

    pet = models.ForeignKey(
        Pet,
        on_delete=models.CASCADE,
        related_name="medical_records",
    )
    record_date = models.DateField(default=timezone.localdate)
    record_type = models.CharField(
        max_length=30,
        choices=RecordType.choices,
        default=RecordType.CHECKUP,
    )
    title = models.CharField(max_length=160)
    description = models.TextField(blank=True)
    veterinarian = models.CharField(max_length=120, blank=True)
    attachment = models.FileField(
        upload_to="pets/medical_records/",
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-record_date", "-id"]
        indexes = [models.Index(fields=["pet", "record_date"])]

    def __str__(self):
        return f"{self.title} for {self.pet.name}"