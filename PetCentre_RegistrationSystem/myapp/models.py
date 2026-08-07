from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone
from django.contrib.gis.db.models import PointField


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
    # Uploads through the default storage backend (Cloudinary — see
    # STORAGES in settings.py), same as Pet/Medicine photos.
    # Lives on User rather than the per-role profile models since every
    # role needs one and there's nothing role-specific about it.
    profile_picture = models.ImageField(upload_to='profile_pictures/', blank=True, null=True)

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
    # Set via the browser's geolocation API ("Use my location") on the
    # Find Nearby Care page — same geography=True pattern as
    # VetProfile.location, so distance queries return real-world meters.
    location = PointField(geography=True, null=True, blank=True)

    def __str__(self):
        return f'UserProfile<{self.user.username}>'


class VetProfile(models.Model):
    """
    Extra profile data for the 'vet' role.
    """
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='vet_profile',
        limit_choices_to={'role': User.Role.VET},
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    specialization = models.CharField(max_length=150, blank=True, default="General Practice")
    # geography=True makes distance queries return real-world meters
    # (accounting for the Earth's curvature) rather than flat-plane units.
    location = PointField(geography=True, null=True, blank=True)
    # The human-readable address text behind `location` — Nominatim's
    # display_name for whichever suggestion the vet picked in Settings
    # (see core.views.update_my_location_view). `location` alone is only
    # ever coordinates; without this there'd be nothing readable to show
    # a pet owner browsing Find Nearby Care.
    clinic_address = models.CharField(max_length=255, blank=True)
    # Displayed in NRS on the appointment booking page. Set per-vet via
    # Django admin — nullable so an unset fee just renders as "—" instead
    # of a misleading 0.
    consultation_fee = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    # Standalone pet pharmacies aren't really a thing pet owners look
    # for locally — medicine is dispensed by the vet directly, or
    # sourced from a wholesale veterinary pharmaceutical supplier
    # ("vetpharma") the vet works with. Optional free text; blank means
    # the vet dispenses in-house rather than through a named supplier.
    # Shown wherever an appointment previously showed a separate
    # pharmacy's name.
    pharma_partner_name = models.CharField(max_length=150, blank=True)

    def __str__(self):
        return f'VetProfile<{self.user.username}>'


#  myapp.Pet has been removed entirely — superseded by
# pet_profiles.Pet (richer: DOB, gender, weight, care notes, medical
# summary/records/vaccinations/medications). Appointment below now
# references 'pet_profiles.Pet' instead.


class Appointment(models.Model):
    class Status(models.TextChoices):
        REQUESTED = 'requested', 'Requested'
        CONFIRMED = 'confirmed', 'Confirmed'
        COMPLETED = 'completed', 'Completed'
        CANCELLED = 'cancelled', 'Cancelled'

    pet = models.ForeignKey(
        'pet_profiles.Pet', on_delete=models.CASCADE, related_name='appointments',
    )
    vet = models.ForeignKey(
        'myapp.User', on_delete=models.CASCADE, related_name='vet_appointments',
        limit_choices_to={'role': User.Role.VET},
    )
    scheduled_time = models.DateTimeField()
    reason = models.CharField(max_length=200, blank=True)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.REQUESTED)
    reminder_sent = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['scheduled_time']

    def __str__(self):
        # scheduled_time is stored UTC-aware — strftime formats it in
        # whatever tzinfo is attached to the object itself (UTC, as
        # fetched from the DB), not settings.TIME_ZONE, so it needs an
        # explicit localtime() conversion first.
        local_time = timezone.localtime(self.scheduled_time)
        return f"{self.pet.name} with Dr. {self.vet.username} @ {local_time:%b %d, %I:%M %p}"

    @property
    def owner(self):
        return self.pet.owner

    @property
    def is_paid(self):
        """
        Whether this appointment's consultation fee has been settled —
        either through Khalti or a vet/owner manually marking it paid
        (see core.views.initiate_khalti_payment_view and
        mark_payment_paid_view). Verified after the visit happens, not
        before — this never gates confirmation or chat (see
        chat.views.start_chat). A vet with no consultation_fee set has
        nothing to charge for, so those appointments count as paid
        immediately.
        """
        vet_profile = getattr(self.vet, 'vet_profile', None)
        if not vet_profile or not vet_profile.consultation_fee:
            return True
        return hasattr(self, 'payment') and self.payment.status == Payment.Status.COMPLETED


