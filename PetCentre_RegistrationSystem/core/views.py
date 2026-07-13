import random
from datetime import datetime, timedelta

import cloudinary.uploader
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.hashers import make_password
from django.contrib.auth.password_validation import validate_password
from django.contrib.gis.db.models.functions import Distance
from django.contrib.gis.geos import Point
from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from django.db.models import Q
from django.shortcuts import render, redirect
from django.utils import timezone

from myapp.decorators import role_required
from myapp.models import (
    Appointment, IPLoginAttempt, LoginAttempt, Medicine, PasswordResetOTP, Pet, Prescription,
    SignupOTP, User, UserProfile, VetProfile, PharmacyProfile,
)
from notifications.models import Notification
from notifications.services import create_notification

MAX_ATTEMPTS_PER_24H = 5


def _generate_otp_code():
    return f"{random.randint(0, 999999):06d}"


def _send_otp(channel, destination, code, purpose="verification"):
    """
    channel: SignupOTP.Channel.EMAIL or .PHONE
    Email sends via EMAIL_BACKEND (console in dev, real SMTP once
    configured). Phone has no real SMS provider connected — a paid
    provider like Twilio would be needed for that, which isn't worth
    the cost for this project right now. This just logs the code so
    the signup flow is still fully testable locally in the meantime.
    """
    if channel == SignupOTP.Channel.PHONE:
        print(f"[SMS STUB — no SMS provider configured] Would send to {destination}: your {purpose} code is {code}")
        return
    send_mail(
        subject=f"Your PetCentre {purpose} code",
        message=f"Your one-time code is: {code}\nIt expires in 10 minutes.",
        from_email=None,
        recipient_list=[destination],
        fail_silently=True,
    )


def _find_user_by_identifier(identifier):
    try:
        return User.objects.get(Q(email__iexact=identifier) | Q(username__iexact=identifier))
    except User.DoesNotExist:
        return None
    except User.MultipleObjectsReturned:
        return User.objects.filter(Q(email__iexact=identifier) | Q(username__iexact=identifier)).order_by('id').first()


def _is_locked_out(user):
    cutoff = timezone.now() - timedelta(hours=24)
    recent_failures = LoginAttempt.objects.filter(user=user, created_at__gte=cutoff).count()
    return recent_failures >= MAX_ATTEMPTS_PER_24H


def _record_failed_attempt(user):
    LoginAttempt.objects.create(user=user)


def _get_client_ip(request):
    # X-Forwarded-For is used when behind a proxy/load balancer (not
    # currently the case for local dev or the current Docker setup,
    # but harmless to check first — falls back to REMOTE_ADDR either way).
    forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
    if forwarded:
        return forwarded.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', '0.0.0.0')


def _is_ip_locked_out(ip_address):
    cutoff = timezone.now() - timedelta(hours=24)
    recent_failures = IPLoginAttempt.objects.filter(ip_address=ip_address, created_at__gte=cutoff).count()
    return recent_failures >= MAX_ATTEMPTS_PER_24H


def _record_failed_ip_attempt(ip_address):
    IPLoginAttempt.objects.create(ip_address=ip_address)


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

def _stash_pending_signup(request, role, form_data, password, extra=None):
    """
    Stores validated signup data server-side in the session (Django's
    default session backend is database-backed here — see
    django.contrib.sessions in INSTALLED_APPS — so this never touches
    the client beyond a signed session-ID cookie). The password is
    hashed with make_password() before storing, never kept as
    plaintext, and is written directly to user.password at account
    creation time (bypassing create_user's own hashing, which would
    otherwise hash the hash and break login).
    """
    request.session['pending_signup'] = {
        'role': role,
        'form_data': form_data,
        'password_hash': make_password(password),
        'extra': extra or {},
    }


