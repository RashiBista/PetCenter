import json

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from django.db.models import Q

from chat.models import ChatRoom, Message


class ChatConsumer(AsyncWebsocketConsumer):
    """
    Handles a single ChatRoom's WebSocket connection.

    Auth note: self.scope['user'] is populated by chat.middleware.JWTAuthMiddleware
    (NOT Django's session-based AuthMiddlewareStack). The frontend must connect
    with the JWT access token as a query param:

        ws://<host>/ws/chat/<room_id>/?token=<access_token>
    """

    async def connect(self):
        self.user = self.scope['user']

        if not self.user.is_authenticated:
            await self.close(code=4001)
            return

        self.room_id = self.scope['url_route']['kwargs']['room_id']

        is_member = await self.is_participant()
        if not is_member:
            await self.close(code=4003)
            return

        self.room_group_name = f'chat_{self.room_id}'
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

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

        message = await self.save_message(message_text)

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