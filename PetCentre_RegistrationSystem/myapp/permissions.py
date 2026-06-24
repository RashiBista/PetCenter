from rest_framework.permissions import BasePermission

from .models import User


class IsPetOwner(BasePermission):
    """Allows access only to authenticated users with role=USER."""
    message = 'This action is restricted to pet-owner accounts.'

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role == User.Role.USER
        )


class IsVet(BasePermission):
    """Allows access only to authenticated users with role=VET."""
    message = 'This action is restricted to veterinarian accounts.'

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role == User.Role.VET
        )
