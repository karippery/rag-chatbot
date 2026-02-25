"""

Sentence-embedding service backed by ``sentence-transformers/all-MiniLM-L6-v2``
running via ONNX Runtime for fast CPU inference.

Lazy-loading strategy
---------------------
The model is **not** loaded at import time.  The first call to
``embed_text()`` or ``embed_batch()`` triggers ``load()``, which either:

1. Loads from a local ONNX cache (fast, no re-conversion), or
2. Converts the HuggingFace model to ONNX, saves it to the cache dir, and
   loads it (slow first run, fast thereafter).

This keeps Django start-up time short and avoids OOM errors in containers
where the model is not needed (e.g. management command containers).

Thread safety
-------------
``load()`` uses a simple ``_model is not None`` guard.  In multi-threaded
environments (Gunicorn with threads) two threads may race through the check
and both attempt to load the model.  This is safe: the second write is a
no-op overwrite with the same object.  Use ``threading.Lock`` if you need
strict single-init semantics.
"""

import logging
import os
from typing import List

import numpy as np
from django.conf import settings
from optimum.onnxruntime import ORTModelForFeatureExtraction
from transformers import AutoTokenizer

logger = logging.getLogger(__name__)


class EmbeddingService:
    """
    Generate dense sentence embeddings using a quantised ONNX model.

    Configuration is loaded from Django settings:
    - EMBEDDING_MODEL_NAME: HuggingFace model identifier
    - EMBEDDING_ONNX_CACHE_DIR: Local directory for cached ONNX model
    - EMBEDDING_ONNX_PROVIDER: ONNX Runtime execution provider
    """

    # Configuration from settings.py
    MODEL_NAME = settings.EMBEDDING_MODEL_NAME
    ONNX_CACHE_DIR = settings.EMBEDDING_ONNX_CACHE_DIR
    ONNX_PROVIDER = settings.EMBEDDING_ONNX_PROVIDER

    _tokenizer = None
    _model = None

    # ──────────────────────────────────────────────────────────────────────────
    # Model lifecycle
    # ──────────────────────────────────────────────────────────────────────────

    def load(self):
        """
        Lazily load (or convert-then-load) the ONNX model.

        On the first call the model files are either read from
        ``ONNX_CACHE_DIR`` (if ``model.onnx`` is present) or exported from
        HuggingFace and persisted to that directory.  Subsequent calls are
        instant because ``_model is not None``.

        Returns:
            Tuple of ``(tokenizer, model)``.

        Raises:
            OSError:      If the cache directory cannot be created.
            Exception:    Propagated from ``transformers`` / ``optimum`` on
                          download or conversion failure.
        """
        if self._model is not None:
            return self._tokenizer, self._model

        onnx_model_path = os.path.join(self.ONNX_CACHE_DIR, "model.onnx")
        already_exported = os.path.exists(onnx_model_path)

        if already_exported:
            logger.info(
                "Loading ONNX model from local cache.",
                extra={
                    "cache_dir": self.ONNX_CACHE_DIR,
                    "provider": self.ONNX_PROVIDER,
                },
            )
            self._tokenizer = AutoTokenizer.from_pretrained(self.ONNX_CACHE_DIR)
            self._model = ORTModelForFeatureExtraction.from_pretrained(
                self.ONNX_CACHE_DIR,
                provider=self.ONNX_PROVIDER,
            )
        else:
            logger.info(
                "ONNX model not found — exporting from HuggingFace Hub. "
                "This may take a few minutes on first run.",
                extra={
                    "model_name": self.MODEL_NAME,
                    "cache_dir": self.ONNX_CACHE_DIR,
                    "provider": self.ONNX_PROVIDER,
                },
            )
            os.makedirs(self.ONNX_CACHE_DIR, exist_ok=True)
            self._tokenizer = AutoTokenizer.from_pretrained(self.MODEL_NAME)
            self._model = ORTModelForFeatureExtraction.from_pretrained(
                self.MODEL_NAME,
                export=True,
                provider=self.ONNX_PROVIDER,
            )
            self._model.save_pretrained(self.ONNX_CACHE_DIR)
            self._tokenizer.save_pretrained(self.ONNX_CACHE_DIR)
            logger.info(
                "ONNX model exported and cached.",
                extra={"cache_dir": self.ONNX_CACHE_DIR},
            )

        return self._tokenizer, self._model

    # ──────────────────────────────────────────────────────────────────────────
    # Embedding helpers
    # ──────────────────────────────────────────────────────────────────────────

    def mean_pooling(
        self,
        token_embeddings: np.ndarray,
        attention_mask: np.ndarray,
    ) -> np.ndarray:
        """
        Pool token embeddings into a single sentence embedding by averaging
        over non-padding tokens.

        Args:
            token_embeddings: Shape ``(batch, seq_len, hidden_size)``.
            attention_mask:   Shape ``(batch, seq_len)``; 1 for real tokens,
                              0 for padding.

        Returns:
            Mean-pooled embeddings, shape ``(batch, hidden_size)``.
        """
        mask = np.expand_dims(attention_mask, axis=-1)            # (B, L, 1)
        summed = np.sum(token_embeddings * mask, axis=1)           # (B, H)
        token_counts = np.clip(mask.sum(axis=1), a_min=1e-9, a_max=None)  # (B, 1)
        return summed / token_counts

    def normalize(self, embeddings: np.ndarray) -> np.ndarray:
        """
        L2-normalise a batch of embeddings so cosine similarity equals dot product.

        Args:
            embeddings: Shape ``(batch, hidden_size)``.

        Returns:
            Unit-norm embeddings of the same shape.
        """
        norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
        # Avoid division by zero for zero vectors (shouldn't happen with real text).
        norms = np.where(norms == 0, 1.0, norms)
        return embeddings / norms

    # ──────────────────────────────────────────────────────────────────────────
    # Public embedding API
    # ──────────────────────────────────────────────────────────────────────────

    def embed_text(self, text: str) -> List[float]:
        """
        Embed a single text string.

        Convenience wrapper around ``embed_batch``.

        Args:
            text: The input string.

        Returns:
            A list of floats representing the embedding vector.

        Raises:
            ValueError: If ``text`` is empty.
        """
        if not text or not text.strip():
            raise ValueError("embed_text received an empty string.")
        return self.embed_batch([text])[0]

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Embed a list of strings in a single forward pass.

        All strings are tokenised together (with padding/truncation) so the
        batch is processed efficiently by ONNX Runtime.

        Args:
            texts: A non-empty list of input strings.  Empty strings are
                   allowed within the list but will produce near-zero vectors.

        Returns:
            A list of embedding vectors (each a ``List[float]``), one per
            input string, in the same order.

        Raises:
            ValueError: If ``texts`` is empty.
            Exception:  Propagated from the model on inference failure.
        """
        if not texts:
            logger.warning("embed_batch called with empty list — returning [].")
            return []

        logger.debug(
            "Embedding batch.",
            extra={
                "batch_size": len(texts),
                "model_name": self.MODEL_NAME,
            },
        )

        tokenizer, model = self.load()

        inputs = tokenizer(
            texts,
            padding=True,
            truncation=True,
            return_tensors="np",
        )

        try:
            outputs = model(**inputs)
        except Exception as exc:
            logger.error(
                "ONNX model inference failed.",
                extra={
                    "batch_size": len(texts),
                    "model_name": self.MODEL_NAME,
                },
                exc_info=True,
            )
            raise

        embeddings = self.mean_pooling(outputs.last_hidden_state, inputs["attention_mask"])
        embeddings = self.normalize(embeddings)

        logger.debug(
            "Batch embedded successfully.",
            extra={
                "batch_size": len(texts),
                "embedding_dim": embeddings.shape[1],
                "model_name": self.MODEL_NAME,
            },
        )
        return embeddings.tolist()


# Module-level singleton — import and call directly.
embedding_service = EmbeddingService()