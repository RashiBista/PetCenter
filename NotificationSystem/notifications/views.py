from django.shortcuts import render

# Create your views here.

from django.shortcuts import get_object_or_404
from django.utils import timezone

from rest_framework import generics, status
from rest_framework.permissions import (
    IsAdminUser,
    IsAuthenticated,
)
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Notification
from .serializers import (
    NotificationCreateSerializer,
    NotificationSerializer,
)
from .services import create_notification


class NotificationListAPIView(
    generics.ListAPIView
):
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = (
            Notification.objects
            .filter(recipient=self.request.user)
            .select_related("recipient")
        )

        role = self.request.query_params.get(
            "role"
        )

        unread = self.request.query_params.get(
            "unread"
        )

        notification_type = (
            self.request.query_params.get("type")
        )

        if role in Notification.RecipientRole.values:
            queryset = queryset.filter(
                recipient_role=role
            )

        if unread == "true":
            queryset = queryset.filter(
                is_read=False
            )

        if (
            notification_type
            in Notification.NotificationType.values
        ):
            queryset = queryset.filter(
                notification_type=notification_type
            )

        return queryset


class NotificationCreateAPIView(APIView):
    """
    Standalone testing endpoint.

    In the integrated project, other modules should
    normally call create_notification() directly.
    """

    permission_classes = [IsAdminUser]

    def post(self, request):
        serializer = NotificationCreateSerializer(
            data=request.data
        )

        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data

        notification = create_notification(
            recipient=data["recipient"],
            recipient_role=data["recipient_role"],
            notification_type=data[
                "notification_type"
            ],
            title=data["title"],
            message=data["message"],
            action_url=data.get(
                "action_url",
                "",
            ),
            metadata=data.get(
                "metadata",
                {},
            ),
            send_email_notification=data.get(
                "send_email",
                True,
            ),
        )

        return Response(
            NotificationSerializer(
                notification
            ).data,
            status=status.HTTP_201_CREATED,
        )


class UnreadCountAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        queryset = Notification.objects.filter(
            recipient=request.user,
            is_read=False,
        )

        role = request.query_params.get("role")

        if role in Notification.RecipientRole.values:
            queryset = queryset.filter(
                recipient_role=role
            )

        return Response({
            "unread_count": queryset.count()
        })


class MarkNotificationReadAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, notification_id):
        notification = get_object_or_404(
            Notification,
            id=notification_id,
            recipient=request.user,
        )

        notification.mark_as_read()

        return Response(
            NotificationSerializer(
                notification
            ).data
        )


class MarkAllNotificationsReadAPIView(
    APIView
):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        queryset = Notification.objects.filter(
            recipient=request.user,
            is_read=False,
        )

        role = request.data.get("role")

        if role in Notification.RecipientRole.values:
            queryset = queryset.filter(
                recipient_role=role
            )

        updated = queryset.update(
            is_read=True,
            read_at=timezone.now(),
        )

        return Response({
            "message": (
                "Notifications marked as read."
            ),
            "updated_count": updated,
        })