from rest_framework.routers import DefaultRouter
from .views import ConversationViewSet, NotificationViewSet

router = DefaultRouter()
router.register("conversations", ConversationViewSet, basename="conversation")
router.register("notifications", NotificationViewSet, basename="notification")

urlpatterns = router.urls
