from django.urls import path

from . import views

app_name = "pet_profiles"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("pets/add/", views.pet_create, name="create"),
    path("pets/<int:pk>/", views.pet_detail, name="detail"),
    path("pets/<int:pk>/edit/", views.pet_edit, name="edit"),
    path("pets/<int:pk>/photo/", views.pet_photo_update, name="photo"),
    path("pets/<int:pk>/medical-summary/", views.medical_summary_edit, name="medical_summary_edit"),
    path("pets/<int:pk>/records/", views.records_list, name="records"),
    path("pets/<int:pk>/appointments/", views.appointments_list, name="appointments"),
    path("pets/<int:pk>/assistant/", views.assistant_bridge, name="assistant"),
    path("pets/<int:pk>/open-list/", views.open_list_bridge, name="open_list"),
]
