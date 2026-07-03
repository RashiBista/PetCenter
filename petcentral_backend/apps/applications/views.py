from django.utils import timezone
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.animals.models import Animal
from apps.common.permissions import IsApplicantOrShelterStaff, IsShelterStaff
from .models import AdoptionApplication, ApplicationDocument, MeetAndGreet, AdoptionRecord
from .serializers import (
    AdoptionApplicationListSerializer,
    AdoptionApplicationDetailSerializer,
    AdoptionApplicationCreateSerializer,
    ApplicationDecisionSerializer,
    ApplicationDocumentSerializer,
    MeetAndGreetSerializer,
    AdoptionRecordSerializer,
)

# Status transitions a shelter staff member is allowed to make manually.
# (Keeps the workflow from jumping e.g. straight from SUBMITTED to FINALIZED.)
ALLOWED_TRANSITIONS = {
    AdoptionApplication.Status.SUBMITTED: {
        AdoptionApplication.Status.UNDER_REVIEW, AdoptionApplication.Status.DENIED,
    },
    AdoptionApplication.Status.UNDER_REVIEW: {
        AdoptionApplication.Status.REFERENCE_CHECK, AdoptionApplication.Status.DENIED,
        AdoptionApplication.Status.MEET_AND_GREET_SCHEDULED,
    },
    AdoptionApplication.Status.REFERENCE_CHECK: {
        AdoptionApplication.Status.MEET_AND_GREET_SCHEDULED, AdoptionApplication.Status.DENIED,
        AdoptionApplication.Status.APPROVED,
    },
    AdoptionApplication.Status.MEET_AND_GREET_SCHEDULED: {
        AdoptionApplication.Status.APPROVED, AdoptionApplication.Status.DENIED,
    },
    AdoptionApplication.Status.APPROVED: {
        AdoptionApplication.Status.FINALIZED, AdoptionApplication.Status.DENIED,
    },
}


class AdoptionApplicationViewSet(viewsets.ModelViewSet):
    """
    list:    GET  /api/applications/            (adopter sees own; staff sees their shelter's)
    create:  POST /api/applications/             (adopter submits application)
    retrieve/update per object permission checks
    decide:  POST /api/applications/{id}/decide/ (shelter staff moves status forward)
    withdraw: POST /api/applications/{id}/withdraw/ (applicant cancels their own)
    finalize: POST /api/applications/{id}/finalize/ (shelter staff completes the adoption)
    """

    permission_classes = [permissions.IsAuthenticated, IsApplicantOrShelterStaff]

    def get_queryset(self):
        user = self.request.user
        qs = AdoptionApplication.objects.select_related("animal", "applicant", "animal__shelter")
        if user.role in ["shelter_staff", "shelter_admin"]:
            return qs.filter(animal__shelter__staff_memberships__user=user)
        if user.role == "platform_admin":
            return qs
        return qs.filter(applicant=user)

    def get_serializer_class(self):
        if self.action == "create":
            return AdoptionApplicationCreateSerializer
        if self.action == "list":
            return AdoptionApplicationListSerializer
        return AdoptionApplicationDetailSerializer

    @action(detail=True, methods=["post"], permission_classes=[permissions.IsAuthenticated, IsShelterStaff])
    def decide(self, request, pk=None):
        application = self.get_object()
        serializer = ApplicationDecisionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        new_status = serializer.validated_data["status"]

        allowed = ALLOWED_TRANSITIONS.get(application.status, set())
        if new_status not in allowed:
            return Response(
                {"detail": f"Cannot move application from {application.status} to {new_status}."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        application.status = new_status
        application.reviewed_by = request.user
        application.review_notes = serializer.validated_data.get("review_notes", application.review_notes)
        if new_status == AdoptionApplication.Status.DENIED:
            application.denial_reason = serializer.validated_data.get("denial_reason", "")
            application.decided_at = timezone.now()
            # Free up the animal again, and auto-reject overlap isn't done here;
            # shelter staff can review other pending applications for the same animal.
            application.animal.status = Animal.Status.AVAILABLE
            application.animal.save(update_fields=["status"])
        if new_status == AdoptionApplication.Status.APPROVED:
            application.decided_at = timezone.now()

        application.save()
        return Response(AdoptionApplicationDetailSerializer(application).data)

    @action(detail=True, methods=["post"], permission_classes=[permissions.IsAuthenticated])
    def withdraw(self, request, pk=None):
        application = self.get_object()
        if application.applicant_id != request.user.id:
            return Response({"detail": "Not your application."}, status=status.HTTP_403_FORBIDDEN)
        application.status = AdoptionApplication.Status.WITHDRAWN
        application.decided_at = timezone.now()
        application.save()

        application.animal.status = Animal.Status.AVAILABLE
        application.animal.save(update_fields=["status"])
        return Response(AdoptionApplicationDetailSerializer(application).data)

    @action(detail=True, methods=["post"], permission_classes=[permissions.IsAuthenticated, IsShelterStaff])
    def finalize(self, request, pk=None):
        application = self.get_object()
        if application.status != AdoptionApplication.Status.APPROVED:
            return Response(
                {"detail": "Only approved applications can be finalized."}, status=status.HTTP_400_BAD_REQUEST
            )

        record = AdoptionRecord.objects.create(
            application=application,
            animal=application.animal,
            adopter=application.applicant,
            adoption_fee_paid=request.data.get("adoption_fee_paid", application.animal.adoption_fee),
            contract_document=request.data.get("contract_document"),
        )

        application.status = AdoptionApplication.Status.FINALIZED
        application.save(update_fields=["status"])

        application.animal.status = Animal.Status.ADOPTED
        application.animal.save(update_fields=["status"])

        # Deny any other pending applications for the same animal
        AdoptionApplication.objects.filter(animal=application.animal).exclude(id=application.id).exclude(
            status__in=[AdoptionApplication.Status.WITHDRAWN, AdoptionApplication.Status.DENIED]
        ).update(status=AdoptionApplication.Status.DENIED, denial_reason="Animal was adopted by another applicant.")

        return Response(AdoptionRecordSerializer(record).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], permission_classes=[permissions.IsAuthenticated])
    def upload_document(self, request, pk=None):
        application = self.get_object()
        if application.applicant_id != request.user.id:
            return Response({"detail": "Not your application."}, status=status.HTTP_403_FORBIDDEN)
        serializer = ApplicationDocumentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(application=application)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], permission_classes=[permissions.IsAuthenticated, IsShelterStaff])
    def schedule_meet_and_greet(self, request, pk=None):
        application = self.get_object()
        serializer = MeetAndGreetSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(application=application)
        application.status = AdoptionApplication.Status.MEET_AND_GREET_SCHEDULED
        application.save(update_fields=["status"])
        return Response(serializer.data, status=status.HTTP_201_CREATED)
