from rest_framework import serializers
from .models import Conversation, Message, Notification


class MessageSerializer(serializers.ModelSerializer):
    sender_name = serializers.CharField(source="sender.get_full_name", read_only=True)

    class Meta:
        model = Message
        fields = ["id", "conversation", "sender", "sender_name", "body", "is_read", "sent_at"]
        read_only_fields = ["id", "sender", "is_read", "sent_at"]

    def create(self, validated_data):
        validated_data["sender"] = self.context["request"].user
        return super().create(validated_data)


class ConversationSerializer(serializers.ModelSerializer):
    messages = MessageSerializer(many=True, read_only=True)
    participant_names = serializers.SerializerMethodField()

    class Meta:
        model = Conversation
        fields = ["id", "application", "participants", "participant_names", "messages", "created_at"]
        read_only_fields = ["id", "created_at"]

    def get_participant_names(self, obj):
        return [p.get_full_name() or p.username for p in obj.participants.all()]


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ["id", "notification_type", "title", "body", "link_url", "is_read", "created_at"]
        read_only_fields = fields
