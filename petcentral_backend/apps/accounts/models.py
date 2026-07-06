import uuid
from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """
    Custom user model. Roles determine what a user can do on the platform.
    - adopter: browses pets, submits applications
    - shelter_staff: manages one shelter's animals/applications
    - shelter_admin: full control over a shelter's account + staff
    - platform_admin: superuser-level access across all shelters
    """

    class Role(models.TextChoices):
        ADOPTER = "adopter", "Adopter"
        SHELTER_STAFF = "shelter_staff", "Shelter Staff"
        SHELTER_ADMIN = "shelter_admin", "Shelter Admin"
        PLATFORM_ADMIN = "platform_admin", "Platform Admin"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.ADOPTER)
    phone_number = models.CharField(max_length=20, blank=True)
    address_line1 = models.CharField(max_length=255, blank=True)
    address_line2 = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)
    postal_code = models.CharField(max_length=20, blank=True)
    country = models.CharField(max_length=100, blank=True)
    is_email_verified = models.BooleanField(default=False)
    profile_photo = models.ImageField(upload_to="profile_photos/", null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.get_full_name() or self.username} ({self.role})"


class AdopterProfile(models.Model):
    """
    Extended profile info specific to adopters, used to pre-fill
    applications and help shelters evaluate suitability.
    """

    class HomeType(models.TextChoices):
        HOUSE = "house", "House"
        APARTMENT = "apartment", "Apartment"
        CONDO = "condo", "Condo"
        OTHER = "other", "Other"

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="adopter_profile")
    home_type = models.CharField(max_length=20, choices=HomeType.choices, blank=True)
    has_yard = models.BooleanField(null=True, blank=True)
    owns_or_rents = models.CharField(max_length=10, choices=[("owns", "Owns"), ("rents", "Rents")], blank=True)
    landlord_name = models.CharField(max_length=255, blank=True)
    landlord_contact = models.CharField(max_length=255, blank=True)
    has_other_pets = models.BooleanField(default=False)
    other_pets_description = models.TextField(blank=True)
    has_children = models.BooleanField(default=False)
    children_ages = models.CharField(max_length=100, blank=True)
    experience_level = models.CharField(
        max_length=20,
        choices=[("first_time", "First-time owner"), ("some", "Some experience"), ("experienced", "Experienced")],
        blank=True,
    )
    vet_reference_name = models.CharField(max_length=255, blank=True)
    vet_reference_contact = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return f"AdopterProfile<{self.user.username}>"
