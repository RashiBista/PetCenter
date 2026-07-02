from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.http import JsonResponse
from django.db.models import Q, Count
from .models import ChatRoom, Message

User = get_user_model()


@login_required
def inbox(request):
    """
    Shows all chat rooms the current user participates in,
    ordered by most recent activity. Includes unread count per room.
    """
    rooms = ChatRoom.objects.filter(
        Q(participant_1=request.user) | Q(participant_2=request.user)
    ).select_related("participant_1", "participant_2").order_by("-updated_at")

    rooms_data = []
    for room in rooms:
        other = room.get_other_participant(request.user)
        last_msg = room.last_message
        unread = Message.objects.filter(
            room=room, is_read=False
        ).exclude(sender=request.user).count()

        rooms_data.append({
            "room": room,
            "other_user": other,
            "last_message": last_msg,
            "unread_count": unread,
        })

    return render(request, "chat/inbox.html", {
        "rooms_data": rooms_data,
        "page_title": "Messages",
    })


@login_required
def start_chat(request, user_id):
    """
    GET  → renders a confirmation page  (rarely needed)
    POST → creates/fetches a room with the target user and redirects to it
    """
    target_user = get_object_or_404(User, pk=user_id)

    if target_user == request.user:
        return redirect("chat:inbox")

    room, _ = ChatRoom.get_or_create_room(request.user, target_user)
    return redirect("chat:room", room_id=room.pk)


@login_required
def room(request, room_id):
    """
    The main chat room view. Renders the last 50 messages.
    WebSocket connection is established client-side via JS.
    """
    chat_room = get_object_or_404(ChatRoom, pk=room_id)

    # Security: only participants may view the room
    if request.user not in (chat_room.participant_1, chat_room.participant_2):
        return redirect("chat:inbox")

    other_user = chat_room.get_other_participant(request.user)

    # Fetch last 50 messages — reversed for display (oldest first)
    messages = Message.objects.filter(room=chat_room).select_related("sender").order_by("-timestamp")[:50]
    messages = list(reversed(messages))

    # Mark incoming messages as read
    Message.objects.filter(
        room=chat_room, is_read=False
    ).exclude(sender=request.user).update(is_read=True)

    return render(request, "chat/room.html", {
        "room": chat_room,
        "other_user": other_user,
        "messages": messages,
        "page_title": f"Chat with {other_user.get_full_name() or other_user.username}",
    })


@login_required
def unread_count(request):
    """
    AJAX endpoint — returns the total unread message count for the navbar badge.
    Usage: GET /chat/unread/  → {"count": 3}
    """
    count = Message.objects.filter(
        room__in=ChatRoom.objects.filter(
            Q(participant_1=request.user) | Q(participant_2=request.user)
        ),
        is_read=False,
    ).exclude(sender=request.user).count()

    return JsonResponse({"count": count})