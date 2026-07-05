from rest_framework.routers import DefaultRouter
from .views import FosterVolunteerViewSet, FosterAssignmentViewSet

router = DefaultRouter()
router.register("foster-volunteers", FosterVolunteerViewSet, basename="foster-volunteer")
router.register("foster-assignments", FosterAssignmentViewSet, basename="foster-assignment")

urlpatterns = router.urls
