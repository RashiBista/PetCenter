from django.shortcuts import get_object_or_404

from .models import Pet


def owner_for_request(request):
    """
    Return the signed-in owner. The original module's "demo mode" bypass
    (auto-creating/reusing a fake account for anonymous visitors) has
    been removed entirely — this project has a real, complete auth
    system (login/signup/OTP/lockout), and every view using this
    function is already wrapped in @login_required, so request.user
    is guaranteed to be a real authenticated account here.
    """
    return request.user


def owned_pet_or_404(request, pet_uuid):
    owner = owner_for_request(request)
    return get_object_or_404(Pet, uuid=pet_uuid, owner=owner)