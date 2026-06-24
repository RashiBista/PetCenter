from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth import get_user_model
from .models import ChatMessage
from .serializers import ChatMessageSerializer

User = get_user_model()

class MessageHistoryView(APIView):
    # permission_classes = [IsAuthenticated]

    def get(self, request, other_user_id):
        try:
            other_user = User.objects.get(id=other_user_id)
        except User.DoesNotExist:
            return Response({"error": "User not found"}, status=404)

        # Get messages between the two users (both directions)
        messages = ChatMessage.objects.filter(
            sender__in=[request.user, other_user],
            recipient__in=[request.user, other_user]
        ).order_by('created_at')

        serializer = ChatMessageSerializer(messages, many=True)
        return Response(serializer.data)