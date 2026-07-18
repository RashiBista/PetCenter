import random
from datetime import datetime, timedelta

import cloudinary.uploader
from django.conf import settings
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
    Accessory, Appointment, IPLoginAttempt, LoginAttempt, Medicine, PasswordResetOTP, Prescription,
    SignupOTP, User, UserProfile, VetProfile, PharmacyProfile,
)
from pet_profiles.models import Pet
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
        fail_silently=False,
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
    # Presentation/dev machines listed here never get IP-locked, so
    # demonstrating account lockout (failing one account 5x) can't
    # accidentally block a DIFFERENT account's successful login from
    # the same machine right after. Account-level lockout is
    # completely unaffected by this — that's still fully live.
    if ip_address in settings.EXEMPT_LOGIN_IPS:
        return False
    cutoff = timezone.now() - timedelta(hours=24)
    recent_failures = IPLoginAttempt.objects.filter(ip_address=ip_address, created_at__gte=cutoff).count()
    return recent_failures >= MAX_ATTEMPTS_PER_24H


def _record_failed_ip_attempt(ip_address):
    if ip_address in settings.EXEMPT_LOGIN_IPS:
        return
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
                # exists sessions can't hold file objects, but they can
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

def _apply_remember_me(request):
    """
    Call right after login(). Checked → session rolls for
    SESSION_COOKIE_AGE (3 days), reset on every request. Unchecked →
    session ends when the browser closes, regardless of the global
    SESSION_COOKIE_AGE setting.
    """
    if request.POST.get('remember_me'):
        request.session.set_expiry(settings.SESSION_COOKIE_AGE)
    else:
        request.session.set_expiry(0)


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
                _apply_remember_me(request)
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
                _apply_remember_me(request)
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
                _apply_remember_me(request)
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
                _apply_remember_me(request)
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
                    fail_silently=False,
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


@role_required(User.Role.VET)
def update_appointment_status_view(request, appointment_id):
    """
    Closes the loop the vet dashboard previously left open — until now,
    appointments just sat as 'Requested' forever with no way for the
    vet to confirm or cancel them, and the owner never heard back.
    """
    appointment = Appointment.objects.filter(id=appointment_id, vet=request.user).select_related('pet', 'pet__owner').first()
    if not appointment:
        return redirect('core:veterinary_dashboard')

    new_status = request.POST.get('status')
    if new_status in (Appointment.Status.CONFIRMED, Appointment.Status.CANCELLED, Appointment.Status.COMPLETED):
        appointment.status = new_status
        appointment.save()

        owner = appointment.pet.owner
        create_notification(
            recipient=owner,
            recipient_role=_recipient_role_for(owner),
            notification_type='appointment',
            title=f"Appointment {appointment.get_status_display()}",
            message=(
                f"Dr. {request.user.get_full_name() or request.user.username} has "
                f"{appointment.get_status_display().lower()} your appointment for "
                f"{appointment.pet.name} on {appointment.scheduled_time:%b %d, %Y at %I:%M %p}."
            ),
            action_url="/dashboard/pet-owner/",
        )
        # Also send the vet their own confirmation receipt of the action
        # they just took, so both sides have a paper trail in email.
        create_notification(
            recipient=request.user,
            recipient_role=_recipient_role_for(request.user),
            notification_type='appointment',
            title=f"You {appointment.get_status_display().lower()} an appointment",
            message=(
                f"You {appointment.get_status_display().lower()} the appointment for "
                f"{appointment.pet.name} (owner: {owner.get_full_name() or owner.username}) "
                f"on {appointment.scheduled_time:%b %d, %Y at %I:%M %p}."
            ),
            action_url="/dashboard/veterinary/appointments/",
        )

    return redirect('core:veterinary_dashboard')


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

# Medicine search + detail


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


@login_required(login_url='core:pet_owner_login')
def accessory_detail_view(request, pk):
    from django.shortcuts import get_object_or_404
    accessory = get_object_or_404(Accessory, pk=pk)
    return render(request, 'core/accessory_detail.html', {'accessory': accessory})


# ------------------------------------------------------------------
# Unified search module — the "Search for medicine, vets..." bar
# visible in every dashboard header feeds into this one view. Two
# modes, switchable via ?category=:
#   'people'     — search registered pet owners/vets/pharmacies, each
#                  result links straight to starting a chat with them
#   'pet_things' — search Medicine + Accessory together
#   'all' (default) — shows both sections on one page
# ------------------------------------------------------------------

