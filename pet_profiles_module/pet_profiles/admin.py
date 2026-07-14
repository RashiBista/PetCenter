from django.contrib import admin

from .models import (
    Appointment,
    MedicalRecord,
    MedicalSummary,
    Medication,
    Pet,
    VaccinationRecord,
)


class MedicalSummaryInline(admin.StackedInline):
    model = MedicalSummary
    extra = 0
    max_num = 1


@admin.register(Pet)
class PetAdmin(admin.ModelAdmin):
    list_display = ("name", "owner", "species", "breed", "gender", "weight_kg")
    list_filter = ("species", "gender")
    search_fields = ("name", "breed", "owner__username", "owner__email")
    inlines = [MedicalSummaryInline]


@admin.register(Medication)
class MedicationAdmin(admin.ModelAdmin):
    list_display = ("name", "pet", "dosage", "frequency", "is_active")
    list_filter = ("is_active",)
    search_fields = ("name", "pet__name")


@admin.register(VaccinationRecord)
class VaccinationRecordAdmin(admin.ModelAdmin):
    list_display = ("vaccine_name", "pet", "administered_on", "next_due_on")
    search_fields = ("vaccine_name", "pet__name")


@admin.register(MedicalRecord)
class MedicalRecordAdmin(admin.ModelAdmin):
    list_display = ("title", "pet", "record_type", "record_date", "veterinarian")
    list_filter = ("record_type",)
    search_fields = ("title", "pet__name", "veterinarian")


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ("title", "pet", "starts_at", "veterinarian", "status")
    list_filter = ("status",)
    search_fields = ("title", "pet__name", "veterinarian")
