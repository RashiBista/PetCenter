from django.contrib import admin
from .models import ChatRoom, Message


@admin.register(ChatRoom)
class ChatRoomAdmin(admin.ModelAdmin):
    list_display = ("id", "participant_1", "participant_2", "room_type", "updated_at")
    list_filter = ("room_type",)
    search_fields = ("participant_1__username", "participant_2__username")
    readonly_fields = ("created_at", "updated_at")


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ("id", "room", "sender", "content_preview", "timestamp", "is_read")
    list_filter = ("is_read",)
    search_fields = ("sender__username", "content")
    readonly_fields = ("timestamp",)

    def content_preview(self, obj):
        return obj.content[:60]
    content_preview.short_description = "Content"