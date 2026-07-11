from django.urls import path

from .views import (
    MarkAllNotificationsReadAPIView,
    MarkNotificationReadAPIView,
    NotificationCreateAPIView,
    NotificationListAPIView,
    UnreadCountAPIView,
)


app_name = "notifications"


urlpatterns = [
    path(
        "",
        NotificationListAPIView.as_view(),
        name="notification-list",
    ),
    path(
        "create/",
        NotificationCreateAPIView.as_view(),
        name="notification-create",
    ),
    path(
        "unread-count/",
        UnreadCountAPIView.as_view(),
        name="unread-count",
    ),
    path(
        "<int:notification_id>/read/",
        MarkNotificationReadAPIView.as_view(),
        name="mark-read",
    ),
    path(
        "mark-all-read/",
        MarkAllNotificationsReadAPIView.as_view(),
        name="mark-all-read",
    ),
]
