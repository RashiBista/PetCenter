import json

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from django.db.models import Q

from chat.models import ChatRoom, Message

MAX_MESSAGE_LENGTH = 2000  # keep in sync with Message.content max_length


class ChatConsumer(AsyncWebsocketConsumer):
    """
    Handles a single ChatRoom's WebSocket connection.

    Auth note: self.scope['user'] is populated by chat.middleware.JWTAuthMiddleware
    (NOT Django's session-based AuthMiddlewareStack). The frontend must connect
    with the JWT access token as a query param:

        ws://<host>/ws/chat/<room_id>/?token=<access_token>
    """

    async def connect(self):
        print("STEP 1: connect() called", flush=True)
        self.user = self.scope['user']
        print(f"STEP 2: user = {self.user}, authenticated = {self.user.is_authenticated}", flush=True)

        if not self.user.is_authenticated:
            print("STEP 2b: closing - not authenticated", flush=True)
            await self.close(code=4001)
            return

        self.room_id = self.scope['url_route']['kwargs']['room_id']
        print(f"STEP 3: room_id = {self.room_id}", flush=True)

        is_member = await self.is_participant()
        print(f"STEP 4: is_member = {is_member}", flush=True)
        if not is_member:
            print("STEP 4b: closing - not a member", flush=True)
            await self.close(code=4003)
            return

        self.room_group_name = f'chat_{self.room_id}'
        print(f"STEP 5: about to group_add, group_name = {self.room_group_name}", flush=True)
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        print("STEP 6: group_add succeeded, about to accept()", flush=True)
        await self.accept()
        print("STEP 7: accept() succeeded - CONNECTION SHOULD BE OPEN NOW", flush=True)

    async def disconnect(self, close_code):
        if hasattr(self, 'room_group_name'):
            await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
        except json.JSONDecodeError:
            return

        message_text = data.get('message', '').strip()
        if not message_text:
            return

        if len(message_text) > MAX_MESSAGE_LENGTH:
            await self.send(text_data=json.dumps({
                'error': f'Message exceeds {MAX_MESSAGE_LENGTH} character limit.',
            }))
            return

        message = await self.save_message(message_text)

        # Notify the other participant — this creates a real Notification
        # row and schedules a real email via notifications.services, same
        # as the appointment-booking trigger in core/views.py.
        await self.notify_other_participant(message_text)

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat_message',
                'message': message_text,
                'sender': self.user.username,
                'sender_id': self.user.id,
                'timestamp': str(message.timestamp),
            }
        )

    async def chat_message(self, event):
        await self.send(text_data=json.dumps({
            'message': event['message'],
            'sender': event['sender'],
            'sender_id': event['sender_id'],
            'timestamp': event['timestamp'],
        }))

    # ---- DB helpers (sync ORM calls wrapped for async context) ----

    @database_sync_to_async
    def is_participant(self):
        return ChatRoom.objects.filter(
            Q(pk=self.room_id),
            Q(participant_1=self.user) | Q(participant_2=self.user)
        ).exists()

    @database_sync_to_async
    def save_message(self, content):
        room = ChatRoom.objects.get(pk=self.room_id)
        return Message.objects.create(
            room=room,
            sender=self.user,
            content=content
        )

    @database_sync_to_async
    def notify_other_participant(self, message_text):
        from myapp.models import User
        from notifications.models import Notification
        from notifications.services import create_notification

        room = ChatRoom.objects.get(pk=self.room_id)
        other_user = room.get_other_participant(self.user)

        recipient_role = (
            Notification.RecipientRole.VET
            if other_user.role == User.Role.VET
            else Notification.RecipientRole.CLIENT
        )

        preview = message_text if len(message_text) <= 100 else message_text[:97] + "..."
        create_notification(
            recipient=other_user,
            recipient_role=recipient_role,
            notification_type='chat',
            title=f"New message from {self.user.get_full_name() or self.user.username}",
            message=preview,
            action_url=f"/chat/room/{room.pk}/",
        )