def pet_owner_signup_view(request):
    """
    Step 1 of signup: validate fields, then send an OTP (email or
    phone) instead of creating the account immediately. The account
    is only actually created once the code is verified — see
    verify_signup_view — so abandoned signups never leave behind
    unverified User rows.
    """
    errors = {}
    form_data = {}

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip()
        phone_number = request.POST.get('phone_number', '').strip()
        password = request.POST.get('password', '')
        password2 = request.POST.get('password2', '')
        channel = request.POST.get('otp_channel', 'email')

        pet_name = request.POST.get('pet_name', '').strip()
        pet_species = request.POST.get('pet_species', '').strip()
        pet_breed = request.POST.get('pet_breed', '').strip()
        pet_photo = request.FILES.get('pet_photo')

        form_data = {
            'username': username, 'email': email, 'phone_number': phone_number,
            'pet_name': pet_name, 'pet_species': pet_species, 'pet_breed': pet_breed,
        }

        errors = _validate_signup_fields(username, email, password, password2)
        if channel == 'phone' and not phone_number:
            errors.setdefault('otp_channel', []).append('Add a phone number above to receive a code by phone.')

        pet_photo_public_id = None
        if pet_photo and not errors:
            if not (pet_name and pet_species):
                errors.setdefault('pet_name', []).append('Pet name and species are required if uploading a photo.')
            else:
                # Upload to Cloudinary right now, before the account even
                # exists — sessions can't hold file objects, but they can
                # hold this short string reference. Tagged so an orphan
                # cleanup job can find and remove it later if the signup
                # is abandoned before OTP verification completes.
                upload_result = cloudinary.uploader.upload(
                    pet_photo, folder='pending_signups', tags=['pending_signup'],
                )
                pet_photo_public_id = upload_result['public_id']

        if not errors:
            _stash_pending_signup(
                request, role='user', form_data=form_data, password=password,
                extra={
                    'pet_name': pet_name, 'pet_species': pet_species, 'pet_breed': pet_breed,
                    'pet_photo_public_id': pet_photo_public_id,
                },
            )
            destination = phone_number if channel == 'phone' else email
            code = _generate_otp_code()
            SignupOTP.objects.create(
                session_key=request.session.session_key or request.session.save() or request.session.session_key,
                channel=channel, destination=destination, code=code,
            )
            _send_otp(channel, destination, code, purpose="signup verification")
            return redirect('core:verify_signup')

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
        channel = request.POST.get('otp_channel', 'email')

        form_data = {'username': username, 'email': email, 'phone_number': phone_number}
        errors = _validate_signup_fields(username, email, password, password2)
        if channel == 'phone' and not phone_number:
            errors.setdefault('otp_channel', []).append('Add a phone number above to receive a code by phone.')

        if not errors:
            _stash_pending_signup(request, role='vet', form_data=form_data, password=password)
            destination = phone_number if channel == 'phone' else email
            code = _generate_otp_code()
            SignupOTP.objects.create(
                session_key=request.session.session_key or request.session.save() or request.session.session_key,
                channel=channel, destination=destination, code=code,
            )
            _send_otp(channel, destination, code, purpose="signup verification")
            return redirect('core:verify_signup')

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
        channel = request.POST.get('otp_channel', 'email')

        form_data = {
            'username': username, 'email': email,
            'phone_number': phone_number, 'pharmacy_name': pharmacy_name,
        }
        errors = _validate_signup_fields(username, email, password, password2)
        if channel == 'phone' and not phone_number:
            errors.setdefault('otp_channel', []).append('Add a phone number above to receive a code by phone.')

        if not errors:
            _stash_pending_signup(request, role='pharmacy', form_data=form_data, password=password, extra={'pharmacy_name': pharmacy_name})
            destination = phone_number if channel == 'phone' else email
            code = _generate_otp_code()
            SignupOTP.objects.create(
                session_key=request.session.session_key or request.session.save() or request.session.session_key,
                channel=channel, destination=destination, code=code,
            )
            _send_otp(channel, destination, code, purpose="signup verification")
            return redirect('core:verify_signup')

    return render(request, 'core/pharmacy_signup.html', {'errors': errors, 'form_data': form_data})


