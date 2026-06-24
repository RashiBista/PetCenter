import json
import urllib.parse
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from django.core.cache import cache
from .models import ChatMessage
from asgiref.sync import sync_to_async
from django_redis import get_redis_connection

@sync_to_async
def redis_sadd(key, value):
    conn = get_redis_connection("default")
    conn.sadd(key, value)

@sync_to_async
def redis_srem(key, value):
    conn = get_redis_connection("default")
    conn.srem(key, value)

User = get_user_model()

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        #  FORCE the logged-in user to be 'admin' (ID=1) for testing
        # Make sure you have a user with ID=1 in your database (you created superuser).
        try:
            self.user = await database_sync_to_async(User.objects.get)(id=1)
        except User.DoesNotExist:
            print(" User with ID=1 not found. Please create a superuser.")
            await self.close()
            return

        # Parse query string to get target_user_id
        query_string = self.scope['query_string'].decode()
        params = urllib.parse.parse_qs(query_string)
        target_ids = params.get('target_user_id', [])

        if not target_ids:
            print("No target_user_id provided in WebSocket URL")
            await self.close()
            return

        try:
            target_id = int(target_ids[0])
            self.target_user = await self.get_user(target_id)
        except (ValueError, User.DoesNotExist):
            print(f" Target user with ID {target_ids[0]} not found")
            await self.close()
            return

        # Create a unique room for this pair
        user_ids = sorted([self.user.id, self.target_user.id])
        self.room_group_name = f'private_chat_{user_ids[0]}_{user_ids[1]}'
        self.user_group_name = f'user_{self.user.id}'

        # Join the room
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.channel_layer.group_add(self.user_group_name, self.channel_name)

        # Set online status
        await redis_sadd('online_users', str(self.user.id))
        await self.broadcast_status('online')

        print(f"WebSocket connected: {self.user.username} <-> {self.target_user.username}")
        await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, 'user') and self.user.is_authenticated:
            await redis_srem('online_users', str(self.user.id))
            await self.broadcast_status('offline')
            await self.channel_layer.group_discard(self.room_group_name, self.channel_name)
            await self.channel_layer.group_discard(self.user_group_name, self.channel_name)

    async def receive(self, text_data):
        data = json.loads(text_data)
        msg_type = data.get('type', 'message')

        if msg_type == 'message':
            user_msg = data.get('message', '').strip()
            if not user_msg:
                return

            # Save message to DB
            msg_obj = await self.save_message(
                sender=self.user,
                recipient=self.target_user,
                message=user_msg
            )

            # Broadcast to the private room
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'chat_message',
                    'sender_id': self.user.id,
                    'sender_username': self.user.username,
                    'message': user_msg,
                    'message_id': msg_obj.id,
                    'timestamp': str(msg_obj.created_at)
                }
            )

        elif msg_type == 'typing':
            status = data.get('status', 'off')
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'typing_indicator',
                    'sender_id': self.user.id,
                    'sender_username': self.user.username,
                    'status': status
                }
            )

        elif msg_type == 'read':
            message_id = data.get('message_id')
            if message_id:
                await self.mark_as_read(message_id)

    # --- Event Handlers ---
    async def chat_message(self, event):
        await self.send(text_data=json.dumps({
            'type': 'message',
            'sender_id': event['sender_id'],
            'sender_username': event['sender_username'],
            'message': event['message'],
            'message_id': event['message_id'],
            'timestamp': event['timestamp']
        }))

    async def typing_indicator(self, event):
        await self.send(text_data=json.dumps({
            'type': 'typing',
            'sender_id': event['sender_id'],
            'sender_username': event['sender_username'],
            'status': event['status']
        }))

    async def status_update(self, event):
        await self.send(text_data=json.dumps({
            'type': 'status',
            'user_id': event['user_id'],
            'username': event['username'],
            'status': event['status']
        }))

    # --- Helper Methods ---
    @database_sync_to_async
    def get_user(self, user_id):
        return User.objects.get(id=user_id)

    @database_sync_to_async
    def save_message(self, sender, recipient, message):
        return ChatMessage.objects.create(
            sender=sender,
            recipient=recipient,
            message=message
        )

    @database_sync_to_async
    def mark_as_read(self, message_id):
        try:
            msg = ChatMessage.objects.get(id=message_id)
            msg.is_read = True
            msg.save()
            return msg
        except ChatMessage.DoesNotExist:
            return None

    async def broadcast_status(self, status):
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'status_update',
                'user_id': self.user.id,
                'username': self.user.username,
                'status': status
            }
        )