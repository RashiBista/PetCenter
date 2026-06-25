from django.db import models
from django.contrib.auth import get_user_model
from django.conf import settings
from django.utils import timezone


class ChatRoom(models.Model):
    """
    A private 1-to-1 chat room between two users.
    Supports all combinations: pet_owner <-> vet, pet_owner <-> pharmacy,
    pet_owner <-> blood_bank, and general user <-> user.
    """

    ROOM_TYPE_CHOICES = [
        ("owner_vet", "Pet Owner ↔ Vet"),
        ("owner_pharmacy", "Pet Owner ↔ Pharmacy"),
        ("owner_bloodbank", "Pet Owner ↔ Blood Bank"),
        ("general", "General"),
    ]

    room_type = models.CharField(
        max_length=20, choices=ROOM_TYPE_CHOICES, default="general"
    )

    # Use settings.AUTH_USER_MODEL string instead of get_user_model()
    # This avoids AppRegistryNotReady errors at import time
    participant_1 = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="chat_rooms_as_p1",
    )
    participant_2 = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="chat_rooms_as_p2",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("participant_1", "participant_2")
        ordering = ["-updated_at"]

    def __str__(self):
        return f"Room({self.participant_1.username} ↔ {self.participant_2.username})"

    @classmethod
    def get_or_create_room(cls, user_a, user_b):
        if user_a.pk > user_b.pk:
            user_a, user_b = user_b, user_a
        room, created = cls.objects.get_or_create(
            participant_1=user_a,
            participant_2=user_b,
        )
        return room, created

    def get_other_participant(self, user):
        if self.participant_1 == user:
            return self.participant_2
        return self.participant_1

    def get_room_name(self):
        return f"chat_{self.pk}"

    @property
    def last_message(self):
        return self.messages.order_by("-timestamp").first()


class Message(models.Model):
    room = models.ForeignKey(ChatRoom, on_delete=models.CASCADE, related_name="messages")
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="sent_messages"
    )
    content = models.TextField(max_length=2000)
    timestamp = models.DateTimeField(default=timezone.now, db_index=True)
    is_read = models.BooleanField(default=False)

    class Meta:
        ordering = ["timestamp"]

    def __str__(self):
        return f"{self.sender.username}: {self.content[:50]}"