from django import forms

from .models import (
    Appointment,
    MedicalRecord,
    MedicalSummary,
    Medication,
    Pet,
    VaccinationRecord,
)


class StyledModelForm(forms.ModelForm):
    """Apply shared CSS classes without requiring a third-party form package."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            existing = field.widget.attrs.get("class", "")
            field.widget.attrs["class"] = f"form-control {existing}".strip()


class PetForm(StyledModelForm):
    class Meta:
        model = Pet
        fields = [
            "name",
            "species",
            "breed",
            "date_of_birth",
            "gender",
            "weight_kg",
            "care_notes",
        ]
        widgets = {
            "date_of_birth": forms.DateInput(attrs={"type": "date"}),
            "care_notes": forms.Textarea(attrs={"rows": 4}),
        }


class PetPhotoForm(StyledModelForm):
    class Meta:
        model = Pet
        fields = ["photo"]
        widgets = {
            "photo": forms.ClearableFileInput(
                attrs={"accept": "image/png,image/jpeg,image/webp"}
            )
        }

    def clean_photo(self):
        photo = self.cleaned_data.get("photo")
        if photo and photo.size > 5 * 1024 * 1024:
            raise forms.ValidationError("Photo must be 5 MB or smaller.")
        return photo


class MedicalSummaryForm(StyledModelForm):
    class Meta:
        model = MedicalSummary
        fields = ["current_conditions", "emergency_notes"]
        widgets = {
            "current_conditions": forms.Textarea(attrs={"rows": 5}),
            "emergency_notes": forms.Textarea(attrs={"rows": 4}),
        }


class MedicationForm(StyledModelForm):
    class Meta:
        model = Medication
        fields = [
            "name",
            "dosage",
            "frequency",
            "instructions",
            "start_date",
            "end_date",
            "is_active",
        ]
        widgets = {
            "start_date": forms.DateInput(attrs={"type": "date"}),
            "end_date": forms.DateInput(attrs={"type": "date"}),
            "instructions": forms.Textarea(attrs={"rows": 3}),
        }


class VaccinationRecordForm(StyledModelForm):
    class Meta:
        model = VaccinationRecord
        fields = [
            "vaccine_name",
            "administered_on",
            "next_due_on",
            "veterinarian",
            "notes",
        ]
        widgets = {
            "administered_on": forms.DateInput(attrs={"type": "date"}),
            "next_due_on": forms.DateInput(attrs={"type": "date"}),
            "notes": forms.Textarea(attrs={"rows": 3}),
        }


class MedicalRecordForm(StyledModelForm):
    class Meta:
        model = MedicalRecord
        fields = [
            "record_date",
            "record_type",
            "title",
            "description",
            "veterinarian",
            "attachment",
        ]
        widgets = {
            "record_date": forms.DateInput(attrs={"type": "date"}),
            "description": forms.Textarea(attrs={"rows": 5}),
        }


class AppointmentForm(StyledModelForm):
    starts_at = forms.DateTimeField(
        input_formats=["%Y-%m-%dT%H:%M"],
        widget=forms.DateTimeInput(
            format="%Y-%m-%dT%H:%M",
            attrs={"type": "datetime-local"},
        ),
    )

    class Meta:
        model = Appointment
        fields = [
            "title",
            "starts_at",
            "veterinarian",
            "location",
            "notes",
            "status",
        ]
        widgets = {"notes": forms.Textarea(attrs={"rows": 4})}
