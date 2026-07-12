from django.conf import settings
from django.db import models
from django.utils import timezone


class Notification(models.Model):
    class RecipientRole(models.TextChoices):
        CLIENT = "client", "Client"
        VET = "vet", "Vet"

    class NotificationType(models.TextChoices):
        GENERAL = "general", "General"
        APPOINTMENT = "appointment", "Appointment"
        MEDICINE = "medicine", "Medicine Reminder"
        CHAT = "chat", "Chat Message"
        ADOPTION = "adoption", "Adoption"
        LOST_FOUND = "lost_found", "Lost and Found"
        REPORT = "report", "Report"
        SYSTEM = "system", "System"

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="received_notifications",
    )

    recipient_role = models.CharField(
        max_length=20,
        choices=RecipientRole.choices,
    )

    notification_type = models.CharField(
        max_length=30,
        choices=NotificationType.choices,
        default=NotificationType.GENERAL,
    )

    title = models.CharField(max_length=255)

    message = models.TextField()

    action_url = models.CharField(
        max_length=500,
        blank=True,
    )

    metadata = models.JSONField(
        default=dict,
        blank=True,
    )

    is_read = models.BooleanField(default=False)

    read_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    email_sent = models.BooleanField(default=False)

    email_error = models.TextField(
        blank=True,
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

        indexes = [
            models.Index(
                fields=[
                    "recipient",
                    "is_read",
                    "created_at",
                ]
            ),
            models.Index(
                fields=[
                    "recipient_role",
                    "created_at",
                ]
            ),
        ]

    def mark_as_read(self):
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()

            self.save(
                update_fields=[
                    "is_read",
                    "read_at",
                ]
            )

    def __str__(self):
        return (
            f"{self.recipient.username}: "
            f"{self.title}"
        )