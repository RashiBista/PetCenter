from django.urls import path
from . import views

app_name = "chat"

urlpatterns = [
    path("", views.inbox, name="inbox"),
    path("start/<int:user_id>/", views.start_chat, name="start_chat"),
    path("room/<uuid:room_uuid>/", views.room, name="room"),
    # Old integer room links (e.g. action_urls stored on notifications
    # before the switch to opaque UUIDs) redirect to the UUID form.
    path("room/<int:room_id>/", views.room_legacy, name="room_legacy"),
    path("unread/", views.unread_count, name="unread_count"),
    
]