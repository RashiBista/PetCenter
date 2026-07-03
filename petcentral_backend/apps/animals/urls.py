from rest_framework.routers import DefaultRouter
from .views import AnimalViewSet, SavedSearchViewSet, FavoriteAnimalViewSet

router = DefaultRouter()
router.register("animals", AnimalViewSet, basename="animal")
router.register("saved-searches", SavedSearchViewSet, basename="saved-search")
router.register("favorites", FavoriteAnimalViewSet, basename="favorite")

urlpatterns = router.urls
