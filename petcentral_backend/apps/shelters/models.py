import uuid
from django.conf import settings
from django.db import models


class Shelter(models.Model):
    """A rescue organization or shelter operating on the platform."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True)
    ein_or_registration_number = models.CharField(max_length=100, blank=True)
    description = models.TextField(blank=True)
    logo = models.ImageField(upload_to="shelter_logos/", null=True, blank=True)
    email = models.EmailField()
    phone_number = models.CharField(max_length=20, blank=True)
    website = models.URLField(blank=True)

    address_line1 = models.CharField(max_length=255, blank=True)
    address_line2 = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    postal_code = models.CharField(max_length=20, blank=True)
    country = models.CharField(max_length=100, default="USA")
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)

    is_verified = models.BooleanField(default=False)  # platform admin verifies legitimacy
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class ShelterStaffMembership(models.Model):
    """Links a User (with role shelter_staff/shelter_admin) to a Shelter."""

    class StaffRole(models.TextChoices):
        STAFF = "staff", "Staff"
        ADMIN = "admin", "Admin"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    shelter = models.ForeignKey(Shelter, on_delete=models.CASCADE, related_name="staff_memberships")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="shelter_memberships")
    staff_role = models.CharField(max_length=10, choices=StaffRole.choices, default=StaffRole.STAFF)
    invited_at = models.DateTimeField(auto_now_add=True)
    accepted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ("shelter", "user")

    def __str__(self):
        return f"{self.user} @ {self.shelter} ({self.staff_role})"
