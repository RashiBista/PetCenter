import uuid
from django.conf import settings
from django.db import models
from apps.applications.models import AdoptionApplication


class Conversation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    application = models.ForeignKey(
        AdoptionApplication, on_delete=models.CASCADE, related_name="conversations", null=True, blank=True
    )
    participants = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name="conversations")
    created_at = models.DateTimeField(auto_now_add=True)


class Message(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name="messages")
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="sent_messages")
    body = models.TextField()
    is_read = models.BooleanField(default=False)
    sent_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["sent_at"]


class Notification(models.Model):
    class NotificationType(models.TextChoices):
        NEW_MATCH = "new_match", "New Saved Search Match"
        APPLICATION_UPDATE = "application_update", "Application Status Update"
        NEW_MESSAGE = "new_message", "New Message"
        MEET_AND_GREET_REMINDER = "meet_and_greet_reminder", "Meet & Greet Reminder"
        POST_ADOPTION_CHECKIN = "post_adoption_checkin", "Post-Adoption Check-In"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications")
    notification_type = models.CharField(max_length=30, choices=NotificationType.choices)
    title = models.CharField(max_length=255)
    body = models.TextField(blank=True)
    link_url = models.CharField(max_length=500, blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
