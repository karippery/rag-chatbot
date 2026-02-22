"""

Character-based text chunking with overlap for RAG pipelines.

Design notes
------------
* Chunking is done on raw characters rather than tokens.  This keeps the
  service dependency-free (no tokeniser required) while still producing
  reasonably uniform chunks for most embedding models.
* ``chunk_overlap`` creates a sliding window so each chunk shares context
  with its neighbours, reducing the chance that a relevant sentence is split
  across a chunk boundary.
* Text is lightly normalised before chunking: consecutive whitespace is
  collapsed to a single space, which prevents huge empty chunks from
  documents that contain many blank lines.
  
"""

import logging
import re
from typing import List

from django.conf import settings

logger = logging.getLogger(__name__)


class ChunkingService:
    """
    Split a long string into overlapping fixed-size character chunks.

    Args:
        chunk_size:    Maximum character count for each chunk.
                       Defaults to ``settings.CHUNK_SIZE``.
        chunk_overlap: Number of characters to repeat from the end of the
                       previous chunk at the start of the next one.
                       Must be strictly less than ``chunk_size``.
                       Defaults to ``settings.CHUNK_OVERLAP``.

    Raises:
        ValueError: If ``chunk_overlap >= chunk_size``.
    """

    def __init__(self, chunk_size: int = None, chunk_overlap: int = None) -> None:
        self.chunk_size = chunk_size or settings.CHUNK_SIZE
        self.chunk_overlap = chunk_overlap or settings.CHUNK_OVERLAP

        if self.chunk_overlap >= self.chunk_size:
            raise ValueError(
                f"chunk_overlap ({self.chunk_overlap}) must be smaller than "
                f"chunk_size ({self.chunk_size})."
            )

        logger.debug(
            "ChunkingService initialised.",
            extra={"chunk_size": self.chunk_size, "chunk_overlap": self.chunk_overlap},
        )

    # ──────────────────────────────────────────────────────────────────────────
    # Public API
    # ──────────────────────────────────────────────────────────────────────────

    def chunk_text(self, text: str) -> List[str]:
        """
        Split *text* into overlapping chunks.

        Empty or whitespace-only input returns an empty list without raising.

        Args:
            text: The full document text to be chunked.

        Returns:
            A list of non-empty chunk strings.  Each chunk is stripped of
            leading/trailing whitespace.  The list is empty when *text* is
            blank.
        """
        if not text or not text.strip():
            logger.debug("chunk_text received empty input — returning [].")
            return []

        text = self._clean_text(text)
        text_length = len(text)
        stride = self.chunk_size - self.chunk_overlap

        chunks: List[str] = []
        start = 0

        while start < text_length:
            end = start + self.chunk_size
            chunk = text[start:end].strip()
            if chunk:  # Skip chunks that are pure whitespace after stripping
                chunks.append(chunk)
            start += stride  # Advance by stride (chunk_size - overlap)

        logger.debug(
            "Text chunked.",
            extra={
                "input_length": text_length,
                "num_chunks": len(chunks),
                "chunk_size": self.chunk_size,
                "chunk_overlap": self.chunk_overlap,
            },
        )
        return chunks

    # ──────────────────────────────────────────────────────────────────────────
    # Private helpers
    # ──────────────────────────────────────────────────────────────────────────

    def _clean_text(self, text: str) -> str:
        """
        Normalise whitespace in *text*.

        Collapses any run of whitespace characters (spaces, tabs, newlines)
        into a single space, then strips leading/trailing whitespace.

        Args:
            text: Raw text to clean.

        Returns:
            Cleaned text string.
        """
        return re.sub(r"\s+", " ", text).strip()