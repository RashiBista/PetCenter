from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.shortcuts import render, redirect
from django.utils import timezone

from myapp.decorators import role_required
from myapp.models import Appointment, Pet, Prescription, User, UserProfile, VetProfile, PharmacyProfile


def landing_page(request):
    return render(request, 'core/landing_page.html')


# ------------------------------------------------------------------
# Shared signup validation helper — used by all three signup views so
# the username/email/password rules stay identical everywhere.
# ------------------------------------------------------------------

def _validate_signup_fields(username, email, password, password2):
    errors = {}
    if User.objects.filter(username__iexact=username).exists():
        errors.setdefault('username', []).append('A user with this username already exists.')
    if User.objects.filter(email__iexact=email).exists():
        errors.setdefault('email', []).append('A user with this email already exists.')
    if password != password2:
        errors.setdefault('password2', []).append("Passwords don't match.")
    else:
        try:
            validate_password(password)
        except ValidationError as e:
            errors.setdefault('password', list(e.messages))
    return errors


# ------------------------------------------------------------------
# Sign up
# ------------------------------------------------------------------

def pet_owner_signup_view(request):
    """
    Pet-owner signup. Includes an optional pet photo upload — this
    uploads straight to Cloudinary since DEFAULT_FILE_STORAGE is set
    to cloudinary_storage.storage.MediaCloudinaryStorage in settings.py
    (cloud name znkhmhn0). No extra code is needed here for that part;
    assigning the uploaded file to Pet.photo is enough, Django's
    storage backend handles the actual upload.
    """
    errors = {}
    form_data = {}

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip()
        phone_number = request.POST.get('phone_number', '').strip()
        password = request.POST.get('password', '')
        password2 = request.POST.get('password2', '')

        pet_name = request.POST.get('pet_name', '').strip()
        pet_species = request.POST.get('pet_species', '').strip()
        pet_breed = request.POST.get('pet_breed', '').strip()
        pet_photo = request.FILES.get('pet_photo')

        form_data = {
            'username': username, 'email': email, 'phone_number': phone_number,
            'pet_name': pet_name, 'pet_species': pet_species, 'pet_breed': pet_breed,
        }

        errors = _validate_signup_fields(username, email, password, password2)

        if pet_photo and not (pet_name and pet_species):
            errors.setdefault('pet_name', []).append('Pet name and species are required if uploading a photo.')

        if not errors:
            user = User.objects.create_user(
                username=username, email=email, password=password,
                phone_number=phone_number, role=User.Role.USER,
            )
            UserProfile.objects.create(user=user)

            if pet_name and pet_species:
                Pet.objects.create(
                    owner=user, name=pet_name, species=pet_species,
                    breed=pet_breed, photo=pet_photo,
                )

            login(request, user, backend='django.contrib.auth.backends.ModelBackend')
            return redirect('core:pet_owner_dashboard')

    return render(request, 'core/pet_owner_signup.html', {'errors': errors, 'form_data': form_data})


def veterinary_signup_view(request):
    errors = {}
    form_data = {}

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip()
        phone_number = request.POST.get('phone_number', '').strip()
        password = request.POST.get('password', '')
        password2 = request.POST.get('password2', '')

        form_data = {'username': username, 'email': email, 'phone_number': phone_number}
        errors = _validate_signup_fields(username, email, password, password2)

        if not errors:
            user = User.objects.create_user(
                username=username, email=email, password=password,
                phone_number=phone_number, role=User.Role.VET,
            )
            VetProfile.objects.create(user=user)
            login(request, user, backend='django.contrib.auth.backends.ModelBackend')
            return redirect('core:veterinary_dashboard')

    return render(request, 'core/veterinary_signup.html', {'errors': errors, 'form_data': form_data})


def pharmacy_signup_view(request):
    errors = {}
    form_data = {}

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip()
        phone_number = request.POST.get('phone_number', '').strip()
        pharmacy_name = request.POST.get('pharmacy_name', '').strip()
        password = request.POST.get('password', '')
        password2 = request.POST.get('password2', '')

        form_data = {
            'username': username, 'email': email,
            'phone_number': phone_number, 'pharmacy_name': pharmacy_name,
        }
        errors = _validate_signup_fields(username, email, password, password2)

        if not errors:
            user = User.objects.create_user(
                username=username, email=email, password=password,
                phone_number=phone_number, role=User.Role.PHARMACY,
            )
            PharmacyProfile.objects.create(user=user, pharmacy_name=pharmacy_name)
            login(request, user, backend='django.contrib.auth.backends.ModelBackend')
            return redirect('core:pharmacy_dashboard')

    return render(request, 'core/pharmacy_signup.html', {'errors': errors, 'form_data': form_data})


# ------------------------------------------------------------------
# Login views — one per role. Each checks the authenticated user
# actually holds the matching role before starting the session.
# ------------------------------------------------------------------

