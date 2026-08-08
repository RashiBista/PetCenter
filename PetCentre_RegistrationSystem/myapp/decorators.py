from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect


def role_required(role):
    """
    Restricts a session-authenticated view to users with a specific
    `role` (myapp.models.User.Role.USER / .VET). Mirrors the intent of
    IsPetOwner/IsVet in permissions.py, but for plain Django views
    instead of DRF APIViews. Used by core/views.py's role-specific
    dashboards.
    """
    def decorator(view_func):
        @wraps(view_func)
        @login_required(login_url='core:landing_page')
        def wrapper(request, *args, **kwargs):
            # Staff/superuser accounts are administrative, not a pet owner
            # or vet — but `role` defaults to USER on every account
            # (createsuperuser never touches custom fields), so without
            # this check an admin account silently passes the USER role
            # gate and ends up stranded on pet-owner-only pages with no
            # way back except retyping the admin URL.
            if request.user.is_staff or request.user.is_superuser:
                return redirect('core:admin_dashboard')
            if request.user.role != role:
                messages.error(request, "You don't have access to that page.")
                return redirect('core:landing_page')
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator