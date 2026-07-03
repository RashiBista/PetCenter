from rest_framework import serializers
from .models import FosterVolunteer, FosterAssignment


class FosterVolunteerSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source="user.get_full_name", read_only=True)

    class Meta:
        model = FosterVolunteer
        fields = [
            "id", "user", "user_name", "shelter", "capacity", "species_preferences",
            "can_handle_medical_needs", "can_handle_behavioral_needs", "is_active",
            "approved_at", "created_at",
        ]
        read_only_fields = ["id", "approved_at", "created_at"]


class FosterAssignmentSerializer(serializers.ModelSerializer):
    animal_name = serializers.CharField(source="animal.name", read_only=True)
    foster_name = serializers.CharField(source="foster.user.get_full_name", read_only=True)

    class Meta:
        model = FosterAssignment
        fields = [
            "id", "animal", "animal_name", "foster", "foster_name", "start_date",
            "expected_end_date", "actual_end_date", "status", "agreement_document",
            "notes", "created_at",
        ]
        read_only_fields = ["id", "created_at"]