def verify_signup_view(request):
    """
    Step 2 of signup. Reads the pending signup data back out of the
    session, checks the OTP, and only NOW actually creates the User +
    role profile (+ pet, for pet owners without a photo attached).
    """
    pending = request.session.get('pending_signup')
    if not pending:
        return redirect('core:landing_page')

    error = None
    if request.method == 'POST':
        code = request.POST.get('otp', '').strip()
        try:
            otp = SignupOTP.objects.filter(
                session_key=request.session.session_key, code=code
            ).latest('created_at')
        except SignupOTP.DoesNotExist:
            error = "Invalid code."
        else:
            if not otp.is_valid():
                error = "This code has expired or was already used. Request a new one."
            else:
                role = pending['role']
                fd = pending['form_data']
                user = User(username=fd['username'], email=fd['email'], phone_number=fd.get('phone_number', ''))
                user.password = pending['password_hash']  # already hashed — do NOT call set_password here
                if role == 'user':
                    user.role = User.Role.USER
                elif role == 'vet':
                    user.role = User.Role.VET
                elif role == 'pharmacy':
                    user.role = User.Role.PHARMACY
                user.save()

                extra = pending.get('extra', {})
                if role == 'user':
                    UserProfile.objects.create(user=user)
                    if extra.get('pet_name') and extra.get('pet_species'):
                        pet = Pet(
                            owner=user, name=extra['pet_name'],
                            species=extra['pet_species'], breed=extra.get('pet_breed', ''),
                        )
                        public_id = extra.get('pet_photo_public_id')
                        if public_id:
                            # Already uploaded to Cloudinary during step 1 —
                            # assign the storage path directly instead of a
                            # File object, so Django records this reference
                            # without triggering a second upload.
                            pet.photo.name = public_id
                        pet.save()
                elif role == 'vet':
                    VetProfile.objects.create(user=user)
                elif role == 'pharmacy':
                    PharmacyProfile.objects.create(user=user, pharmacy_name=extra.get('pharmacy_name', ''))

                otp.is_used = True
                otp.save()
                del request.session['pending_signup']

                login(request, user, backend='django.contrib.auth.backends.ModelBackend')
                dashboard_map = {
                    'user': 'core:pet_owner_dashboard',
                    'vet': 'core:veterinary_dashboard',
                    'pharmacy': 'core:pharmacy_dashboard',
                }
                return redirect(dashboard_map[role])

    return render(request, 'core/verify_signup.html', {'error': error, 'destination': None})


def resend_signup_otp_view(request):
    pending = request.session.get('pending_signup')
    if not pending:
        return redirect('core:landing_page')

    fd = pending['form_data']
    # Re-derive channel/destination the same way the original signup did —
    # simplest approach: reuse whatever the most recent OTP for this
    # session used.
    last_otp = SignupOTP.objects.filter(session_key=request.session.session_key).order_by('-created_at').first()
    channel = last_otp.channel if last_otp else SignupOTP.Channel.EMAIL
    destination = fd.get('phone_number') if channel == SignupOTP.Channel.PHONE else fd.get('email')

    code = _generate_otp_code()
    SignupOTP.objects.create(session_key=request.session.session_key, channel=channel, destination=destination, code=code)
    _send_otp(channel, destination, code, purpose="signup verification")
    messages.success(request, "A new code has been sent.")
    return redirect('core:verify_signup')


# ------------------------------------------------------------------
# Login views — one per role. Each checks the authenticated user
# actually holds the matching role before starting the session.
# ------------------------------------------------------------------

def pet_owner_login_view(request):
    error = None
    if request.method == 'POST':
        identifier = request.POST.get('email', '').strip()
        password = request.POST.get('password', '')
        client_ip = _get_client_ip(request)
        target_user = _find_user_by_identifier(identifier)

        if _is_ip_locked_out(client_ip):
            error = "Too many failed attempts from this network. Try again in 24 hours."
        elif target_user and _is_locked_out(target_user):
            error = "Too many failed attempts. Try again in 24 hours."
        else:
            user = authenticate(request, username=identifier, password=password)
            if user is None:
                _record_failed_ip_attempt(client_ip)
                if target_user:
                    _record_failed_attempt(target_user)
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
        client_ip = _get_client_ip(request)
        target_user = _find_user_by_identifier(identifier)

        if _is_ip_locked_out(client_ip):
            error = "Too many failed attempts from this network. Try again in 24 hours."
        elif target_user and _is_locked_out(target_user):
            error = "Too many failed attempts. Try again in 24 hours."
        else:
            user = authenticate(request, username=identifier, password=password)
            if user is None:
                _record_failed_ip_attempt(client_ip)
                if target_user:
                    _record_failed_attempt(target_user)
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
        client_ip = _get_client_ip(request)
        target_user = _find_user_by_identifier(identifier)

        if _is_ip_locked_out(client_ip):
            error = "Too many failed attempts from this network. Try again in 24 hours."
        elif target_user and _is_locked_out(target_user):
            error = "Too many failed attempts. Try again in 24 hours."
        else:
            user = authenticate(request, username=identifier, password=password)
            if user is None:
                _record_failed_ip_attempt(client_ip)
                if target_user:
                    _record_failed_attempt(target_user)
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
        client_ip = _get_client_ip(request)
        target_user = _find_user_by_identifier(identifier)

        if _is_ip_locked_out(client_ip):
            error = "Too many failed attempts from this network. Try again in 24 hours."
        elif target_user and _is_locked_out(target_user):
            error = "Too many failed attempts. Try again in 24 hours."
        else:
            user = authenticate(request, username=identifier, password=password)
            if user is None:
                _record_failed_ip_attempt(client_ip)
                if target_user:
                    _record_failed_attempt(target_user)
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
# Password reset — email OTP flow. Works for any role (pet owner,
# vet, pharmacy, admin) since it just looks up by email/username.
# ------------------------------------------------------------------

