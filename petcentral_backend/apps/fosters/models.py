import uuid
from django.conf import settings
from django.db import models
from apps.animals.models import Animal
from apps.shelters.models import Shelter


class FosterVolunteer(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="foster_profiles")
    shelter = models.ForeignKey(Shelter, on_delete=models.CASCADE, related_name="foster_volunteers")
    capacity = models.PositiveIntegerField(default=1)  # how many animals they can foster at once
    species_preferences = models.JSONField(default=list, blank=True)
    can_handle_medical_needs = models.BooleanField(default=False)
    can_handle_behavioral_needs = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "shelter")


class FosterAssignment(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    animal = models.ForeignKey(Animal, on_delete=models.CASCADE, related_name="foster_assignments")
    foster = models.ForeignKey(FosterVolunteer, on_delete=models.CASCADE, related_name="assignments")
    start_date = models.DateField()
    expected_end_date = models.DateField(null=True, blank=True)
    actual_end_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=15, choices=Status.choices, default=Status.ACTIVE)
    agreement_document = models.FileField(upload_to="foster_agreements/", null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
