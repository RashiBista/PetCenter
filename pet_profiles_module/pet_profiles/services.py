from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404

from .models import Pet


def owner_for_request(request):
    """
    Return the signed-in owner.

    Demo mode exists only so the module works while the current project still
    uses click-through login screens. Disable it as soon as real login is wired.
    """
    if request.user.is_authenticated:
        return request.user

    if getattr(settings, "PET_PROFILES_DEMO_MODE", False):
        username = getattr(
            settings,
            "PET_PROFILES_DEMO_USERNAME",
            "demo_pet_owner",
        )
        user_model = get_user_model()
        owner, _ = user_model.objects.get_or_create(username=username)
        return owner

    raise PermissionDenied("Please sign in to manage pet profiles.")


def owned_pet_or_404(request, pk):
    owner = owner_for_request(request)
    return get_object_or_404(Pet, pk=pk, owner=owner)