def forgot_password_view(request):
    sent = False
    error = None
    if request.method == 'POST':
        identifier = request.POST.get('email', '').strip()
        try:
            user = User.objects.get(Q(email__iexact=identifier) | Q(username__iexact=identifier))
        except User.DoesNotExist:
            error = "No account found with that email or username."
        else:
            cutoff = timezone.now() - timedelta(hours=24)
            recent_otp_count = PasswordResetOTP.objects.filter(user=user, created_at__gte=cutoff).count()
            if recent_otp_count >= MAX_ATTEMPTS_PER_24H:
                error = "Too many reset attempts. Try again in 24 hours."
            else:
                code = _generate_otp_code()
                PasswordResetOTP.objects.create(user=user, code=code)
                send_mail(
                    subject="Your PetCentre password reset code",
                    message=f"Your one-time code is: {code}\nIt expires in 10 minutes. If you didn't request this, ignore this email.",
                    from_email=None,
                    recipient_list=[user.email],
                    fail_silently=True,
                )
                request.session['reset_user_id'] = user.id
                sent = True
    return render(request, 'core/forgot_password.html', {'sent': sent, 'error': error})


def reset_password_view(request):
    user_id = request.session.get('reset_user_id')
    if not user_id:
        return redirect('core:forgot_password')

    error = None
    if request.method == 'POST':
        code = request.POST.get('otp', '').strip()
        new_password = request.POST.get('password', '')
        password2 = request.POST.get('password2', '')

        try:
            user = User.objects.get(id=user_id)
            otp = PasswordResetOTP.objects.filter(user=user, code=code).latest('created_at')
        except (User.DoesNotExist, PasswordResetOTP.DoesNotExist):
            error = "Invalid code."
        else:
            if not otp.is_valid():
                error = "This code has expired or was already used. Request a new one."
            elif new_password != password2:
                error = "Passwords don't match."
            else:
                try:
                    validate_password(new_password)
                except ValidationError as e:
                    error = " ".join(e.messages)
                else:
                    user.set_password(new_password)
                    user.save()
                    otp.is_used = True
                    otp.save()
                    del request.session['reset_user_id']
                    messages.success(request, "Password reset successful — please log in.")
                    return redirect('core:landing_page')

    return render(request, 'core/reset_password.html', {'error': error})


# ------------------------------------------------------------------
# Appointment booking
# ------------------------------------------------------------------

def _recipient_role_for(user):
    """
    Maps our User.Role values to the notifications app's RecipientRole
    choices, which only has 'client'/'vet'. Anything that isn't VET
    (pet owner, pharmacy, admin) is treated as 'client' for now.
    """
    return Notification.RecipientRole.VET if user.role == User.Role.VET else Notification.RecipientRole.CLIENT


@role_required(User.Role.USER)
def book_appointment_view(request):
    """
    Rendered as core/appointment_booking.html (matches the "Book an
    Appointment" designed page). Pets/vets are real DB records; the
    7-day date strip is generated here since there's no real
    per-vet availability system yet — every future date/slot is shown
    as open. Time slots are a fixed common set for the same reason.
    """
    pets = Pet.objects.filter(owner=request.user)
    vets = User.objects.filter(role=User.Role.VET).select_related('vet_profile')
    error = None

    upcoming_dates = [timezone.localdate() + timezone.timedelta(days=i) for i in range(7)]
    time_slots = ["09:00", "10:30", "11:15", "13:00", "14:30", "16:00"]

    if request.method == 'POST':
        pet_id = request.POST.get('pet')
        vet_id = request.POST.get('vet')
        date_str = request.POST.get('date', '')
        time_str = request.POST.get('time', '')
        reason = request.POST.get('reason', '').strip()

        try:
            pet = pets.get(id=pet_id)
            vet = vets.get(id=vet_id)
            naive_dt = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
            scheduled_time = timezone.make_aware(naive_dt)
        except Exception:
            error = "Please select a pet, vet, date, and time."
        else:
            if scheduled_time < timezone.now():
                error = "Please choose a future date and time."
            else:
                appt = Appointment.objects.create(pet=pet, vet=vet, scheduled_time=scheduled_time, reason=reason)
                create_notification(
                    recipient=vet,
                    recipient_role=_recipient_role_for(vet),
                    notification_type='appointment',
                    title="New appointment request",
                    message=f"{request.user.get_full_name() or request.user.username} requested an appointment for {pet.name} on {scheduled_time:%b %d, %Y at %I:%M %p}.",
                    action_url=f"/dashboard/veterinary/",
                )
                messages.success(request, f"Appointment requested with Dr. {vet.get_full_name() or vet.username}.")
                return redirect('core:pet_owner_dashboard')

    return render(request, 'core/appointment_booking.html', {
        'pets': pets, 'vets': vets, 'error': error,
        'upcoming_dates': upcoming_dates, 'time_slots': time_slots,
    })


