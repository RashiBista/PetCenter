"""
Server-side proxy between the PetCentre UI and the n8n RAG workflow
(the "chatbot" workflow exported in rag/workflows.json — Gemini agent +
Pinecone vector store over the pet-care knowledge base).

The browser deliberately does not talk to n8n directly. n8n listens on
its own origin (localhost:5678 in dev) and its webhooks have no auth in
front of them, so putting that URL in the page source would let anyone
POST to the workflow and burn Gemini/Pinecone quota without being a
logged-in PetCentre user. Routing through Django keeps the workflow
behind @login_required and keeps the n8n host out of the page.
"""

import json
import logging

import requests
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST

logger = logging.getLogger(__name__)

# Every failure path returns this as `reply` so the chat UI always has
# something to render in the bubble — the front end shows `reply`
# whether or not the response status was OK.
FALLBACK_REPLY = (
    "Sorry — I can't reach the assistant right now. Please try again in a "
    "moment. If your pet needs urgent help, contact a vet directly."
)

# Long enough for a detailed question, short enough that a runaway paste
# doesn't turn into a huge Gemini prompt.
MAX_MESSAGE_LENGTH = 2000


def _extract_reply(payload):
    """
    Pull the assistant's text out of whatever n8n sends back.

    The workflow's last node ("Edit Fields") emits {"text": ...}, but the
    shape depends on which node ends up last — an AI Agent on its own
    responds with {"output": ...}. Accepting either means reordering the
    workflow in n8n doesn't silently break the chat.
    """
    if isinstance(payload, list):
        payload = payload[0] if payload else {}
    if not isinstance(payload, dict):
        return ""

    for key in ("text", "output", "reply", "message"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


@login_required(login_url="core:pet_owner_login")
@require_POST
def chat_message_view(request):
    """POST {"message": "..."} -> {"reply": "..."}"""
    try:
        body = json.loads(request.body or b"{}")
    except ValueError:
        return JsonResponse({"reply": "Sorry, I didn't catch that."}, status=400)

    message = (body.get("message") or "").strip()
    if not message:
        return JsonResponse({"reply": "Please type a message first."}, status=400)
    message = message[:MAX_MESSAGE_LENGTH]

    webhook_url = settings.N8N_CHATBOT_WEBHOOK_URL
    if not webhook_url:
        logger.warning(
            "N8N_CHATBOT_WEBHOOK_URL is not set — the chatbot cannot reach the "
            "RAG workflow. See rag/README.md for the setup steps."
        )
        return JsonResponse(
            {"reply": FALLBACK_REPLY, "error": "not_configured"}, status=503
        )

    # n8n's Simple Memory node keys conversation history off sessionId, so
    # this is what makes follow-up questions ("and how much of it?") work.
    # The Django session key scopes that history to one browser session:
    # logging out or a new browser starts a clean conversation, which also
    # stops one user's history leaking into another's on a shared device.
    if not request.session.session_key:
        request.session.save()
    session_id = f"petcentre-{request.session.session_key}"

    try:
        response = requests.post(
            webhook_url,
            json={
                # The three fields n8n's own chat widget posts to a Chat
                # Trigger — matching them means the trigger needs no
                # special configuration beyond being made public.
                "action": "sendMessage",
                "sessionId": session_id,
                "chatInput": message,
            },
            timeout=settings.N8N_CHATBOT_TIMEOUT,
        )
        response.raise_for_status()
        payload = response.json()
    except (requests.RequestException, ValueError):
        logger.exception("Call to the n8n chatbot webhook failed")
        return JsonResponse(
            {"reply": FALLBACK_REPLY, "error": "upstream_unavailable"}, status=502
        )

    reply = _extract_reply(payload)
    if not reply:
        logger.warning("n8n chatbot returned no usable text: %r", payload)
        return JsonResponse(
            {"reply": FALLBACK_REPLY, "error": "empty_response"}, status=502
        )

    return JsonResponse({"reply": reply})
