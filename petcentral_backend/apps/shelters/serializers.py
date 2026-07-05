from rest_framework import serializers
from .models import Shelter, ShelterStaffMembership


class ShelterSerializer(serializers.ModelSerializer):
    class Meta:
        model = Shelter
        fields = [
            "id", "name", "slug", "description", "logo", "email", "phone_number", "website",
            "address_line1", "address_line2", "city", "state", "postal_code", "country",
            "latitude", "longitude", "is_verified", "is_active",
        ]
        read_only_fields = ["id", "is_verified"]


class ShelterStaffMembershipSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source="user.email", read_only=True)

    class Meta:
        model = ShelterStaffMembership
        fields = ["id", "shelter", "user", "user_email", "staff_role", "invited_at", "accepted_at"]
        read_only_fields = ["id", "invited_at", "accepted_at"]
