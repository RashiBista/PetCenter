from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from django.conf import settings
from django.contrib import messages
from django.db.models import Q
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .forms import MedicalSummaryForm, PetForm, PetPhotoForm
from .models import Appointment, MedicalSummary, Pet


def _pet_queryset(request):
    if request.user.is_authenticated:
        if request.user.is_staff:
            return Pet.objects.filter(Q(owner=request.user) | Q(owner__isnull=True))
        return Pet.objects.filter(owner=request.user)
    return Pet.objects.filter(owner__isnull=True)


def _get_pet(request, pk):
    return get_object_or_404(_pet_queryset(request), pk=pk)


def _profile_context(request, pet):
    summary, _ = MedicalSummary.objects.get_or_create(pet=pet)
    upcoming = (
        pet.appointments.filter(
            status=Appointment.Status.UPCOMING,
            start_datetime__gte=timezone.now(),
        )
        .order_by("start_datetime")
        .first()
    )
    return {
        "pet": pet,
        "pets": _pet_queryset(request),
        "medical_summary": summary,
        "active_prescriptions": pet.prescriptions.filter(active=True),
        "vaccinations": pet.vaccinations.all()[:3],
        "upcoming_appointment": upcoming,
    }


def dashboard(request):
    pets = _pet_queryset(request)
    pet_id = request.GET.get("pet")
    if pet_id:
        try:
            pet = pets.get(pk=pet_id)
        except (Pet.DoesNotExist, ValueError):
            raise Http404("Pet not found")
    else:
        pet = pets.first()

    if not pet:
        return render(request, "pet_profiles/empty.html")
    return render(request, "pet_profiles/profile.html", _profile_context(request, pet))


def pet_detail(request, pk):
    pet = _get_pet(request, pk)
    return render(request, "pet_profiles/profile.html", _profile_context(request, pet))


def pet_create(request):
    if request.method == "POST":
        form = PetForm(request.POST)
        if form.is_valid():
            pet = form.save(commit=False)
            if request.user.is_authenticated:
                pet.owner = request.user
            pet.save()
            messages.success(request, f"{pet.name}'s profile was created.")
            return redirect("pet_profiles:detail", pk=pet.pk)
    else:
        form = PetForm()
    return render(
        request,
        "pet_profiles/form.html",
        {
            "form": form,
            "page_title": "Add a pet",
            "submit_label": "Create profile",
            "cancel_url": "pet_profiles:dashboard",
        },
    )


def pet_edit(request, pk):
    pet = _get_pet(request, pk)
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
        "pet_profiles/form.html",
        {
            "form": form,
            "pet": pet,
            "page_title": f"Edit {pet.name}",
            "submit_label": "Save changes",
            "cancel_url": "pet_profiles:detail",
            "cancel_pk": pet.pk,
        },
    )


def pet_photo_update(request, pk):
    pet = _get_pet(request, pk)
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
        {
            "form": form,
            "pet": pet,
            "page_title": f"Change {pet.name}'s photo",
        },
    )


def medical_summary_edit(request, pk):
    pet = _get_pet(request, pk)
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
        "pet_profiles/form.html",
        {
            "form": form,
            "pet": pet,
            "page_title": f"Edit {pet.name}'s medical summary",
            "submit_label": "Save medical summary",
            "cancel_url": "pet_profiles:detail",
            "cancel_pk": pet.pk,
        },
    )


def records_list(request, pk):
    pet = _get_pet(request, pk)
    return render(
        request,
        "pet_profiles/records.html",
        {
            "pet": pet,
            "records": pet.medical_records.all(),
            "vaccinations": pet.vaccinations.all(),
            "prescriptions": pet.prescriptions.all(),
        },
    )


def appointments_list(request, pk):
    pet = _get_pet(request, pk)
    return render(
        request,
        "pet_profiles/appointments.html",
        {"pet": pet, "appointments": pet.appointments.all()},
    )


def _external_url(base_url, pet):
    formatted = base_url.format(pet_id=pet.pk, pet_name=pet.name)
    if "{pet_id}" in base_url or "{pet_name}" in base_url:
        return formatted

    parts = urlsplit(formatted)
    query = dict(parse_qsl(parts.query, keep_blank_values=True))
    query.setdefault("pet_id", str(pet.pk))
    query.setdefault("pet_name", pet.name)
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))


def assistant_bridge(request, pk):
    pet = _get_pet(request, pk)
    if settings.CHATBOT_URL:
        return redirect(_external_url(settings.CHATBOT_URL, pet))
    return render(
        request,
        "pet_profiles/integration_missing.html",
        {
            "pet": pet,
            "integration_name": "Chatbot",
            "setting_name": "CHATBOT_URL",
            "example": "http://127.0.0.1:8001/chat/?pet_id={pet_id}",
        },
        status=503,
    )


def open_list_bridge(request, pk):
    pet = _get_pet(request, pk)
    if settings.OPEN_LIST_URL:
        return redirect(_external_url(settings.OPEN_LIST_URL, pet))
    return redirect("pet_profiles:appointments", pk=pet.pk)
