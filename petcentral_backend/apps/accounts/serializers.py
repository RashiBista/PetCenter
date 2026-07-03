from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from .models import User, AdopterProfile


class AdopterProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = AdopterProfile
        fields = [
            "home_type", "has_yard", "owns_or_rents", "landlord_name", "landlord_contact",
            "has_other_pets", "other_pets_description", "has_children", "children_ages",
            "experience_level", "vet_reference_name", "vet_reference_contact",
        ]


class UserSerializer(serializers.ModelSerializer):
    adopter_profile = AdopterProfileSerializer(required=False)

    class Meta:
        model = User
        fields = [
            "id", "username", "email", "first_name", "last_name", "role", "phone_number",
            "address_line1", "address_line2", "city", "state", "postal_code", "country",
            "profile_photo", "adopter_profile",
        ]
        read_only_fields = ["id", "role"]

    def update(self, instance, validated_data):
        profile_data = validated_data.pop("adopter_profile", None)
        instance = super().update(instance, validated_data)
        if profile_data is not None:
            AdopterProfile.objects.update_or_create(user=instance, defaults=profile_data)
        return instance


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[validate_password])

    class Meta:
        model = User
        fields = ["username", "email", "password", "first_name", "last_name", "role"]

    def validate_role(self, role):
        # Public registration can only create adopters; shelter accounts are
        # provisioned by platform admins or via a separate verified onboarding flow.
        if role and role != User.Role.ADOPTER:
            raise serializers.ValidationError("Only adopter accounts can self-register.")
        return role or User.Role.ADOPTER

    def create(self, validated_data):
        password = validated_data.pop("password")
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        AdopterProfile.objects.create(user=user)
        return user
