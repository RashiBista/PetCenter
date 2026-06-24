from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from .models import UserProfile, VetProfile

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
    """Registration serializer for pet-owner ('user') accounts."""
    role = User.Role.USER

    def create(self, validated_data):
        user = super().create(validated_data)
        UserProfile.objects.create(user=user)
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
