from django.contrib import admin

# Register your models here.

from django.contrib import admin

from .models import Notification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = [
        "title",
        "recipient",
        "recipient_role",
        "notification_type",
        "is_read",
        "email_sent",
        "created_at",
    ]

    list_filter = [
        "recipient_role",
        "notification_type",
        "is_read",
        "email_sent",
        "created_at",
    ]

    search_fields = [
        "title",
        "message",
        "recipient__username",
        "recipient__email",
    ]

    readonly_fields = [
        "created_at",
        "read_at",
        "email_sent",
        "email_error",
    ]