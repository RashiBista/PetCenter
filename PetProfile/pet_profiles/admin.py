from django.contrib import admin

from .models import Appointment, MedicalRecord, MedicalSummary, Pet, Prescription, Vaccination


class PrescriptionInline(admin.TabularInline):
    model = Prescription
    extra = 0


class VaccinationInline(admin.TabularInline):
    model = Vaccination
    extra = 0


@admin.register(Pet)
class PetAdmin(admin.ModelAdmin):
    list_display = ("name", "species", "breed", "gender", "weight_kg", "owner")
    list_filter = ("species", "gender")
    search_fields = ("name", "breed", "owner__username")
    inlines = [PrescriptionInline, VaccinationInline]


@admin.register(MedicalSummary)
class MedicalSummaryAdmin(admin.ModelAdmin):
    list_display = ("pet", "updated_at")
    search_fields = ("pet__name", "current_conditions", "allergies")


@admin.register(Prescription)
class PrescriptionAdmin(admin.ModelAdmin):
    list_display = ("medicine_name", "pet", "dosage", "frequency", "active")
    list_filter = ("active",)
    search_fields = ("medicine_name", "pet__name")


@admin.register(Vaccination)
class VaccinationAdmin(admin.ModelAdmin):
    list_display = ("name", "pet", "administered_date", "due_date")
    search_fields = ("name", "pet__name")


@admin.register(MedicalRecord)
class MedicalRecordAdmin(admin.ModelAdmin):
    list_display = ("title", "pet", "record_type", "record_date", "veterinarian")
    list_filter = ("record_type",)
    search_fields = ("title", "pet__name", "veterinarian")


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ("title", "pet", "start_datetime", "veterinarian", "status")
    list_filter = ("status",)
    search_fields = ("title", "pet__name", "veterinarian", "clinic")
