"""
Retrieval-augmented Q&A for the PetPal chatbot widget — embeds the
user's question via Gemini, finds the closest KnowledgeChunk rows in
this same Postgres database by cosine distance (pgvector), and asks
Gemini to answer using only that retrieved context.

No separate vector database or workflow host: everything runs inside
this Django process against the database already in use for the rest
of the app.
"""
import time

from django.conf import settings
from google import genai
from google.genai import errors, types
from pgvector.django import CosineDistance

from core.models import KnowledgeChunk

# Gemini's free tier routinely returns 503 ("high demand") or 429 (rate
# limit) for a request that succeeds a moment later on retry — observed
# directly while testing this exact key. Worth one short retry before
# giving up and showing the user a failure message.
RETRYABLE_STATUS_CODES = (429, 503)
MAX_RETRIES = 2
RETRY_DELAY_SECONDS = 2

# Must match KnowledgeChunk.embedding's dimensions exactly — pgvector
# enforces a fixed size per column, so changing this without a matching
# migration + full re-ingest breaks retrieval.
EMBEDDING_MODEL = "gemini-embedding-001"
EMBEDDING_DIMENSIONS = 768
GENERATION_MODEL = "gemini-flash-latest"

TOP_N_CHUNKS = 3

NOT_CONFIGURED_REPLY = (
    "Sorry — I can't reach the assistant right now. Please try again in a "
    "moment. If your pet needs urgent help, contact a vet directly."
)
NO_CONTEXT_REPLY = (
    "I'm not sure about that — I'd recommend checking with one of our "
    "veterinarians."
)

SYSTEM_PROMPT = """You are "PetPal", the virtual assistant for Pet Centre — an online platform that connects pet owners with veterinary services, appointments, medicines, and pet-care guidance.

## Your Persona
- You are warm, friendly, and empathetic — pet owners are often worried about their animals, so always acknowledge their concern before answering.
- You speak in simple, clear language. Avoid heavy medical jargon; when a technical term is necessary, explain it in one short sentence.
- You are professional but approachable, like a helpful front-desk assistant at a veterinary clinic.
- Keep answers concise: 2-5 sentences for simple questions, short bullet points for lists or steps.

## Your Knowledge & the Retrieved Context
- You answer questions using ONLY the information retrieved from the Pet Centre knowledge base (the context provided below).
- If the context contains the answer, use it and summarize it naturally — do not copy text word-for-word, and do not mention "documents", "context", or "knowledge base" to the user.
- If the context does NOT contain the answer, say honestly that you're not sure and recommend checking with a veterinarian. Never invent facts, prices, medicines, dosages, or appointment details.

## Safety Rules
- You are NOT a veterinarian and must never diagnose conditions or prescribe medicines or dosages.
- If a user describes symptoms that sound urgent (difficulty breathing, seizures, poisoning, severe bleeding, collapse), immediately advise them to contact a veterinarian or emergency animal clinic right away — before anything else.
- For any medical question, end with a gentle reminder to consult a registered veterinarian for a proper diagnosis.
- Politely refuse questions unrelated to pets or Pet Centre and steer the conversation back to what you can help with.
"""

_client = None


def _get_client():
    global _client
    if _client is None:
        _client = genai.Client(api_key=settings.GEMINI_API_KEY)
    return _client


def _with_retry(call):
    """Retries `call` on Gemini's transient 429/503 responses — anything
    else (bad API key, invalid model, etc.) is a real failure and
    shouldn't be retried."""
    for attempt in range(MAX_RETRIES + 1):
        try:
            return call()
        except errors.APIError as exc:
            if exc.code not in RETRYABLE_STATUS_CODES or attempt == MAX_RETRIES:
                raise
            time.sleep(RETRY_DELAY_SECONDS)


def embed_text(text, task_type):
    """task_type is 'RETRIEVAL_DOCUMENT' at ingest time, 'RETRIEVAL_QUERY' at query time — gemini-embedding-001 optimizes the vector differently for each."""
    result = _with_retry(lambda: _get_client().models.embed_content(
        model=EMBEDDING_MODEL,
        contents=text,
        config=types.EmbedContentConfig(
            output_dimensionality=EMBEDDING_DIMENSIONS,
            task_type=task_type,
        ),
    ))
    return result.embeddings[0].values


def answer_question(question):
    if not settings.GEMINI_API_KEY:
        return NOT_CONFIGURED_REPLY

    query_embedding = embed_text(question, task_type="RETRIEVAL_QUERY")
    chunks = list(
        KnowledgeChunk.objects
        .annotate(distance=CosineDistance("embedding", query_embedding))
        .order_by("distance")[:TOP_N_CHUNKS]
    )
    if not chunks:
        return NO_CONTEXT_REPLY

    context = "\n\n".join(chunk.content for chunk in chunks)
    prompt = f"{SYSTEM_PROMPT}\n\nContext:\n{context}\n\nUser question:\n{question}"

    response = _with_retry(lambda: _get_client().models.generate_content(model=GENERATION_MODEL, contents=prompt))
    return response.text
