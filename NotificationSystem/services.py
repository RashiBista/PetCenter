import logging

from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction

from .models import Notification


logger = logging.getLogger(__name__)


def send_notification_email(
    notification_id: int,
) -> None:
    try:
        notification = (
            Notification.objects
            .select_related("recipient")
            .get(id=notification_id)
        )
    except Notification.DoesNotExist:
        return

    recipient_email = notification.recipient.email

    if not recipient_email:
        Notification.objects.filter(
            id=notification.id
        ).update(
            email_error=(
                "Recipient has no email address."
            )
        )
        return

    try:
        emails_sent = send_mail(
            subject=notification.title,
            message=notification.message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[recipient_email],
            fail_silently=False,
        )

        if emails_sent:
            Notification.objects.filter(
                id=notification.id
            ).update(
                email_sent=True,
                email_error="",
            )

    except Exception as error:
        logger.exception(
            "Notification email failed."
        )

        Notification.objects.filter(
            id=notification.id
        ).update(
            email_sent=False,
            email_error=str(error),
        )


def create_notification(
    *,
    recipient,
    recipient_role: str,
    title: str,
    message: str,
    notification_type: str = "general",
    action_url: str = "",
    metadata: dict | None = None,
    send_email_notification: bool = True,
) -> Notification:
    if recipient_role not in (
        Notification.RecipientRole.values
    ):
        raise ValueError(
            f"Invalid recipient role: {recipient_role}"
        )

    if notification_type not in (
        Notification.NotificationType.values
    ):
        raise ValueError(
            "Invalid notification type: "
            f"{notification_type}"
        )

    with transaction.atomic():
        notification = Notification.objects.create(
            recipient=recipient,
            recipient_role=recipient_role,
            notification_type=notification_type,
            title=title,
            message=message,
            action_url=action_url,
            metadata=metadata or {},
        )

        if send_email_notification:
            transaction.on_commit(
                lambda notification_id=notification.id:
                send_notification_email(
                    notification_id
                )
            )

    return notification
