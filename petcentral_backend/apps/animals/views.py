from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets, permissions, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.common.permissions import IsShelterStaffOfObject, IsShelterStaff
from .models import Animal, AnimalPhoto, MedicalRecord, SavedSearch, FavoriteAnimal
from .filters import AnimalFilter
from .serializers import (
    AnimalListSerializer,
    AnimalDetailSerializer,
    AnimalWriteSerializer,
    AnimalPhotoSerializer,
    MedicalRecordSerializer,
    SavedSearchSerializer,
    FavoriteAnimalSerializer,
)


class AnimalViewSet(viewsets.ModelViewSet):
    """
    list:   GET  /api/animals/                 (public browse/search)
    retrieve: GET /api/animals/{id}/            (public detail page)
    create: POST /api/animals/                 (shelter staff only)
    update/partial_update/destroy               (shelter staff of that animal's shelter only)
    favorite: POST /api/animals/{id}/favorite/  (authenticated adopters)
    """

    queryset = Animal.objects.select_related("shelter").prefetch_related("photos", "medical_records")
    permission_classes = [permissions.IsAuthenticatedOrReadOnly, IsShelterStaffOfObject]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = AnimalFilter
    search_fields = ["name", "breed", "description"]
    ordering_fields = ["intake_date", "adoption_fee", "approximate_age_months"]

    def get_queryset(self):
        qs = super().get_queryset()
        # Public users only ever see available/pending/fostered animals, never drafts/removed
        if not (self.request.user.is_authenticated and self.request.user.role in ["shelter_staff", "shelter_admin", "platform_admin"]):
            qs = qs.exclude(status=Animal.Status.NOT_AVAILABLE)
        return qs

    def get_serializer_class(self):
        if self.action == "list":
            return AnimalListSerializer
        if self.action in ["create", "update", "partial_update"]:
            return AnimalWriteSerializer
        return AnimalDetailSerializer

    def perform_create(self, serializer):
        # Ensure the creating user actually belongs to the shelter they're posting to
        shelter = serializer.validated_data["shelter"]
        if not shelter.staff_memberships.filter(user=self.request.user).exists():
            raise permissions.PermissionDenied("You are not a staff member of this shelter.")
        serializer.save()

    @action(detail=True, methods=["post"], permission_classes=[permissions.IsAuthenticated])
    def favorite(self, request, pk=None):
        animal = self.get_object()
        fav, created = FavoriteAnimal.objects.get_or_create(user=request.user, animal=animal)
        if not created:
            fav.delete()
            return Response({"favorited": False}, status=status.HTTP_200_OK)
        return Response({"favorited": True}, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], permission_classes=[IsShelterStaff])
    def upload_photo(self, request, pk=None):
        animal = self.get_object()
        serializer = AnimalPhotoSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(animal=animal)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], permission_classes=[IsShelterStaff])
    def add_medical_record(self, request, pk=None):
        animal = self.get_object()
        serializer = MedicalRecordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(animal=animal)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class SavedSearchViewSet(viewsets.ModelViewSet):
    serializer_class = SavedSearchSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return SavedSearch.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class FavoriteAnimalViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = FavoriteAnimalSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return FavoriteAnimal.objects.filter(user=self.request.user).select_related("animal")