def pet_owner_login_view(request):
    error = None
    if request.method == 'POST':
        identifier = request.POST.get('email', '').strip()
        password = request.POST.get('password', '')
        user = authenticate(request, username=identifier, password=password)
        if user is None:
            error = 'Invalid email/username or password.'
        elif not user.is_pet_owner:
            error = 'This account is not a pet-owner account. Use the correct login page.'
        else:
            login(request, user)
            return redirect('core:pet_owner_dashboard')
    return render(request, 'core/pet_owner_login.html', {'error': error})


def veterinary_login_view(request):
    error = None
    if request.method == 'POST':
        identifier = request.POST.get('email', '').strip()
        password = request.POST.get('password', '')
        user = authenticate(request, username=identifier, password=password)
        if user is None:
            error = 'Invalid email or password.'
        elif not user.is_vet:
            error = 'This account is not a veterinarian account.'
        else:
            login(request, user)
            return redirect('core:veterinary_dashboard')
    return render(request, 'core/veterinary_login.html', {'error': error})


def pharmacy_login_view(request):
    error = None
    if request.method == 'POST':
        identifier = request.POST.get('email', '').strip()
        password = request.POST.get('password', '')
        user = authenticate(request, username=identifier, password=password)
        if user is None:
            error = 'Invalid email or password.'
        elif not user.is_pharmacy:
            error = 'This account is not a pharmacy account.'
        else:
            login(request, user)
            return redirect('core:pharmacy_dashboard')
    return render(request, 'core/pharmacy_login.html', {'error': error})


def admin_login_view(request):
    error = None
    if request.method == 'POST':
        identifier = request.POST.get('adminId', '').strip()
        password = request.POST.get('password', '')
        user = authenticate(request, username=identifier, password=password)
        if user is None:
            error = 'Invalid credentials.'
        elif not (user.is_staff or user.is_superuser):
            error = 'This account does not have administrator access.'
        else:
            login(request, user)
            return redirect('core:admin_dashboard')
    return render(request, 'core/admin_login.html', {'error': error})


def logout_view(request):
    logout(request)
    return redirect('core:landing_page')


# ------------------------------------------------------------------
# Dashboards
# ------------------------------------------------------------------

@role_required(User.Role.USER)
def pet_owner_dashboard(request):
    pets = Pet.objects.filter(owner=request.user)
    next_appointment = Appointment.objects.filter(
        pet__owner=request.user,
        scheduled_time__gte=timezone.now(),
        status__in=[Appointment.Status.REQUESTED, Appointment.Status.CONFIRMED],
    ).select_related('pet', 'vet').first()

    return render(request, 'core/pet_owner_dashboard.html', {
        'pets': pets,
        'pet_count': pets.count(),
        'next_appointment': next_appointment,
    })


@role_required(User.Role.VET)
def veterinary_dashboard(request):
    today = timezone.localdate()
    todays_appointments = Appointment.objects.filter(
        vet=request.user,
        scheduled_time__date=today,
    ).select_related('pet', 'pet__owner').order_by('scheduled_time')

    total_patients = Pet.objects.filter(
        appointments__vet=request.user
    ).distinct().count()

    return render(request, 'core/veterinary_dashboard.html', {
        'todays_appointments': todays_appointments,
        'total_patients': total_patients,
    })


@role_required(User.Role.PHARMACY)
def pharmacy_dashboard(request):
    if request.method == 'POST':
        # Fulfill action: mark a pending prescription as fulfilled by this pharmacy.
        prescription_id = request.POST.get('prescription_id')
        Prescription.objects.filter(
            id=prescription_id, status=Prescription.Status.PENDING
        ).update(
            status=Prescription.Status.FULFILLED,
            pharmacy=request.user,
            fulfilled_at=timezone.now(),
        )
        return redirect('core:pharmacy_dashboard')

    pending_prescriptions = Prescription.objects.filter(
        status=Prescription.Status.PENDING
    ).select_related('pet', 'pet__owner', 'vet')

    recently_fulfilled = Prescription.objects.filter(
        status=Prescription.Status.FULFILLED, pharmacy=request.user
    ).select_related('pet', 'vet')[:5]

    return render(request, 'core/pharmacy_dashboard.html', {
        'pending_prescriptions': pending_prescriptions,
        'pending_count': pending_prescriptions.count(),
        'recently_fulfilled': recently_fulfilled,
    })


@login_required(login_url='core:admin_login')
def admin_dashboard(request):
    if not (request.user.is_staff or request.user.is_superuser):
        messages.error(request, "You don't have access to that page.")
        return redirect('core:landing_page')
    return render(request, 'core/admin_dashboard.html')


@login_required(login_url='core:pet_owner_login')
def chatbot_view(request):
    return render(request, 'core/chatbot_assistant.html')