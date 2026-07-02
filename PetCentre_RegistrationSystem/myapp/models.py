from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """
    Custom user model for PetCentre.

    Replaces Django's default auth.User so we can attach a `role` field
    directly to the authentication record. All authentication (login,
    JWT issuance, permissions) is keyed off this model regardless of role;
    role-specific data lives in the related profile models below
    (OneToOne), keeping user and vet data cleanly separated while sharing
    a single auth/identity table.
    """

    class Role(models.TextChoices):
        USER = 'user', 'User'
        VET = 'vet', 'Veterinarian'

    role = models.CharField(
        max_length=10,
        choices=Role.choices,
        default=Role.USER,
        help_text='Determines which profile (UserProfile / VetProfile) this account owns.',
    )
    phone_number = models.CharField(max_length=20, blank=True)
    email = models.EmailField(unique=True)

    # Email is required and used as the natural unique login identifier
    # alongside username; keep username for compatibility with existing
    # AbstractUser-based auth (login still accepts username, see views.py).
    REQUIRED_FIELDS = ['email']

    def __str__(self):
        return f'{self.username} ({self.role})'

    @property
    def is_vet(self):
        return self.role == self.Role.VET

    @property
    def is_pet_owner(self):
        return self.role == self.Role.USER


class UserProfile(models.Model):
    """
    Extra profile data for the 'user' (pet owner) role.
    Created automatically alongside a User with role=USER.
    """
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='user_profile',
        limit_choices_to={'role': User.Role.USER},
    )
    address = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'UserProfile<{self.user.username}>'


class VetProfile(models.Model):
    """
    Extra profile data for the 'vet' role. Kept intentionally minimal
    for now (basic info + role only); credential/clinic fields such as
    license number, clinic name, and specialization can be added here
    later without touching the User/auth model.
    """
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='vet_profile',
        limit_choices_to={'role': User.Role.VET},
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class Pet(models.Model):
    owner = models.ForeignKey(
        'myapp.User',
        on_delete=models.CASCADE,
        related_name='pets',
        limit_choices_to={'role': User.Role.USER},
    )
    name = models.CharField(max_length=100)
    species = models.CharField(max_length=50)
    breed = models.CharField(max_length=100, blank=True)
    photo = models.ImageField(upload_to='pets/', blank=True, null=True)

    def __str__(self):
        return f"{self.name} → {self.owner.username}"
    def __str__(self):
        return f'VetProfile<{self.user.username}>'