# ------------------------------------------------------------------
# Medicine search + detail
# ------------------------------------------------------------------

@login_required(login_url='core:pet_owner_login')
def medicine_search_view(request):
    query = request.GET.get('q', '').strip()
    medicines = Medicine.objects.all()
    if query:
        medicines = medicines.filter(Q(name__icontains=query) | Q(category__icontains=query))
    return render(request, 'core/medicine_search.html', {'medicines': medicines, 'query': query})


@login_required(login_url='core:pet_owner_login')
def medicine_detail_view(request, pk):
    from django.shortcuts import get_object_or_404
    medicine = get_object_or_404(Medicine, pk=pk)
    return render(request, 'core/medicine_detail.html', {'medicine': medicine})


# ------------------------------------------------------------------
# Notifications
# ------------------------------------------------------------------

@login_required(login_url='core:pet_owner_login')
def pet_owner_notifications_view(request):
    if request.method == 'POST' and request.POST.get('action') == 'mark_all_read':
        Notification.objects.filter(recipient=request.user, is_read=False).update(
            is_read=True, read_at=timezone.now()
        )
        return redirect('core:pet_owner_notifications')

    notifications = Notification.objects.filter(recipient=request.user)
    # Viewing the page marks everything as read, same pattern as chat's unread_count.
    Notification.objects.filter(recipient=request.user, is_read=False).update(
        is_read=True, read_at=timezone.now()
    )
    return render(request, 'core/pet_own_notif.html', {'notifications': notifications})


# ------------------------------------------------------------------
# Pet profile (view + add pets)
# ------------------------------------------------------------------

@login_required(login_url='core:pet_owner_login')
def pet_profile_view(request):
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        species = request.POST.get('species', '').strip()
        breed = request.POST.get('breed', '').strip()
        photo = request.FILES.get('photo')
        if name and species:
            Pet.objects.create(owner=request.user, name=name, species=species, breed=breed, photo=photo)
            messages.success(request, f"{name} was added.")
        return redirect('core:pet_profile')

    pets = Pet.objects.filter(owner=request.user)
    return render(request, 'core/pet_profile.html', {'pets': pets})


# ------------------------------------------------------------------
# Find nearest vets — lists real vet accounts. NOTE: there is no real
# geolocation, distance, or ratings data anywhere in this system yet,
# so "distance" and star ratings from the original design are NOT
# rendered here (no data to back them) — only real fields: name,
# specialization, email/phone for contact, and a link to book/chat.
# ------------------------------------------------------------------

@login_required(login_url='core:pet_owner_login')
def find_nearest_vets_view(request):
    """
    If the browser supplies ?lat=&lng= (via navigator.geolocation on
    the frontend), vets with a saved location are sorted by real
    distance using PostGIS. Vets without a saved location, or when no
    lat/lng is supplied at all, are just listed with no distance shown
    — no fake numbers are ever displayed.
    """
    vets = User.objects.filter(role=User.Role.VET).select_related('vet_profile')

    user_point = None
    lat = request.GET.get('lat')
    lng = request.GET.get('lng')
    if lat and lng:
        try:
            user_point = Point(float(lng), float(lat), srid=4326)
        except (TypeError, ValueError):
            user_point = None

    if user_point:
        vets = vets.filter(vet_profile__location__isnull=False).annotate(
            distance=Distance('vet_profile__location', user_point)
        ).order_by('distance')

    return render(request, 'core/find_nearest_vets.html', {
        'vets': vets,
        'has_location': bool(user_point),
    })


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