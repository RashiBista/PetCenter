from rest_framework import viewsets, permissions
from apps.common.permissions import IsShelterStaffOfObject
from .models import Shelter, ShelterStaffMembership
from .serializers import ShelterSerializer, ShelterStaffMembershipSerializer


class ShelterViewSet(viewsets.ModelViewSet):
    """Public read access to browse shelters; write access limited to that shelter's own staff."""

    queryset = Shelter.objects.filter(is_active=True)
    serializer_class = ShelterSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly, IsShelterStaffOfObject]
    lookup_field = "slug"


class ShelterStaffMembershipViewSet(viewsets.ModelViewSet):
    serializer_class = ShelterStaffMembershipSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        # Staff can see memberships only for shelters they belong to
        return ShelterStaffMembership.objects.filter(shelter__staff_memberships__user=self.request.user)
