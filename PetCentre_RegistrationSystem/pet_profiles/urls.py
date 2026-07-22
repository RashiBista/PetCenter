from django.urls import path

from . import views

app_name = "pet_profiles"

urlpatterns = [
    path("", views.home, name="home"),
    path("new/", views.pet_create, name="create"),
    path("<uuid:pet_uuid>/", views.pet_detail, name="detail"),
    path("<uuid:pet_uuid>/edit/", views.pet_edit, name="edit"),
    path("<uuid:pet_uuid>/photo/", views.pet_photo_edit, name="photo_edit"),
    path(
        "<uuid:pet_uuid>/medical-summary/edit/",
        views.medical_summary_edit,
        name="medical_summary_edit",
    ),
    path("<uuid:pet_uuid>/records/", views.medical_records, name="records"),
    path("<uuid:pet_uuid>/records/add/", views.add_medical_record, name="record_add"),
    path("<uuid:pet_uuid>/vaccinations/add/", views.add_vaccination, name="vaccination_add"),
    path("<uuid:pet_uuid>/medications/add/", views.add_medication, name="medication_add"),
    path("<uuid:pet_uuid>/appointments/open/", views.appointment_open, name="appointment_open"),
    path("<uuid:pet_uuid>/assistant/", views.assistant_open, name="assistant_open"),
]
