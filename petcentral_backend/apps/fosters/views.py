from django.utils import timezone
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.animals.models import Animal
from apps.common.permissions import IsShelterStaff
from .models import FosterVolunteer, FosterAssignment
from .serializers import FosterVolunteerSerializer, FosterAssignmentSerializer


class FosterVolunteerViewSet(viewsets.ModelViewSet):
    serializer_class = FosterVolunteerSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.role in ["shelter_staff", "shelter_admin", "platform_admin"]:
            return FosterVolunteer.objects.filter(shelter__staff_memberships__user=user)
        return FosterVolunteer.objects.filter(user=user)


class FosterAssignmentViewSet(viewsets.ModelViewSet):
    serializer_class = FosterAssignmentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.role in ["shelter_staff", "shelter_admin", "platform_admin"]:
            return FosterAssignment.objects.filter(animal__shelter__staff_memberships__user=user)
        return FosterAssignment.objects.filter(foster__user=user)

    def perform_create(self, serializer):
        assignment = serializer.save()
        assignment.animal.status = Animal.Status.FOSTERED
        assignment.animal.save(update_fields=["status"])

    @action(detail=True, methods=["post"], permission_classes=[permissions.IsAuthenticated, IsShelterStaff])
    def complete(self, request, pk=None):
        assignment = self.get_object()
        assignment.status = FosterAssignment.Status.COMPLETED
        assignment.actual_end_date = timezone.now().date()
        assignment.save()
        assignment.animal.status = Animal.Status.AVAILABLE
        assignment.animal.save(update_fields=["status"])
        return Response(FosterAssignmentSerializer(assignment).data, status=status.HTTP_200_OK)
