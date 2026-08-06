from django.db import models
from pgvector.django import VectorField


class KnowledgeChunk(models.Model):
    """
    A chunk of the pet-care knowledge base, embedded via Gemini
    (gemini-embedding-001) and retrieved by cosine similarity to answer
    chatbot questions — see core/rag.py. 768 dimensions matches the
    output_dimensionality requested at ingest time in
    core.management.commands.ingest_knowledge; the two must stay in
    sync, since pgvector enforces a fixed dimension per column.
    """
    title = models.CharField(max_length=255)
    content = models.TextField()
    embedding = VectorField(dimensions=768)
    source = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title
