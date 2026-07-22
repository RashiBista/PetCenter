from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Q, Count
from rest_framework_simplejwt.tokens import RefreshToken

from .models import ChatRoom, Message
from myapp.models import Appointment

User = get_user_model()


@login_required
def inbox(request):
    """
    Shows all chat rooms the current user participates in,
    ordered by most recent activity. Includes unread count per room.
    """
    rooms = list(
        ChatRoom.objects.filter(
            Q(participant_1=request.user) | Q(participant_2=request.user)
        ).select_related("participant_1", "participant_2").order_by("-updated_at")
    )
    room_ids = [room.pk for room in rooms]

    # Previously each room.last_message + unread count was its own query
    # (2N+1 total for N rooms) — every extra round trip to a remote DB
    # adds real, noticeable latency, so these are batched into one query
    # each regardless of how many rooms there are.
    last_messages = {
        message.room_id: message
        for message in Message.objects.filter(room_id__in=room_ids)
            .select_related("sender")
            .order_by("room_id", "-timestamp")
            .distinct("room_id")
    }
    unread_counts = dict(
        Message.objects.filter(room_id__in=room_ids, is_read=False)
        .exclude(sender=request.user)
        .values("room_id")
        .annotate(count=Count("id"))
        .values_list("room_id", "count")
    )

    rooms_data = [
        {
            "room": room,
            "other_user": room.get_other_participant(request.user),
            "last_message": last_messages.get(room.pk),
            "unread_count": unread_counts.get(room.pk, 0),
        }
        for room in rooms
    ]

    return render(request, "chat/inbox.html", {
        "rooms_data": rooms_data,
        "page_title": "Messages",
    })


@login_required
def start_chat(request, user_id):
    """
    GET  → renders a confirmation page  (rarely needed)
    POST → creates/fetches a room with the target user and redirects to it

    Chat is restricted to pet-owner <-> vet pairs, and only once the vet
    has accepted (confirmed) an appointment from that pet owner — chat is
    meant as a follow-up channel for an existing consultation, not a
    general-purpose messenger.
    """
    target_user = get_object_or_404(User, pk=user_id)

    if target_user == request.user:
        return redirect("chat:inbox")

    if request.user.is_pet_owner and target_user.is_vet:
        owner, vet = request.user, target_user
    elif request.user.is_vet and target_user.is_pet_owner:
        owner, vet = target_user, request.user
    else:
        messages.error(request, "Chat is only available between a pet owner and a vet.")
        return redirect("chat:inbox")

    has_confirmed_appointment = Appointment.objects.filter(
        pet__owner=owner, vet=vet, status=Appointment.Status.CONFIRMED
    ).exists()

    if not has_confirmed_appointment:
        messages.error(
            request,
            "You can only chat with a vet once they've accepted an appointment with you.",
        )
        return redirect("chat:inbox")

    room, _ = ChatRoom.get_or_create_room(request.user, target_user)
    return redirect("chat:room", room_uuid=room.uuid)


@login_required
def room_legacy(request, room_id):
    """
    Backward-compat for integer room URLs that still exist in the wild
    (stored notification action_urls, old bookmarks) — permanently
    redirects to the opaque UUID address.
    """
    chat_room = get_object_or_404(ChatRoom, pk=room_id)
    if request.user not in (chat_room.participant_1, chat_room.participant_2):
        return redirect("chat:inbox")
    return redirect("chat:room", room_uuid=chat_room.uuid)


@login_required
def room(request, room_uuid):
    """
    The main chat room view. Renders the last 50 messages.
    WebSocket connection is established client-side via JS.

    ws_token: ChatConsumer authenticates over WebSocket via JWTAuthMiddleware
    (see chat/middlewares.py) — a completely separate auth path from this
    view's session-based @login_required. Without minting a token here,
    room.html's {{ ws_token }} renders empty, producing a WebSocket URL
    like ?token= with nothing after it, which JWTAuthMiddleware treats as
    AnonymousUser and the consumer rejects.
    """
    chat_room = get_object_or_404(ChatRoom, uuid=room_uuid)

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

    # Mint a short-lived JWT so the WebSocket handshake can authenticate.
    ws_token = str(RefreshToken.for_user(request.user).access_token)

    return render(request, "chat/room.html", {
        "room": chat_room,
        "other_user": other_user,
        "messages": messages,
        "ws_token": ws_token,
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