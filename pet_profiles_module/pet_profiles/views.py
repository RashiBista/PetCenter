from urllib.parse import urlencode

from django.conf import settings
from django.contrib import messages
from django.db.models import Prefetch
from django.http import HttpResponseRedirect
from django.shortcuts import redirect, render
from django.urls import NoReverseMatch, reverse
from django.utils import timezone

from .forms import (
    AppointmentForm,
    MedicalRecordForm,
    MedicalSummaryForm,
    MedicationForm,
    PetForm,
    PetPhotoForm,
    VaccinationRecordForm,
)
from .models import (
    Appointment,
    MedicalRecord,
    MedicalSummary,
    Medication,
    Pet,
    VaccinationRecord,
)
from .services import owned_pet_or_404, owner_for_request


def home(request):
    owner = owner_for_request(request)
    first_pet = Pet.objects.filter(owner=owner).first()
    if first_pet:
        return redirect("pet_profiles:detail", pk=first_pet.pk)
    return redirect("pet_profiles:create")


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
            return redirect("pet_profiles:detail", pk=pet.pk)
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


def pet_detail(request, pk):
    owner = owner_for_request(request)
    pet = (
        Pet.objects.filter(pk=pk, owner=owner)
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
        from django.http import Http404

        raise Http404("Pet not found")

    summary, _ = MedicalSummary.objects.get_or_create(pet=pet)
    upcoming = (
        Appointment.objects.filter(
            pet=pet,
            starts_at__gte=timezone.now(),
            status=Appointment.Status.SCHEDULED,
        )
        .order_by("starts_at")
        .first()
    )
    pets = Pet.objects.filter(owner=owner).only("id", "name", "photo")

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


def pet_edit(request, pk):
    pet = owned_pet_or_404(request, pk)
    if request.method == "POST":
        form = PetForm(request.POST, instance=pet)
        if form.is_valid():
            form.save()
            messages.success(request, "Pet details updated.")
            return redirect("pet_profiles:detail", pk=pet.pk)
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
            "cancel_url": reverse("pet_profiles:detail", kwargs={"pk": pet.pk}),
        },
    )


def pet_photo_edit(request, pk):
    pet = owned_pet_or_404(request, pk)
    if request.method == "POST":
        form = PetPhotoForm(request.POST, request.FILES, instance=pet)
        if form.is_valid():
            form.save()
            messages.success(request, "Pet photo updated.")
            return redirect("pet_profiles:detail", pk=pet.pk)
    else:
        form = PetPhotoForm(instance=pet)

    return render(
        request,
        "pet_profiles/photo_form.html",
        {"form": form, "pet": pet},
    )


def medical_summary_edit(request, pk):
    pet = owned_pet_or_404(request, pk)
    summary, _ = MedicalSummary.objects.get_or_create(pet=pet)
    if request.method == "POST":
        form = MedicalSummaryForm(request.POST, instance=summary)
        if form.is_valid():
            form.save()
            messages.success(request, "Medical summary updated.")
            return redirect("pet_profiles:detail", pk=pet.pk)
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
            "cancel_url": reverse("pet_profiles:detail", kwargs={"pk": pet.pk}),
        },
    )


def medical_records(request, pk):
    pet = owned_pet_or_404(request, pk)
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


def add_medical_record(request, pk):
    pet = owned_pet_or_404(request, pk)
    return _create_related_record(
        request=request,
        pet=pet,
        form_class=MedicalRecordForm,
        page_title="Add medical record",
        success_message="Medical record added.",
    )


def add_vaccination(request, pk):
    pet = owned_pet_or_404(request, pk)
    return _create_related_record(
        request=request,
        pet=pet,
        form_class=VaccinationRecordForm,
        page_title="Add vaccination",
        success_message="Vaccination record added.",
    )


def add_medication(request, pk):
    pet = owned_pet_or_404(request, pk)
    return _create_related_record(
        request=request,
        pet=pet,
        form_class=MedicationForm,
        page_title="Add prescription",
        success_message="Prescription added.",
    )


def _create_related_record(
    request,
    pet,
    form_class,
    page_title,
    success_message,
):
    if request.method == "POST":
        form = form_class(request.POST, request.FILES)
        if form.is_valid():
            item = form.save(commit=False)
            item.pet = pet
            item.save()
            messages.success(request, success_message)
            return redirect("pet_profiles:records", pk=pet.pk)
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
            "cancel_url": reverse("pet_profiles:records", kwargs={"pk": pet.pk}),
        },
    )


def appointment_open(request, pk):
    pet = owned_pet_or_404(request, pk)
    external_name = getattr(settings, "PET_PROFILE_APPOINTMENT_URL_NAME", "")
    if external_name:
        try:
            url = reverse(external_name)
            query = urlencode({"pet_id": pet.pk})
            return HttpResponseRedirect(f"{url}?{query}")
        except NoReverseMatch:
            messages.warning(
                request,
                "The configured appointment module URL was not found. Showing the local list instead.",
            )
    return redirect("pet_profiles:appointment_list", pk=pet.pk)


def appointment_list(request, pk):
    pet = owned_pet_or_404(request, pk)
    appointments = pet.appointments.all()
    return render(
        request,
        "pet_profiles/appointment_list.html",
        {"pet": pet, "appointments": appointments},
    )


def appointment_add(request, pk):
    pet = owned_pet_or_404(request, pk)
    if request.method == "POST":
        form = AppointmentForm(request.POST)
        if form.is_valid():
            appointment = form.save(commit=False)
            appointment.pet = pet
            appointment.save()
            messages.success(request, "Appointment added.")
            return redirect("pet_profiles:appointment_list", pk=pet.pk)
    else:
        form = AppointmentForm()

    return render(
        request,
        "pet_profiles/form_page.html",
        {
            "form": form,
            "pet": pet,
            "page_title": "Add appointment",
            "submit_label": "Save appointment",
            "cancel_url": reverse(
                "pet_profiles:appointment_list",
                kwargs={"pk": pet.pk},
            ),
        },
    )


def assistant_open(request, pk):
    pet = owned_pet_or_404(request, pk)
    chatbot_name = getattr(
        settings,
        "PET_PROFILE_CHATBOT_URL_NAME",
        "core:chatbot",
    )
    try:
        url = reverse(chatbot_name)
    except NoReverseMatch:
        messages.error(
            request,
            "Chatbot route not found. Check PET_PROFILE_CHATBOT_URL_NAME in settings.py.",
        )
        return redirect("pet_profiles:detail", pk=pet.pk)

    query = urlencode({"pet_id": pet.pk, "pet_name": pet.name})
    return HttpResponseRedirect(f"{url}?{query}")
