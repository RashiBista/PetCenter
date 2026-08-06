import re
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from core.models import KnowledgeChunk
from core.rag import embed_text

# Within the 500-1000 char/chunk range that keeps each chunk focused
# enough for retrieval to pull in relevant-not-noisy context, without
# fragmenting related sentences across chunk boundaries.
CHUNK_TARGET_SIZE = 800


class Command(BaseCommand):
    help = (
        "Chunk a pet-care knowledge document, embed each chunk via Gemini, "
        "and store it for the RAG chatbot (see core/rag.py). Safe to "
        "re-run after editing the document — replaces any existing "
        "chunks from the same source first."
    )

    def add_arguments(self, parser):
        parser.add_argument('path', help='Path to a plain-text document to ingest.')
        parser.add_argument(
            '--source',
            help="Label stored on each chunk (defaults to the filename). "
                 "Re-running with the same source replaces its existing chunks.",
        )

    def handle(self, *args, **options):
        path = Path(options['path'])
        if not path.is_file():
            raise CommandError(f"No such file: {path}")

        text = path.read_text(encoding='utf-8')
        source = options['source'] or path.name
        chunks = self._chunk_text(text)
        if not chunks:
            raise CommandError("Document produced no chunks — is it empty?")

        deleted, _ = KnowledgeChunk.objects.filter(source=source).delete()
        if deleted:
            self.stdout.write(f"Removed {deleted} existing chunk(s) for source '{source}'.")

        for i, chunk_text in enumerate(chunks, start=1):
            embedding = embed_text(chunk_text, task_type='RETRIEVAL_DOCUMENT')
            KnowledgeChunk.objects.create(
                title=f"{source} — part {i}",
                content=chunk_text,
                embedding=embedding,
                source=source,
            )
            self.stdout.write(f"  Ingested chunk {i}/{len(chunks)} ({len(chunk_text)} chars)")

        self.stdout.write(self.style.SUCCESS(f"Ingested {len(chunks)} chunk(s) from {path.name}."))

    def _chunk_text(self, text):
        """
        Splits on blank-line-separated paragraphs, merging consecutive
        short paragraphs up to CHUNK_TARGET_SIZE so related sentences
        stay together, and falling back to a sentence-level split for
        any single paragraph too long to fit in one chunk on its own.
        """
        paragraphs = [p.strip() for p in re.split(r'\n\s*\n', text) if p.strip()]
        chunks = []
        current = ''
        for para in paragraphs:
            if len(para) > CHUNK_TARGET_SIZE:
                if current:
                    chunks.append(current)
                    current = ''
                chunks.extend(self._split_long_paragraph(para))
                continue

            if current and len(current) + len(para) + 2 > CHUNK_TARGET_SIZE:
                chunks.append(current)
                current = para
            else:
                current = f"{current}\n\n{para}".strip()

        if current:
            chunks.append(current)
        return chunks

    def _split_long_paragraph(self, paragraph):
        sentences = re.split(r'(?<=[.!?])\s+', paragraph)
        pieces = []
        piece = ''
        for sentence in sentences:
            if piece and len(piece) + len(sentence) + 1 > CHUNK_TARGET_SIZE:
                pieces.append(piece)
                piece = sentence
            else:
                piece = f"{piece} {sentence}".strip()
        if piece:
            pieces.append(piece)
        return pieces