@login_required(login_url='core:pet_owner_login')
def search_view(request):
    query = request.GET.get('q', '').strip()
    category = request.GET.get('category', 'all')

    people_results = []
    pet_things_results = []

    if query and category in ('people', 'all'):
        people_results = User.objects.filter(
            Q(username__icontains=query) | Q(email__icontains=query) |
            Q(first_name__icontains=query) | Q(last_name__icontains=query)
        ).exclude(id=request.user.id).exclude(is_superuser=True)[:20]

    if query and category in ('pet_things', 'all'):
        medicines = Medicine.objects.filter(Q(name__icontains=query) | Q(category__icontains=query))
        accessories = Accessory.objects.filter(Q(name__icontains=query) | Q(category__icontains=query))
        pet_things_results = (
            [{'kind': 'medicine', 'obj': m} for m in medicines] +
            [{'kind': 'accessory', 'obj': a} for a in accessories]
        )

    return render(request, 'core/search.html', {
        'query': query,
        'category': category,
        'people_results': people_results,
        'pet_things_results': pet_things_results,
    })


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
    """
    Superseded by the richer pet_profiles app (medical records,
    vaccinations, medications, per-pet care notes) — this URL name is
    kept alive (in case anything still links to it by name) but just
    hands off to the new module instead of rendering its own page.
    """
    return redirect('pet_profiles:home')


# ------------------------------------------------------------------
# Find nearest vets "lists real vet accounts. NOTE: there is no real
# geolocation, distance, or ratings data anywhere in this system yet,
# so "distance" and star ratings from the original design are NOT
# rendered here (no data to back them) :only real fields: name,
# specialization, email/phone for contact, and a link to book/chat.
# ------------------------------------------------------------------

