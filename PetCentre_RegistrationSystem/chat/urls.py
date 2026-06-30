from django.urls import path
from . import views

app_name = "chat"

urlpatterns = [
    path("", views.Inbox.as_view(), name="inbox"),
    path("start/<int:user_id>/", views.start_chat, name="start_chat"),
    path("room/<int:room_id>/", views.room, name="room"),
    path("unread/", views.unread_count, name="unread_count"),
]