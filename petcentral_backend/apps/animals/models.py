import uuid
from django.conf import settings
from django.db import models
from apps.shelters.models import Shelter


class Animal(models.Model):
    class Species(models.TextChoices):
        DOG = "dog", "Dog"
        CAT = "cat", "Cat"
        RABBIT = "rabbit", "Rabbit"
        BIRD = "bird", "Bird"
        SMALL_ANIMAL = "small_animal", "Small Animal"
        OTHER = "other", "Other"

    class Size(models.TextChoices):
        SMALL = "small", "Small"
        MEDIUM = "medium", "Medium"
        LARGE = "large", "Large"
        EXTRA_LARGE = "extra_large", "Extra Large"

    class Gender(models.TextChoices):
        MALE = "male", "Male"
        FEMALE = "female", "Female"
        UNKNOWN = "unknown", "Unknown"

    class EnergyLevel(models.TextChoices):
        LOW = "low", "Low"
        MEDIUM = "medium", "Medium"
        HIGH = "high", "High"

    class Status(models.TextChoices):
        AVAILABLE = "available", "Available"
        PENDING = "pending", "Pending"          # application in progress
        ON_HOLD = "on_hold", "On Hold"           # temporarily paused (e.g. medical)
        FOSTERED = "fostered", "In Foster Care"
        ADOPTED = "adopted", "Adopted"
        NOT_AVAILABLE = "not_available", "Not Available"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    shelter = models.ForeignKey(Shelter, on_delete=models.CASCADE, related_name="animals")

    name = models.CharField(max_length=100)
    species = models.CharField(max_length=20, choices=Species.choices)
    breed = models.CharField(max_length=150, blank=True)
    secondary_breed = models.CharField(max_length=150, blank=True)
    gender = models.CharField(max_length=10, choices=Gender.choices, default=Gender.UNKNOWN)
    size = models.CharField(max_length=15, choices=Size.choices, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    approximate_age_months = models.PositiveIntegerField(null=True, blank=True)
    weight_lbs = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    color = models.CharField(max_length=100, blank=True)

    description = models.TextField(blank=True)
    personality_traits = models.JSONField(default=list, blank=True)  # e.g. ["playful", "shy", "affectionate"]
    energy_level = models.CharField(max_length=10, choices=EnergyLevel.choices, blank=True)

    good_with_dogs = models.BooleanField(null=True, blank=True)
    good_with_cats = models.BooleanField(null=True, blank=True)
    good_with_children = models.BooleanField(null=True, blank=True)
    is_house_trained = models.BooleanField(null=True, blank=True)
    is_spayed_or_neutered = models.BooleanField(default=False)
    is_vaccinated = models.BooleanField(default=False)
    is_microchipped = models.BooleanField(default=False)
    special_needs = models.TextField(blank=True)
    caretaker_notes = models.TextField(blank=True)

    status = models.CharField(max_length=15, choices=Status.choices, default=Status.AVAILABLE)
    intake_date = models.DateField(auto_now_add=True)
    intake_type = models.CharField(
        max_length=20,
        choices=[("stray", "Stray"), ("surrender", "Owner Surrender"), ("transfer", "Transfer"), ("born_in_care", "Born in Care")],
        blank=True,
    )
    adoption_fee = models.DecimalField(max_digits=8, decimal_places=2, default=0)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="animals_created"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["species", "status"]),
            models.Index(fields=["shelter", "status"]),
        ]

    def __str__(self):
        return f"{self.name} ({self.species}) - {self.shelter.name}"


class AnimalPhoto(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    animal = models.ForeignKey(Animal, on_delete=models.CASCADE, related_name="photos")
    image = models.ImageField(upload_to="animal_photos/")
    is_primary = models.BooleanField(default=False)
    caption = models.CharField(max_length=255, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-is_primary", "uploaded_at"]


class MedicalRecord(models.Model):
    """Tracks vaccinations, treatments, and vet visits for an animal."""

    class RecordType(models.TextChoices):
        VACCINATION = "vaccination", "Vaccination"
        TREATMENT = "treatment", "Treatment"
        SURGERY = "surgery", "Surgery"
        CHECKUP = "checkup", "Checkup"
        SPAY_NEUTER = "spay_neuter", "Spay/Neuter"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    animal = models.ForeignKey(Animal, on_delete=models.CASCADE, related_name="medical_records")
    record_type = models.CharField(max_length=20, choices=RecordType.choices)
    description = models.CharField(max_length=255)
    date_administered = models.DateField()
    veterinarian = models.CharField(max_length=255, blank=True)
    document = models.FileField(upload_to="medical_records/", null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


class SavedSearch(models.Model):
    """Allows adopters to save search filters and get notified of matches."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="saved_searches")
    name = models.CharField(max_length=100)
    filters = models.JSONField(default=dict)  # serialized query params
    notify_by_email = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)


class FavoriteAnimal(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="favorites")
    animal = models.ForeignKey(Animal, on_delete=models.CASCADE, related_name="favorited_by")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "animal")
