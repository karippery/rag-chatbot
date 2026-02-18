import re
from typing import List
from django.conf import settings


class ChunkingService:
    """
    Production-ready chunking service for RAG.
    Character based with proper overlap.
    """

    def __init__(self, chunk_size=None, chunk_overlap=None):

        self.chunk_size = chunk_size or settings.CHUNK_SIZE
        self.chunk_overlap = chunk_overlap or settings.CHUNK_OVERLAP
        if self.chunk_overlap >= self.chunk_size:
            raise ValueError("chunk_overlap must be smaller than chunk_size")


    def chunk_text(self, text: str) -> List[str]:

        if not text or not text.strip():
            return []

        text = self._clean_text(text)

        chunks = []

        start = 0
        text_length = len(text)

        while start < text_length:

            end = start + self.chunk_size

            chunk = text[start:end]

            chunks.append(chunk.strip())

            start = end - self.chunk_overlap

            if start < 0:
                start = 0

        return chunks


    def _clean_text(self, text: str) -> str:

        text = re.sub(r"\s+", " ", text)

        return text.strip()