@login_required(login_url='core:pet_owner_login')
def find_nearest_vets_view(request):
    """
    Combined "Find Nearby Care" locator — covers both veterinary
    clinics AND pharmacies, the two location-relevant registered
    entity types in the system. Filterable via ?type=vet|pharmacy|all.

    If the browser supplies ?lat=&lng= (via navigator.geolocation on
    the frontend), results with a saved location are sorted by real
    distance using PostGIS. Results without a saved location, or when
    no lat/lng is supplied at all, are just listed with no distance
    shown — no fake numbers are ever displayed.
    """
    type_filter = request.GET.get('type', 'all')

    user_point = None
    lat = request.GET.get('lat')
    lng = request.GET.get('lng')
    if lat and lng:
        try:
            user_point = Point(float(lng), float(lat), srid=4326)
        except (TypeError, ValueError):
            user_point = None

    vets = []
    pharmacies = []

    if type_filter in ('all', 'vet'):
        vets = User.objects.filter(role=User.Role.VET).select_related('vet_profile')
        if user_point:
            vets = vets.filter(vet_profile__location__isnull=False).annotate(
                distance=Distance('vet_profile__location', user_point)
            ).order_by('distance')

    if type_filter in ('all', 'pharmacy'):
        pharmacies = User.objects.filter(role=User.Role.PHARMACY).select_related('pharmacy_profile')
        if user_point:
            pharmacies = pharmacies.filter(pharmacy_profile__location__isnull=False).annotate(
                distance=Distance('pharmacy_profile__location', user_point)
            ).order_by('distance')

    return render(request, 'core/find_nearest_vets.html', {
        'vets': vets,
        'pharmacies': pharmacies,
        'type_filter': type_filter,
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
def veterinary_appointments_view(request):
    """
    The full appointments list — the dashboard itself only ever showed
    TODAY's appointments; the sidebar 'Appointments' link had nowhere
    real to go until now.
    """
    status_filter = request.GET.get('status', 'all')
    appointments = Appointment.objects.filter(vet=request.user).select_related('pet', 'pet__owner').order_by('scheduled_time')
    if status_filter in (Appointment.Status.REQUESTED, Appointment.Status.CONFIRMED, Appointment.Status.COMPLETED, Appointment.Status.CANCELLED):
        appointments = appointments.filter(status=status_filter)

    return render(request, 'core/veterinary_appointments.html', {
        'appointments': appointments,
        'status_filter': status_filter,
        'status_choices': [('all', 'All')] + list(Appointment.Status.choices),
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

    pending_prescriptions_count = Prescription.objects.filter(
        vet=request.user, status=Prescription.Status.PENDING
    ).count()

    return render(request, 'core/veterinary_dashboard.html', {
        'todays_appointments': todays_appointments,
        'total_patients': total_patients,
        'pending_prescriptions_count': pending_prescriptions_count,
    })


@role_required(User.Role.PHARMACY)
def pharmacy_dashboard(request):
    if request.method == 'POST':
        action = request.POST.get('action', 'fulfill')
        prescription_id = request.POST.get('prescription_id')

        if action == 'set_reminder':
            reminder_date = request.POST.get('reminder_date')
            prescription = Prescription.objects.filter(id=prescription_id).select_related('pet', 'pet__owner').first()
            if prescription and reminder_date:
                prescription.reminder_date = reminder_date
                prescription.reminder_sent = False  # allow re-triggering if the date was changed
                prescription.save(update_fields=['reminder_date', 'reminder_sent'])
                # Confirmation that the reminder was set — sent immediately,
                # separate from the actual reminder which fires the day before.
                create_notification(
                    recipient=prescription.pet.owner,
                    recipient_role=_recipient_role_for(prescription.pet.owner),
                    notification_type='medicine',
                    title="Medicine reminder set",
                    message=(
                        f"A reminder has been set for {prescription.pet.name}'s "
                        f"{prescription.medicine_name} on {prescription.reminder_date:%b %d, %Y}."
                    ),
                    action_url="/dashboard/pet-owner/",
                )
            return redirect('core:pharmacy_dashboard')

        # Fulfill action: mark a pending prescription as fulfilled by this pharmacy.
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
def admin_create_user_view(request):
    """
    Real, embedded user-creation form — replaces sending admins out to
    Django admin's generic (and previously unstyled, due to the Daphne
    static-file gap) add-user page. Creates the User + matching role
    profile in one step, same pattern as the public signup views, just
    without the OTP step since an admin is creating this account
    directly and doesn't need to verify their own identity.
    """
    if not (request.user.is_staff or request.user.is_superuser):
        messages.error(request, "You don't have access to that page.")
        return redirect('core:landing_page')

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip()
        phone_number = request.POST.get('phone_number', '').strip()
        password = request.POST.get('password', '')
        role = request.POST.get('role', '')
        pharmacy_name = request.POST.get('pharmacy_name', '').strip()

        errors = _validate_signup_fields(username, email, password, password)  # password==password2 since there's no confirm field here
        if role not in (User.Role.USER, User.Role.VET, User.Role.PHARMACY):
            errors.setdefault('role', []).append('Choose a valid role.')

        if not errors:
            user = User.objects.create_user(
                username=username, email=email, password=password,
                phone_number=phone_number, role=role,
            )
            if role == User.Role.USER:
                UserProfile.objects.create(user=user)
            elif role == User.Role.VET:
                VetProfile.objects.create(user=user)
            elif role == User.Role.PHARMACY:
                PharmacyProfile.objects.create(user=user, pharmacy_name=pharmacy_name)

            messages.success(request, f"{username} was created as a {user.get_role_display()}.")
            return redirect('core:admin_dashboard')

        messages.error(request, " ".join(msg for msgs in errors.values() for msg in msgs))

    return redirect('core:admin_dashboard')


@login_required(login_url='core:admin_login')
def admin_add_medicine_view(request):
    if not (request.user.is_staff or request.user.is_superuser):
        return redirect('core:landing_page')
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        if name:
            Medicine.objects.create(
                name=name,
                category=request.POST.get('category', '').strip(),
                price=request.POST.get('price') or None,
                description=request.POST.get('description', '').strip(),
                in_stock=True,
            )
            messages.success(request, f"{name} added to Medicine catalog.")
    return redirect('core:admin_dashboard')


@login_required(login_url='core:admin_login')
def admin_toggle_medicine_stock_view(request, item_id):
    if not (request.user.is_staff or request.user.is_superuser):
        return redirect('core:landing_page')
    if request.method == 'POST':
        item = Medicine.objects.filter(id=item_id).first()
        if item:
            item.in_stock = not item.in_stock
            item.save(update_fields=['in_stock'])
    return redirect('core:admin_dashboard')


@login_required(login_url='core:admin_login')
def admin_delete_medicine_view(request, item_id):
    if not (request.user.is_staff or request.user.is_superuser):
        return redirect('core:landing_page')
    if request.method == 'POST':
        Medicine.objects.filter(id=item_id).delete()
        messages.success(request, "Medicine removed.")
    return redirect('core:admin_dashboard')


@login_required(login_url='core:admin_login')
def admin_add_accessory_view(request):
    if not (request.user.is_staff or request.user.is_superuser):
        return redirect('core:landing_page')
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        if name:
            Accessory.objects.create(
                name=name,
                category=request.POST.get('category', '').strip(),
                price=request.POST.get('price') or None,
                description=request.POST.get('description', '').strip(),
                in_stock=True,
            )
            messages.success(request, f"{name} added to Accessory catalog.")
    return redirect('core:admin_dashboard')


@login_required(login_url='core:admin_login')
def admin_toggle_accessory_stock_view(request, item_id):
    if not (request.user.is_staff or request.user.is_superuser):
        return redirect('core:landing_page')
    if request.method == 'POST':
        item = Accessory.objects.filter(id=item_id).first()
        if item:
            item.in_stock = not item.in_stock
            item.save(update_fields=['in_stock'])
    return redirect('core:admin_dashboard')


@login_required(login_url='core:admin_login')
def admin_delete_accessory_view(request, item_id):
    if not (request.user.is_staff or request.user.is_superuser):
        return redirect('core:landing_page')
    if request.method == 'POST':
        Accessory.objects.filter(id=item_id).delete()
        messages.success(request, "Accessory removed.")
    return redirect('core:admin_dashboard')


@login_required(login_url='core:admin_login')
def admin_dashboard(request):
    if not (request.user.is_staff or request.user.is_superuser):
        messages.error(request, "You don't have access to that page.")
        return redirect('core:landing_page')

    stats = {
        'total_owners': User.objects.filter(role=User.Role.USER).count(),
        'total_vets': User.objects.filter(role=User.Role.VET).count(),
        'total_pharmacies': User.objects.filter(role=User.Role.PHARMACY).count(),
        'total_medicines': Medicine.objects.count(),
        'total_accessories': Accessory.objects.count(),
        'total_appointments': Appointment.objects.count(),
        'pending_prescriptions': Prescription.objects.filter(status=Prescription.Status.PENDING).count(),
        'total_pets': Pet.objects.count(),
    }

    recent_users = User.objects.exclude(is_superuser=True).order_by('-date_joined')[:15]
    all_medicines = Medicine.objects.order_by('-created_at')
    all_accessories = Accessory.objects.order_by('-created_at')
    all_appointments = Appointment.objects.select_related('pet', 'pet__owner', 'vet').order_by('-scheduled_time')[:20]
    all_prescriptions = Prescription.objects.select_related('pet', 'vet', 'pharmacy').order_by('-created_at')[:20]

    return render(request, 'core/admin_dashboard.html', {
        'stats': stats,
        'recent_users': recent_users,
        'all_medicines': all_medicines,
        'all_accessories': all_accessories,
        'all_appointments': all_appointments,
        'all_prescriptions': all_prescriptions,
    })


@login_required(login_url='core:admin_login')
def toggle_user_active_view(request, user_id):
    """
    Real add/remove-user control — 'remove' is a soft deactivation
    (is_active=False) rather than a hard delete, since hard-deleting a
    User would cascade-delete their pets/appointments/prescriptions
    (all FK on_delete=CASCADE). Full destructive delete, if ever
    needed, stays in Django admin where that risk is explicit.
    """
    if not (request.user.is_staff or request.user.is_superuser):
        messages.error(request, "You don't have access to that page.")
        return redirect('core:landing_page')

    if request.method == 'POST':
        target = User.objects.filter(id=user_id).exclude(is_superuser=True).first()
        if target:
            target.is_active = not target.is_active
            target.save(update_fields=['is_active'])
            messages.success(request, f"{target.username} was {'reactivated' if target.is_active else 'deactivated'}.")

    return redirect('core:admin_dashboard')


@login_required(login_url='core:pet_owner_login')
def chatbot_view(request):
    return render(request, 'core/chatbot_assistant.html')