class Payment(models.Model):
    """
    One payment record for an appointment's consultation fee — either a
    Khalti ePayment transaction, or a vet/owner manually marking a fee
    as received (e.g. paid in cash at the clinic), tracked identically
    otherwise. Retried Khalti attempts reuse this same row (see
    core.views.initiate_khalti_payment_view) rather than piling up
    duplicate rows per attempt — only the latest attempt matters.
    """
    class Status(models.TextChoices):
        INITIATED = 'initiated', 'Initiated'
        COMPLETED = 'completed', 'Completed'
        FAILED = 'failed', 'Failed'

    class Method(models.TextChoices):
        KHALTI = 'khalti', 'Khalti'
        MANUAL = 'manual', 'Manual'

    appointment = models.OneToOneField(
        'myapp.Appointment', on_delete=models.CASCADE, related_name='payment',
    )
    # Only Khalti payments have a pidx — manual ones have nothing to
    # look up against an external gateway.
    pidx = models.CharField(max_length=100, unique=True, null=True, blank=True)
    method = models.CharField(max_length=10, choices=Method.choices, default=Method.KHALTI)
    amount = models.DecimalField(max_digits=8, decimal_places=2)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.INITIATED)
    khalti_transaction_id = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'Payment<appointment={self.appointment_id}> {self.status}'


class VetAvailability(models.Model):
    """
    A single date+time slot a vet has explicitly opened up for booking.
    Manually managed by the vet (see core.vet_availability_view) — replaces
    the old app-wide static date/time list every vet shared regardless of
    their real schedule. A slot stays "open" here even once booked; the
    booking flow instead checks for a non-cancelled Appointment at that
    exact vet+time to decide availability, so a cancellation naturally
    reopens the slot without needing to recreate the row.
    """
    vet = models.ForeignKey(
        'myapp.User', on_delete=models.CASCADE, related_name='availability_slots',
        limit_choices_to={'role': User.Role.VET},
    )
    date = models.DateField()
    time = models.TimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['date', 'time']
        unique_together = ('vet', 'date', 'time')

    def __str__(self):
        return f'{self.vet.username} available {self.date} {self.time}'



class PasswordResetOTP(models.Model):
    user = models.ForeignKey(
        'myapp.User', on_delete=models.CASCADE, related_name='reset_otps',
    )
    code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    is_used = models.BooleanField(default=False)

    def is_valid(self):
        if self.is_used:
            return False
        return (timezone.now() - self.created_at).total_seconds() < 600  # 10 minutes

    def __str__(self):
        return f"OTP for {self.user.username} ({'used' if self.is_used else 'active'})"


class Medicine(models.Model):
    name = models.CharField(max_length=150)
    category = models.CharField(max_length=100, blank=True)
    description = models.TextField(blank=True)
    dosage_info = models.TextField(blank=True)
    price = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    in_stock = models.BooleanField(default=True)
    photo = models.ImageField(upload_to='medicines/', blank=True, null=True)
    pharmacy_name = models.CharField(max_length=150, blank=True, default="Main Clinic Pharmacy")
    pharmacy_contact = models.CharField(max_length=50, blank=True)
    pharmacy_hours = models.CharField(max_length=100, blank=True, default="Mon-Fri: 8am - 6pm")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class SignupOTP(models.Model):
    """
    OTP verification sent DURING signup, before the account exists.
    Unlike PasswordResetOTP, there's no `user` FK yet — the signup
    form data lives in the session (see core/views.py) until this
    code is verified, so abandoned signups never create orphaned
    unverified User rows.
    """
    class Channel(models.TextChoices):
        EMAIL = 'email', 'Email'
        PHONE = 'phone', 'Phone'

    session_key = models.CharField(max_length=40)
    channel = models.CharField(max_length=10, choices=Channel.choices)
    destination = models.CharField(max_length=150)
    code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    is_used = models.BooleanField(default=False)

    def is_valid(self):
        if self.is_used:
            return False
        return (timezone.now() - self.created_at).total_seconds() < 600

    def __str__(self):
        return f"Signup OTP for {self.destination} ({'used' if self.is_used else 'active'})"


class LoginAttempt(models.Model):
    """
    Tracks failed login attempts (per account) for lockout purposes.
    Only failed attempts count toward the limit.
    """
    user = models.ForeignKey(
        'myapp.User', on_delete=models.CASCADE, related_name='login_attempts',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=['user', 'created_at'])]


class IPLoginAttempt(models.Model):
    """
    Tracks failed login attempts by IP address, independent of which
    username/email was targeted — closes the gap where hammering many
    different usernames from the same machine wasn't rate-limited.
    """
    ip_address = models.GenericIPAddressField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=['ip_address', 'created_at'])]