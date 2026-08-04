from django.urls import reverse

from notifications.models import Notification


def unread_notification_count(request):
    """
    Makes {{ unread_notification_count }} available in every template so
    the bell icon's red dot reflects real state instead of always showing.
    """
    if not request.user.is_authenticated:
        return {}
    count = Notification.objects.filter(recipient=request.user, is_read=False).count()
    return {'unread_notification_count': count}


def dashboard_url(request):
    """
    Makes {{ dashboard_url }} available in every template so the "Pet
    Centre" brand link always goes back to the current user's own
    dashboard, regardless of which subcontext it's clicked from (a pet
    profile page, Django admin, account settings, etc.) — rather than a
    single hardcoded destination that's only right for one role.
    """
    user = getattr(request, 'user', None)
    if not user or not user.is_authenticated:
        return {'dashboard_url': reverse('core:landing_page')}
    if user.is_staff or user.is_superuser:
        return {'dashboard_url': reverse('core:admin_dashboard')}
    if user.is_vet:
        return {'dashboard_url': reverse('core:veterinary_dashboard')}
    return {'dashboard_url': reverse('core:pet_owner_dashboard')}
