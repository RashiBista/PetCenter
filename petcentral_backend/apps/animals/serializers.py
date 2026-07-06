from rest_framework import serializers
from .models import Animal, AnimalPhoto, MedicalRecord, SavedSearch, FavoriteAnimal


class AnimalPhotoSerializer(serializers.ModelSerializer):
    class Meta:
        model = AnimalPhoto
        fields = ["id", "image", "is_primary", "caption", "uploaded_at"]


class MedicalRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = MedicalRecord
        fields = ["id", "record_type", "description", "date_administered", "veterinarian", "document", "notes"]


class AnimalListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for browse/search result grids."""

    primary_photo = serializers.SerializerMethodField()
    shelter_name = serializers.CharField(source="shelter.name", read_only=True)
    shelter_city = serializers.CharField(source="shelter.city", read_only=True)
    shelter_state = serializers.CharField(source="shelter.state", read_only=True)

    class Meta:
        model = Animal
        fields = [
            "id", "name", "species", "breed", "gender", "size",
            "approximate_age_months", "status", "adoption_fee",
            "primary_photo", "shelter_name", "shelter_city", "shelter_state",
        ]

    def get_primary_photo(self, obj):
        photo = obj.photos.filter(is_primary=True).first() or obj.photos.first()
        if photo:
            request = self.context.get("request")
            url = photo.image.url
            return request.build_absolute_uri(url) if request else url
        return None


class AnimalDetailSerializer(serializers.ModelSerializer):
    """Full profile serializer for a single animal's page."""

    photos = AnimalPhotoSerializer(many=True, read_only=True)
    medical_records = MedicalRecordSerializer(many=True, read_only=True)
    shelter_name = serializers.CharField(source="shelter.name", read_only=True)

    class Meta:
        model = Animal
        fields = [
            "id", "shelter", "shelter_name", "name", "species", "breed", "secondary_breed",
            "gender", "size", "date_of_birth", "approximate_age_months", "weight_lbs", "color",
            "description", "personality_traits", "energy_level",
            "good_with_dogs", "good_with_cats", "good_with_children",
            "is_house_trained", "is_spayed_or_neutered", "is_vaccinated", "is_microchipped",
            "special_needs", "caretaker_notes", "status", "intake_date", "intake_type",
            "adoption_fee", "photos", "medical_records", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class AnimalWriteSerializer(serializers.ModelSerializer):
    """Used by shelter staff to create/update an animal listing."""

    class Meta:
        model = Animal
        exclude = ["created_by"]

    def create(self, validated_data):
        request = self.context["request"]
        validated_data["created_by"] = request.user
        return super().create(validated_data)


class SavedSearchSerializer(serializers.ModelSerializer):
    class Meta:
        model = SavedSearch
        fields = ["id", "name", "filters", "notify_by_email", "created_at"]
        read_only_fields = ["id", "created_at"]


class FavoriteAnimalSerializer(serializers.ModelSerializer):
    animal_detail = AnimalListSerializer(source="animal", read_only=True)

    class Meta:
        model = FavoriteAnimal
        fields = ["id", "animal", "animal_detail", "created_at"]
        read_only_fields = ["id", "created_at"]
