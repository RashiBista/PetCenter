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
