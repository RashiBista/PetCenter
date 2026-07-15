from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from .models import UserProfile, VetProfile
from pet_profiles.models import Pet

User = get_user_model()


class BaseRegisterSerializer(serializers.ModelSerializer):
    """
    Shared registration fields/logic for both roles. Subclasses set
    `role` and may extend `create()` to attach a role-specific profile.
    """
    password = serializers.CharField(
        write_only=True, required=True, validators=[validate_password]
    )
    password2 = serializers.CharField(write_only=True, required=True, label='Confirm password')

    role = None  # set by subclasses (User.Role.USER / User.Role.VET)

    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'phone_number', 'password', 'password2', 'date_joined', 'role')
        read_only_fields = ('id', 'date_joined', 'role')

    def validate_email(self, value):
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError('A user with this email already exists.')
        return value

    def validate_username(self, value):
        if User.objects.filter(username__iexact=value).exists():
            raise serializers.ValidationError('A user with this username already exists.')
        return value

    def validate(self, attrs):
        if attrs.get('password') != attrs.pop('password2', None):
            raise serializers.ValidationError({'password2': "Passwords don't match."})
        return attrs

    def create(self, validated_data):
        validated_data.pop('role', None)  # role is fixed per-endpoint, never client-supplied
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            password=validated_data['password'],
            phone_number=validated_data.get('phone_number', ''),
            role=self.role,
        )
        return user


class UserRegisterSerializer(BaseRegisterSerializer):
    """
    Registration serializer for pet-owner ('user') accounts.

    Pet fields are optional at registration time — a pet owner can sign
    up without a pet yet, or add one immediately including a photo.
    Photo uploads go to Cloudinary automatically once DEFAULT_FILE_STORAGE
    is configured (see settings.py); no extra code needed here for that.
    """
    pet_name = serializers.CharField(write_only=True, required=False, allow_blank=True)
    pet_species = serializers.CharField(write_only=True, required=False, allow_blank=True)
    pet_breed = serializers.CharField(write_only=True, required=False, allow_blank=True)
    pet_photo = serializers.ImageField(write_only=True, required=False, allow_null=True)

    role = User.Role.USER

    class Meta(BaseRegisterSerializer.Meta):
        fields = BaseRegisterSerializer.Meta.fields + (
            'pet_name', 'pet_species', 'pet_breed', 'pet_photo',
        )

    def validate(self, attrs):
        attrs = super().validate(attrs)
        # If any pet field is supplied, require at least name + species
        # so we don't create a half-blank Pet record.
        pet_fields_present = any([
            attrs.get('pet_name'), attrs.get('pet_species'), attrs.get('pet_photo')
        ])
        if pet_fields_present and not (attrs.get('pet_name') and attrs.get('pet_species')):
            raise serializers.ValidationError(
                {'pet_name': 'Pet name and species are required if adding a pet during registration.'}
            )
        return attrs

    def create(self, validated_data):
        pet_name = validated_data.pop('pet_name', None)
        pet_species = validated_data.pop('pet_species', None)
        pet_breed = validated_data.pop('pet_breed', '')
        pet_photo = validated_data.pop('pet_photo', None)

        user = super().create(validated_data)
        UserProfile.objects.create(user=user)

        if pet_name and pet_species:
            Pet.objects.create(
                owner=user,
                name=pet_name,
                species=pet_species,
                breed=pet_breed,
                photo=pet_photo,
            )

        return user


class VetRegisterSerializer(BaseRegisterSerializer):
    """Registration serializer for veterinarian ('vet') accounts."""
    role = User.Role.VET

    def create(self, validated_data):
        user = super().create(validated_data)
        VetProfile.objects.create(user=user)
        return user


class UserPublicSerializer(serializers.ModelSerializer):
    """Read-only representation of a User, safe to return in API responses."""
    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'phone_number', 'role', 'date_joined')
        read_only_fields = fields


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(required=True, write_only=True)