from urllib.parse import urlencode

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Prefetch
from django.http import Http404, HttpResponseRedirect
from django.shortcuts import redirect, render
from django.urls import NoReverseMatch, reverse
from django.utils import timezone

from myapp.decorators import role_required
from myapp.models import Appointment as RealAppointment, User

from .forms import (
    MedicalRecordForm,
    MedicalSummaryForm,
    MedicationForm,
    PetForm,
    PetPhotoForm,
    VaccinationRecordForm,
)
from .models import MedicalRecord, MedicalSummary, Medication, Pet, VaccinationRecord
from .services import owned_pet_or_404, owner_for_request

LOGIN_URL = 'core:pet_owner_login'


@login_required(login_url=LOGIN_URL)
@role_required(User.Role.USER)
def home(request):
    owner = owner_for_request(request)
    first_pet = Pet.objects.filter(owner=owner).first()
    if first_pet:
        return redirect("pet_profiles:detail", pet_uuid=first_pet.uuid)
    return redirect("pet_profiles:create")


@login_required(login_url=LOGIN_URL)
@role_required(User.Role.USER)
def pet_create(request):
    owner = owner_for_request(request)
    if request.method == "POST":
        form = PetForm(request.POST)
        if form.is_valid():
            pet = form.save(commit=False)
            pet.owner = owner
            pet.save()
            MedicalSummary.objects.get_or_create(pet=pet)
            messages.success(request, f"{pet.name}'s profile was created.")
            return redirect("pet_profiles:detail", pet_uuid=pet.uuid)
    else:
        form = PetForm()

    return render(
        request,
        "pet_profiles/form_page.html",
        {
            "form": form,
            "page_title": "Add another pet",
            "submit_label": "Create pet profile",
            "cancel_url": reverse("pet_profiles:home"),
        },
    )


@login_required(login_url=LOGIN_URL)
@role_required(User.Role.USER)
def pet_detail(request, pet_uuid):
    owner = owner_for_request(request)
    pet = (
        Pet.objects.filter(uuid=pet_uuid, owner=owner)
        .prefetch_related(
            Prefetch(
                "medications",
                queryset=Medication.objects.filter(is_active=True),
                to_attr="active_medications",
            ),
            "vaccinations",
        )
        .first()
    )
    if pet is None:
        raise Http404("Pet not found")

    summary, _ = MedicalSummary.objects.get_or_create(pet=pet)
    # Real appointment system — vet-linked, confirm/cancel-able, notifies
    # the owner — not the module's own removed local Appointment model.
    upcoming = (
        RealAppointment.objects.filter(
            pet=pet,
            scheduled_time__gte=timezone.now(),
            status__in=[RealAppointment.Status.REQUESTED, RealAppointment.Status.CONFIRMED],
        )
        .select_related('vet')
        .order_by('scheduled_time')
        .first()
    )
    pets = Pet.objects.filter(owner=owner).only("id", "uuid", "name", "photo")

    return render(
        request,
        "pet_profiles/pet_detail.html",
        {
            "pet": pet,
            "pets": pets,
            "summary": summary,
            "vaccinations": pet.vaccinations.all()[:2],
            "upcoming": upcoming,
        },
    )


@login_required(login_url=LOGIN_URL)
@role_required(User.Role.USER)
def pet_edit(request, pet_uuid):
    pet = owned_pet_or_404(request, pet_uuid)
    if request.method == "POST":
        form = PetForm(request.POST, instance=pet)
        if form.is_valid():
            form.save()
            messages.success(request, "Pet details updated.")
            return redirect("pet_profiles:detail", pet_uuid=pet.uuid)
    else:
        form = PetForm(instance=pet)

    return render(
        request,
        "pet_profiles/form_page.html",
        {
            "form": form,
            "pet": pet,
            "page_title": f"Edit {pet.name}",
            "submit_label": "Save changes",
            "cancel_url": reverse("pet_profiles:detail", kwargs={"pet_uuid": pet.uuid}),
        },
    )


@login_required(login_url=LOGIN_URL)
@role_required(User.Role.USER)
def pet_photo_edit(request, pet_uuid):
    pet = owned_pet_or_404(request, pet_uuid)
    if request.method == "POST":
        form = PetPhotoForm(request.POST, request.FILES, instance=pet)
        if form.is_valid():
            form.save()
            messages.success(request, "Pet photo updated.")
            return redirect("pet_profiles:detail", pet_uuid=pet.uuid)
    else:
        form = PetPhotoForm(instance=pet)

    return render(
        request,
        "pet_profiles/photo_form.html",
        {"form": form, "pet": pet},
    )


