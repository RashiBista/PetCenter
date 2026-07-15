from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.gis.admin import GISModelAdmin

from .models import (
    Accessory, Appointment, IPLoginAttempt, LoginAttempt, Medicine, PasswordResetOTP,
    PharmacyProfile, Prescription, SignupOTP, User, UserProfile, VetProfile,
)


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'role', 'phone_number', 'is_staff', 'is_active', 'date_joined')
    list_filter = ('role', 'is_staff', 'is_active')
    fieldsets = UserAdmin.fieldsets + (
        ('PetCentre role info', {'fields': ('role', 'phone_number')}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('PetCentre role info', {'fields': ('role', 'phone_number')}),
    )


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'address', 'created_at')
    search_fields = ('user__username', 'user__email')


@admin.register(VetProfile)
class VetProfileAdmin(GISModelAdmin):
    # GISModelAdmin (instead of plain ModelAdmin) renders `location` as
    # a clickable map widget in the admin form, so a vet's coordinates
    # can be set visually instead of typing raw lat/lng.
    list_display = ('user', 'created_at')
    search_fields = ('user__username', 'user__email')


@admin.register(PharmacyProfile)
class PharmacyProfileAdmin(GISModelAdmin):
    list_display = ('user', 'pharmacy_name', 'created_at')
    search_fields = ('user__username', 'user__email', 'pharmacy_name')


@admin.register(Medicine)
class MedicineAdmin(admin.ModelAdmin):
    # This is currently the ONLY way to create Medicine records — the
    # app itself has no add/edit form for them, only search/detail.
    list_display = ('name', 'category', 'price', 'in_stock', 'pharmacy_name', 'created_at')
    list_filter = ('in_stock', 'category')
    search_fields = ('name', 'category', 'pharmacy_name')


@admin.register(Accessory)
class AccessoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'price', 'in_stock', 'pharmacy_name', 'created_at')
    list_filter = ('in_stock', 'category')
    search_fields = ('name', 'category', 'pharmacy_name')


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ('pet', 'vet', 'scheduled_time', 'status', 'created_at')
    list_filter = ('status', 'vet')
    search_fields = ('pet__name', 'vet__username', 'reason')
    autocomplete_fields = ('pet', 'vet')


@admin.register(Prescription)
class PrescriptionAdmin(admin.ModelAdmin):
    list_display = ('medicine_name', 'pet', 'vet', 'pharmacy', 'status', 'created_at')
    list_filter = ('status',)
    search_fields = ('medicine_name', 'pet__name', 'vet__username')
    autocomplete_fields = ('pet', 'vet', 'pharmacy')


# --- Debugging/visibility only — these aren't meant to be edited by
# hand, but seeing them in admin helps diagnose OTP/lockout issues
# without needing direct DB/shell access. ---

@admin.register(PasswordResetOTP)
class PasswordResetOTPAdmin(admin.ModelAdmin):
    list_display = ('user', 'code', 'is_used', 'created_at')
    readonly_fields = ('user', 'code', 'created_at')
    search_fields = ('user__username', 'user__email')


@admin.register(SignupOTP)
class SignupOTPAdmin(admin.ModelAdmin):
    list_display = ('destination', 'channel', 'code', 'is_used', 'created_at')
    readonly_fields = ('session_key', 'channel', 'destination', 'code', 'created_at')
    search_fields = ('destination',)


@admin.register(LoginAttempt)
class LoginAttemptAdmin(admin.ModelAdmin):
    list_display = ('user', 'created_at')
    readonly_fields = ('user', 'created_at')
    search_fields = ('user__username',)


@admin.register(IPLoginAttempt)
class IPLoginAttemptAdmin(admin.ModelAdmin):
    list_display = ('ip_address', 'created_at')
    readonly_fields = ('ip_address', 'created_at')
    search_fields = ('ip_address',)