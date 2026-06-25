import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.utils import timezone
from .models import ChatRoom, Message


class ChatConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for real-time chat.

    Connection URL pattern:  ws/chat/<room_id>/
    Each room maps to a Channel Layer group named  chat_<room_id>

    Lifecycle:
        connect    → join the group, mark older messages as read
        disconnect → leave the group
        receive    → save message to DB, broadcast to group
    """

    async def connect(self):
        self.room_id = self.scope["url_route"]["kwargs"]["room_id"]
        self.room_group_name = f"chat_{self.room_id}"
        self.user = self.scope["user"]

        # Reject unauthenticated connections immediately
        if not self.user.is_authenticated:
            await self.close()
            return

        # Verify the user actually belongs to this room
        room = await self.get_room()
        if room is None:
            await self.close()
            return

        self.room = room

        # Join the channel layer group
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

        # Mark all unread messages in this room as read for the current user
        await self.mark_messages_read()

    async def disconnect(self, close_code):
        if hasattr(self, "room_group_name"):
            await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data):
        """Handle an incoming message from the WebSocket client."""
        try:
            data = json.loads(text_data)
            content = data.get("message", "").strip()
        except (json.JSONDecodeError, KeyError):
            return

        if not content or len(content) > 2000:
            return

        # Save to DB
        message = await self.save_message(content)

        # Broadcast to both users in the room
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "chat_message",
                "message_id": message.id,
                "content": content,
                "sender_id": self.user.id,
                "sender_username": self.user.username,
                "sender_full_name": self.user.get_full_name() or self.user.username,
                "timestamp": message.timestamp.strftime("%Y-%m-%dT%H:%M:%S"),
                "is_own": False,  # Will be overridden per-client
            },
        )

    async def chat_message(self, event):
        """Receive a message from the channel layer group and forward to WebSocket."""
        # Tell each client whether this message belongs to them
        event["is_own"] = event["sender_id"] == self.user.id
        await self.send(text_data=json.dumps(event))

    # ─── Database helpers (run in thread pool via database_sync_to_async) ────

    @database_sync_to_async
    def get_room(self):
        try:
            room = ChatRoom.objects.get(pk=self.room_id)
            if self.user not in (room.participant_1, room.participant_2):
                return None
            return room
        except ChatRoom.DoesNotExist:
            return None

    @database_sync_to_async
    def save_message(self, content):
        msg = Message.objects.create(
            room=self.room,
            sender=self.user,
            content=content,
        )
        # Bump room's updated_at so inbox ordering stays fresh
        ChatRoom.objects.filter(pk=self.room.pk).update(updated_at=timezone.now())
        return msg

    @database_sync_to_async
    def mark_messages_read(self):
        Message.objects.filter(
            room=self.room,
            is_read=False,
        ).exclude(sender=self.user).update(is_read=True)