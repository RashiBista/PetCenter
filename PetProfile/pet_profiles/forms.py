from django import forms

from .models import MedicalSummary, Pet


class StyledModelForm(forms.ModelForm):
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
            "microchip_number",
            "notes",
        ]
        widgets = {
            "date_of_birth": forms.DateInput(attrs={"type": "date"}),
            "notes": forms.Textarea(attrs={"rows": 4}),
        }


class PetPhotoForm(StyledModelForm):
    class Meta:
        model = Pet
        fields = ["photo"]
        widgets = {
            "photo": forms.ClearableFileInput(attrs={"accept": "image/*"}),
        }


class MedicalSummaryForm(StyledModelForm):
    class Meta:
        model = MedicalSummary
        fields = ["current_conditions", "allergies", "medical_notes"]
        widgets = {
            "current_conditions": forms.Textarea(attrs={"rows": 4}),
            "allergies": forms.Textarea(attrs={"rows": 3}),
            "medical_notes": forms.Textarea(attrs={"rows": 5}),
        }
