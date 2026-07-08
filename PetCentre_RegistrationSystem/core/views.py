from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect

from myapp.decorators import role_required
from myapp.models import User


def landing_page(request):
    return render(request, 'core/landing_page.html')


# ------------------------------------------------------------------
# Login views — one per role, matching the three separate login
# templates already designed. Each authenticates, then checks the
# authenticated user actually holds the matching role/permission
# before starting the session, so a pet owner can't log in through
# the vet page (or vice versa) even with valid credentials.
# ------------------------------------------------------------------

def pet_owner_login_view(request):
    error = None
    if request.method == 'POST':
        identifier = request.POST.get('email', '').strip()  # field is named "email" in the template, accepts username or email via UsernameOrEmailBackend
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
# Dashboards — role-gated, reusing the same decorator pattern as the
# session-based chat/dashboard flow.
# ------------------------------------------------------------------

@role_required(User.Role.USER)
def pet_owner_dashboard(request):
    return render(request, 'core/pet_owner_dashboard.html')


@role_required(User.Role.VET)
def veterinary_dashboard(request):
    return render(request, 'core/veterinary_dashboard.html')


@login_required(login_url='core:admin_login')
def admin_dashboard(request):
    if not (request.user.is_staff or request.user.is_superuser):
        messages.error(request, "You don't have access to that page.")
        return redirect('core:landing_page')
    return render(request, 'core/admin_dashboard.html')


@login_required(login_url='core:pet_owner_login')
def chatbot_view(request):
    return render(request, 'core/chatbot_assistant.html')