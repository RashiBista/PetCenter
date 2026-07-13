from django.contrib.auth import get_user_model

from rest_framework import serializers

from .models import Notification


User = get_user_model()


class NotificationSerializer(
    serializers.ModelSerializer
):
    recipient_username = (
        serializers.CharField(
            source="recipient.username",
            read_only=True,
        )
    )

    recipient_email = serializers.EmailField(
        source="recipient.email",
        read_only=True,
    )

    class Meta:
        model = Notification

        fields = [
            "id",
            "recipient",
            "recipient_username",
            "recipient_email",
            "recipient_role",
            "notification_type",
            "title",
            "message",
            "action_url",
            "metadata",
            "is_read",
            "read_at",
            "email_sent",
            "email_error",
            "created_at",
        ]

        read_only_fields = [
            "id",
            "recipient",
            "recipient_username",
            "recipient_email",
            "is_read",
            "read_at",
            "email_sent",
            "email_error",
            "created_at",
        ]


class NotificationCreateSerializer(
    serializers.Serializer
):
    recipient_id = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(),
        source="recipient",
    )

    recipient_role = serializers.ChoiceField(
        choices=Notification.RecipientRole.choices
    )

    notification_type = serializers.ChoiceField(
        choices=Notification.NotificationType.choices,
        default=Notification.NotificationType.GENERAL,
    )

    title = serializers.CharField(max_length=255)

    message = serializers.CharField()

    action_url = serializers.CharField(
        max_length=500,
        required=False,
        allow_blank=True,
    )

    metadata = serializers.JSONField(
        required=False,
    )

    send_email = serializers.BooleanField(
        default=True,
    )
