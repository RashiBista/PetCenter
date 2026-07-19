import asyncio
import json

from asgiref.sync import sync_to_async
from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from django.db.models import Q

from chat.models import ChatRoom, Message
from notifications.services import send_notification_email

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
        self.user = self.scope['user']

        if not self.user.is_authenticated:
            await self.close(code=4001)
            return

        self.room_id = self.scope['url_route']['kwargs']['room_id']

        # Cached here instead of re-fetched on every message — the room
        # and its participants don't change for the life of a connection,
        # so there's no reason send_message() should pay another Neon
        # round trip just to look up the other participant each time.
        self.other_user = await self.get_other_participant()
        if self.other_user is None:
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

        if len(message_text) > MAX_MESSAGE_LENGTH:
            await self.send(text_data=json.dumps({
                'error': f'Message exceeds {MAX_MESSAGE_LENGTH} character limit.',
            }))
            return

        message = await self.save_message(message_text)

        # Broadcast first so the message shows up immediately in both
        # participants' chat windows — the notification below triggers a
        # real SMTP send via notifications.services, which used to run
        # before this and made every message wait on a Gmail round-trip
        # before it appeared on screen.
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

        # Notify the other participant  this creates a real Notification
        # row and schedules a real email via notifications.services, same
        # as the appointment-booking trigger in core/views.py.
        #
        # The DB write runs on the shared thread-sensitive executor like
        # any other ORM call here, but the actual SMTP send is handed off
        # via thread_sensitive=False. database_sync_to_async's thread
        # affinity means EVERY thread-sensitive call in the whole process
        # serializes onto one shared thread — a single Gmail send taking
        # several seconds would otherwise stall every other chat
        # connection's DB queries (including new connections' is_participant
        # checks) process-wide until it finished.
        notification_id = await self.create_chat_notification(message_text, self.other_user)
        asyncio.ensure_future(
            sync_to_async(send_notification_email, thread_sensitive=False)(notification_id)
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
    def get_other_participant(self):
        try:
            room = ChatRoom.objects.get(
                Q(pk=self.room_id),
                Q(participant_1=self.user) | Q(participant_2=self.user)
            )
        except ChatRoom.DoesNotExist:
            return None
        return room.get_other_participant(self.user)

    @database_sync_to_async
    def save_message(self, content):
        return Message.objects.create(
            room_id=self.room_id,
            sender=self.user,
            content=content
        )

    @database_sync_to_async
    def create_chat_notification(self, message_text, other_user):
        from myapp.models import User
        from notifications.models import Notification
        from notifications.services import create_notification

        recipient_role = (
            Notification.RecipientRole.VET
            if other_user.role == User.Role.VET
            else Notification.RecipientRole.CLIENT
        )

        preview = message_text if len(message_text) <= 100 else message_text[:97] + "..."
        notification = create_notification(
            recipient=other_user,
            recipient_role=recipient_role,
            notification_type='chat',
            title=f"New message from {self.user.get_full_name() or self.user.username}",
            message=preview,
            action_url=f"/chat/room/{self.room_id}/",
            # We send the email ourselves (see receive()) via a
            # non-thread-sensitive executor so the slow SMTP call can't
            # stall the shared DB thread — don't let create_notification's
            # on_commit hook send it again on the blocking path.
            send_email_notification=False,
        )
        return notification.id