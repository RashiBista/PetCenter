from datetime import timedelta

from django.conf import settings
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
        null=True,
        blank=True,
    )
    name = models.CharField(max_length=80)
    species = models.CharField(max_length=20, choices=Species.choices, default=Species.DOG)
    breed = models.CharField(max_length=100, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=20, choices=Gender.choices, default=Gender.UNKNOWN)
    weight_kg = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    photo = models.ImageField(upload_to="pets/%Y/%m/", blank=True, null=True)
    microchip_number = models.CharField(max_length=100, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name", "id"]

    def __str__(self):
        return self.name

    @property
    def age_display(self):
        if not self.date_of_birth:
            return "Age unknown"
        today = timezone.localdate()
        years = today.year - self.date_of_birth.year
        if (today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day):
            years -= 1
        if years <= 0:
            months = max(
                0,
                (today.year - self.date_of_birth.year) * 12
                + today.month
                - self.date_of_birth.month,
            )
            return f"{months} Month{'s' if months != 1 else ''}"
        return f"{years} Year{'s' if years != 1 else ''}"


class MedicalSummary(models.Model):
    pet = models.OneToOneField(Pet, on_delete=models.CASCADE, related_name="medical_summary")
    current_conditions = models.TextField(blank=True)
    allergies = models.TextField(blank=True)
    medical_notes = models.TextField(blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "Medical summaries"

    def __str__(self):
        return f"Medical summary for {self.pet.name}"


class Prescription(models.Model):
    pet = models.ForeignKey(Pet, on_delete=models.CASCADE, related_name="prescriptions")
    medicine_name = models.CharField(max_length=120)
    dosage = models.CharField(max_length=80, blank=True)
    frequency = models.CharField(max_length=80, blank=True)
    start_date = models.DateField(default=timezone.localdate)
    end_date = models.DateField(null=True, blank=True)
    instructions = models.TextField(blank=True)
    active = models.BooleanField(default=True)

    class Meta:
        ordering = ["-active", "medicine_name"]

    def __str__(self):
        return f"{self.medicine_name} for {self.pet.name}"


class Vaccination(models.Model):
    pet = models.ForeignKey(Pet, on_delete=models.CASCADE, related_name="vaccinations")
    name = models.CharField(max_length=120)
    administered_date = models.DateField(null=True, blank=True)
    due_date = models.DateField(null=True, blank=True)
    administered_by = models.CharField(max_length=120, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["due_date", "name"]

    def __str__(self):
        return f"{self.name} for {self.pet.name}"

    @property
    def status(self):
        if not self.due_date:
            return "unknown"
        today = timezone.localdate()
        if self.due_date < today:
            return "overdue"
        if self.due_date <= today + timedelta(days=30):
            return "due_soon"
        return "valid"

    @property
    def status_label(self):
        return {
            "overdue": "Overdue",
            "due_soon": "Due Soon",
            "valid": "Valid",
            "unknown": "No Due Date",
        }[self.status]


class MedicalRecord(models.Model):
    class RecordType(models.TextChoices):
        CHECKUP = "checkup", "Checkup"
        LAB = "lab", "Lab Result"
        SURGERY = "surgery", "Surgery"
        PRESCRIPTION = "prescription", "Prescription"
        VACCINATION = "vaccination", "Vaccination"
        OTHER = "other", "Other"

    pet = models.ForeignKey(Pet, on_delete=models.CASCADE, related_name="medical_records")
    record_type = models.CharField(max_length=30, choices=RecordType.choices, default=RecordType.CHECKUP)
    title = models.CharField(max_length=160)
    description = models.TextField(blank=True)
    record_date = models.DateField(default=timezone.localdate)
    veterinarian = models.CharField(max_length=120, blank=True)
    attachment = models.FileField(upload_to="medical_records/%Y/%m/", blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-record_date", "-created_at"]

    def __str__(self):
        return f"{self.title} for {self.pet.name}"


class Appointment(models.Model):
    class Status(models.TextChoices):
        UPCOMING = "upcoming", "Upcoming"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"

    pet = models.ForeignKey(Pet, on_delete=models.CASCADE, related_name="appointments")
    title = models.CharField(max_length=160)
    start_datetime = models.DateTimeField()
    veterinarian = models.CharField(max_length=120, blank=True)
    clinic = models.CharField(max_length=160, blank=True)
    notes = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.UPCOMING)

    class Meta:
        ordering = ["start_datetime"]

    def __str__(self):
        return f"{self.title} for {self.pet.name}"
