from rest_framework import serializers
from apps.animals.models import Animal
from .models import AdoptionApplication, ApplicationDocument, MeetAndGreet, AdoptionRecord


class ApplicationDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = ApplicationDocument
        fields = ["id", "document_type", "file", "uploaded_at"]


class MeetAndGreetSerializer(serializers.ModelSerializer):
    class Meta:
        model = MeetAndGreet
        fields = ["id", "scheduled_at", "location", "is_home_visit", "status", "notes"]


class AdoptionApplicationListSerializer(serializers.ModelSerializer):
    animal_name = serializers.CharField(source="animal.name", read_only=True)
    animal_photo = serializers.SerializerMethodField()
    applicant_name = serializers.CharField(source="applicant.get_full_name", read_only=True)

    class Meta:
        model = AdoptionApplication
        fields = [
            "id", "animal", "animal_name", "animal_photo",
            "applicant", "applicant_name", "status", "submitted_at",
        ]

    def get_animal_photo(self, obj):
        photo = obj.animal.photos.filter(is_primary=True).first()
        return photo.image.url if photo else None


class AdoptionApplicationDetailSerializer(serializers.ModelSerializer):
    documents = ApplicationDocumentSerializer(many=True, read_only=True)
    meet_and_greets = MeetAndGreetSerializer(many=True, read_only=True)
    animal_name = serializers.CharField(source="animal.name", read_only=True)
    applicant_name = serializers.CharField(source="applicant.get_full_name", read_only=True)

    class Meta:
        model = AdoptionApplication
        fields = [
            "id", "animal", "animal_name", "applicant", "applicant_name", "status",
            "household_info", "reason_for_adopting", "availability_for_visit",
            "reviewed_by", "review_notes", "denial_reason",
            "documents", "meet_and_greets",
            "submitted_at", "updated_at", "decided_at",
        ]
        read_only_fields = [
            "id", "status", "reviewed_by", "review_notes", "denial_reason",
            "submitted_at", "updated_at", "decided_at",
        ]


class AdoptionApplicationCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = AdoptionApplication
        fields = ["animal", "household_info", "reason_for_adopting", "availability_for_visit"]

    def validate_animal(self, animal):
        if animal.status != Animal.Status.AVAILABLE:
            raise serializers.ValidationError("This animal is not currently available for adoption.")
        return animal

    def validate(self, attrs):
        request = self.context["request"]
        animal = attrs["animal"]
        if AdoptionApplication.objects.filter(
            animal=animal,
            applicant=request.user,
            status__in=[
                AdoptionApplication.Status.SUBMITTED,
                AdoptionApplication.Status.UNDER_REVIEW,
                AdoptionApplication.Status.REFERENCE_CHECK,
                AdoptionApplication.Status.MEET_AND_GREET_SCHEDULED,
            ],
        ).exists():
            raise serializers.ValidationError("You already have an active application for this animal.")
        return attrs

    def create(self, validated_data):
        request = self.context["request"]
        validated_data["applicant"] = request.user
        application = super().create(validated_data)

        # Move the animal into "pending" so other applicants see accurate status
        animal = application.animal
        animal.status = Animal.Status.PENDING
        animal.save(update_fields=["status"])
        return application


class ApplicationDecisionSerializer(serializers.Serializer):
    """Used by shelter staff to approve/deny/move an application through its workflow."""

    status = serializers.ChoiceField(choices=AdoptionApplication.Status.choices)
    review_notes = serializers.CharField(required=False, allow_blank=True)
    denial_reason = serializers.CharField(required=False, allow_blank=True)


class AdoptionRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = AdoptionRecord
        fields = ["id", "application", "animal", "adopter", "adoption_fee_paid", "contract_document", "finalized_at"]
        read_only_fields = ["id", "finalized_at"]
