from rest_framework import permissions


class IsShelterStaffOfObject(permissions.BasePermission):
    """
    Grants write access only to staff/admins belonging to the shelter
    that owns the object (Animal, Application, etc.). Read access is open.
    Expects the object to expose `.shelter` directly or via `.animal.shelter`.
    """

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True

        if request.user.role == "platform_admin":
            return True

        shelter = getattr(obj, "shelter", None) or getattr(getattr(obj, "animal", None), "shelter", None)
        if shelter is None:
            return False

        return shelter.staff_memberships.filter(user=request.user).exists()


class IsApplicantOrShelterStaff(permissions.BasePermission):
    """
    For AdoptionApplication objects: the applicant can view/withdraw their
    own application; shelter staff for that animal's shelter can view/manage it.
    """

    def has_object_permission(self, request, view, obj):
        if obj.applicant_id == request.user.id:
            return request.method in permissions.SAFE_METHODS or view.action == "withdraw"

        is_staff = obj.animal.shelter.staff_memberships.filter(user=request.user).exists()
        return is_staff or request.user.role == "platform_admin"


class IsShelterStaff(permissions.BasePermission):
    """Generic check: user has at least one active shelter staff membership."""

    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and (request.user.role in ["shelter_staff", "shelter_admin", "platform_admin"])
        )