@login_required(login_url=LOGIN_URL)
@role_required(User.Role.USER)
def medical_summary_edit(request, pet_uuid):
    pet = owned_pet_or_404(request, pet_uuid)
    summary, _ = MedicalSummary.objects.get_or_create(pet=pet)
    if request.method == "POST":
        form = MedicalSummaryForm(request.POST, instance=summary)
        if form.is_valid():
            form.save()
            messages.success(request, "Medical summary updated.")
            return redirect("pet_profiles:detail", pet_uuid=pet.uuid)
    else:
        form = MedicalSummaryForm(instance=summary)

    return render(
        request,
        "pet_profiles/form_page.html",
        {
            "form": form,
            "pet": pet,
            "page_title": "Edit medical summary",
            "submit_label": "Save medical summary",
            "cancel_url": reverse("pet_profiles:detail", kwargs={"pet_uuid": pet.uuid}),
        },
    )


@login_required(login_url=LOGIN_URL)
@role_required(User.Role.USER)
def medical_records(request, pet_uuid):
    pet = owned_pet_or_404(request, pet_uuid)
    return render(
        request,
        "pet_profiles/medical_records.html",
        {
            "pet": pet,
            "records": pet.medical_records.all(),
            "vaccinations": pet.vaccinations.all(),
            "medications": pet.medications.all(),
        },
    )


@login_required(login_url=LOGIN_URL)
@role_required(User.Role.USER)
def add_medical_record(request, pet_uuid):
    pet = owned_pet_or_404(request, pet_uuid)
    return _create_related_record(
        request=request,
        pet=pet,
        form_class=MedicalRecordForm,
        page_title="Add medical record",
        success_message="Medical record added.",
    )


@login_required(login_url=LOGIN_URL)
@role_required(User.Role.USER)
def add_vaccination(request, pet_uuid):
    pet = owned_pet_or_404(request, pet_uuid)
    return _create_related_record(
        request=request,
        pet=pet,
        form_class=VaccinationRecordForm,
        page_title="Add vaccination",
        success_message="Vaccination record added.",
    )


@login_required(login_url=LOGIN_URL)
@role_required(User.Role.USER)
def add_medication(request, pet_uuid):
    pet = owned_pet_or_404(request, pet_uuid)
    return _create_related_record(
        request=request,
        pet=pet,
        form_class=MedicationForm,
        page_title="Add prescription",
        success_message="Prescription added.",
    )


def _create_related_record(request, pet, form_class, page_title, success_message):
    if request.method == "POST":
        form = form_class(request.POST, request.FILES)
        if form.is_valid():
            item = form.save(commit=False)
            item.pet = pet
            item.save()
            messages.success(request, success_message)
            return redirect("pet_profiles:records", pet_uuid=pet.uuid)
    else:
        form = form_class()

    return render(
        request,
        "pet_profiles/form_page.html",
        {
            "form": form,
            "pet": pet,
            "page_title": page_title,
            "submit_label": "Save",
            "cancel_url": reverse("pet_profiles:records", kwargs={"pet_uuid": pet.uuid}),
        },
    )


@login_required(login_url=LOGIN_URL)
@role_required(User.Role.USER)
def appointment_open(request, pet_uuid):
    """
    Always redirects into the REAL appointment system — the module's
    own local Appointment model/list/add views were removed entirely
    since a real, vet-linked, notification-triggering appointment
    system already exists project-wide.
    """
    pet = owned_pet_or_404(request, pet_uuid)
    external_name = getattr(settings, "PET_PROFILE_APPOINTMENT_URL_NAME", "")
    if external_name:
        try:
            url = reverse(external_name)
            query = urlencode({"pet_id": pet.uuid})
            return HttpResponseRedirect(f"{url}?{query}")
        except NoReverseMatch:
            messages.warning(request, "The appointments page could not be found.")
    return redirect("core:pet_owner_dashboard")


@login_required(login_url=LOGIN_URL)
@role_required(User.Role.USER)
def assistant_open(request, pet_uuid):
    pet = owned_pet_or_404(request, pet_uuid)
    chatbot_name = getattr(settings, "PET_PROFILE_CHATBOT_URL_NAME", "core:chatbot")
    try:
        url = reverse(chatbot_name)
    except NoReverseMatch:
        messages.error(request, "Chatbot route not found.")
        return redirect("pet_profiles:detail", pet_uuid=pet.uuid)

    query = urlencode({"pet_id": pet.uuid, "pet_name": pet.name})
    return HttpResponseRedirect(f"{url}?{query}")