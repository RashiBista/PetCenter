from django.urls import path

from . import views

app_name = "pet_profiles"

urlpatterns = [
    path("", views.home, name="home"),
    path("new/", views.pet_create, name="create"),
    path("<int:pk>/", views.pet_detail, name="detail"),
    path("<int:pk>/edit/", views.pet_edit, name="edit"),
    path("<int:pk>/photo/", views.pet_photo_edit, name="photo_edit"),
    path(
        "<int:pk>/medical-summary/edit/",
        views.medical_summary_edit,
        name="medical_summary_edit",
    ),
    path("<int:pk>/records/", views.medical_records, name="records"),
    path(
        "<int:pk>/records/add/",
        views.add_medical_record,
        name="record_add",
    ),
    path(
        "<int:pk>/vaccinations/add/",
        views.add_vaccination,
        name="vaccination_add",
    ),
    path(
        "<int:pk>/medications/add/",
        views.add_medication,
        name="medication_add",
    ),
    path(
        "<int:pk>/appointments/open/",
        views.appointment_open,
        name="appointment_open",
    ),
    path(
        "<int:pk>/appointments/",
        views.appointment_list,
        name="appointment_list",
    ),
    path(
        "<int:pk>/appointments/add/",
        views.appointment_add,
        name="appointment_add",
    ),
    path("<int:pk>/assistant/", views.assistant_open, name="assistant_open"),
]
