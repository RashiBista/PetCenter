from rest_framework.routers import DefaultRouter
from .views import AdoptionApplicationViewSet

router = DefaultRouter()
router.register("applications", AdoptionApplicationViewSet, basename="application")

urlpatterns = router.urls
