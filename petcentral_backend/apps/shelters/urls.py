from rest_framework.routers import DefaultRouter
from .views import ShelterViewSet, ShelterStaffMembershipViewSet

router = DefaultRouter()
router.register("shelters", ShelterViewSet, basename="shelter")
router.register("shelter-staff", ShelterStaffMembershipViewSet, basename="shelter-staff")

urlpatterns = router.urls
