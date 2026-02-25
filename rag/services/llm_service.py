"""
Manages loading, inference, and unloading of local Qwen causal-language models.

Model registry
--------------
Models are configured in settings.py RESPONSE_MODE_MODELS.

Models are kept in three parallel class-level registries (tokenizer, model,
pipeline) and lazily loaded on first use.  Call ``load_all_models()`` at
Django app startup (e.g. in ``AppConfig.ready()``) to pay the cold-start cost
once rather than on the first user request.

Fallback strategy
-----------------
``generate_answer`` never raises.  If the LLM is unavailable or inference
fails, it falls back to a simple extractive heuristic that returns the first
few sentences of the retrieved context.  The returned ``bool`` flag tells the
caller which path was taken (``True`` = LLM, ``False`` = extractive).

Thread safety
-------------
The ``_model is not None`` guard in ``load_model`` is not atomically safe
under concurrent Django workers.  In multi-threaded environments two threads
may race through the check and both attempt to download/load the model.  The
outcome is harmless (the second write overwrites the first with an identical
object) but wastes memory during the race window.  Add a ``threading.Lock``
per model key if strict single-init is required.
"""

import logging
import time
from typing import Optional, Tuple

import torch
from django.conf import settings
from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline

logger = logging.getLogger(__name__)


class LLMService:
    """
    Registry-backed service for local causal-LM inference.

    Class-level registries are shared across all instances, so a single set
    of loaded models is reused regardless of how many times the service is
    instantiated.  In practice a module-level singleton (``llm_service``) is
    the only instance.
    """

    # Initialize registries from settings
    MODEL_REGISTRY = {model: None for model in settings.RESPONSE_MODE_MODELS.values()}
    TOKENIZER_REGISTRY = {model: None for model in settings.RESPONSE_MODE_MODELS.values()}
    PIPELINE_REGISTRY = {model: None for model in settings.RESPONSE_MODE_MODELS.values()}

    DEFAULT_MODEL = settings.LLM_DEFAULT_MODEL

    # Inference parameters from settings
    INFERENCE_PARAMS = settings.LLM_INFERENCE_PARAMS

    # ──────────────────────────────────────────────────────────────────────────
    # Model lifecycle
    # ──────────────────────────────────────────────────────────────────────────

    def load_model(self, model_name: Optional[str] = None) -> bool:
        """
        Load a single model into the in-process registry.

        Idempotent: returns immediately if the model is already loaded.
        Falls back to ``DEFAULT_MODEL`` if an unknown name is requested.

        Args:
            model_name: HuggingFace model identifier. ``None`` uses
                        ``DEFAULT_MODEL``.

        Returns:
            ``True`` if the model is loaded (either already was or just loaded).
            ``False`` if loading failed for any reason (exception is logged
            but not re-raised so callers can degrade gracefully).
        """
        model_name = model_name or self.DEFAULT_MODEL

        if model_name not in self.MODEL_REGISTRY:
            logger.warning(
                "Unknown model requested — falling back to default.",
                extra={"requested_model": model_name, "default_model": self.DEFAULT_MODEL},
            )
            model_name = self.DEFAULT_MODEL

        if self.PIPELINE_REGISTRY.get(model_name) is not None:
            logger.debug("Model already loaded.", extra={"model_name": model_name})
            return True

        logger.info("Loading LLM model.", extra={"model_name": model_name})
        start_time = time.time()

        try:
            tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
            if tokenizer.pad_token is None:
                tokenizer.pad_token = tokenizer.eos_token
                logger.debug(
                    "pad_token was None — set to eos_token.",
                    extra={"model_name": model_name},
                )

            use_gpu = torch.cuda.is_available()
            device_label = "GPU" if use_gpu else "CPU"
            logger.debug(
                "Loading model weights.",
                extra={"model_name": model_name, "device": device_label},
            )

            model = AutoModelForCausalLM.from_pretrained(
                model_name,
                torch_dtype=torch.float16 if use_gpu else torch.float32,
                device_map="auto" if use_gpu else None,
                trust_remote_code=True,
                low_cpu_mem_usage=True,
            )

            if not use_gpu:
                model = model.to("cpu")

            pipe = pipeline(
                "text-generation",
                model=model,
                tokenizer=tokenizer,
                device=0 if use_gpu else -1,
                max_new_tokens=self.INFERENCE_PARAMS["max_new_tokens"],
                temperature=self.INFERENCE_PARAMS["temperature"],
                top_p=self.INFERENCE_PARAMS["top_p"],
                do_sample=self.INFERENCE_PARAMS["do_sample"],
                repetition_penalty=self.INFERENCE_PARAMS["repetition_penalty"],
                pad_token_id=tokenizer.eos_token_id,
            )

            self.TOKENIZER_REGISTRY[model_name] = tokenizer
            self.MODEL_REGISTRY[model_name] = model
            self.PIPELINE_REGISTRY[model_name] = pipe

            elapsed = time.time() - start_time
            logger.info(
                "Model loaded successfully.",
                extra={
                    "model_name": model_name,
                    "device": device_label,
                    "load_time_seconds": round(elapsed, 2),
                },
            )
            return True

        except Exception as exc:
            elapsed = time.time() - start_time
            logger.error(
                "Failed to load model.",
                extra={
                    "model_name": model_name,
                    "error": str(exc),
                    "elapsed_seconds": round(elapsed, 2),
                },
                exc_info=True,
            )
            return False

    def load_all_models(self) -> None:
        """
        Preload every registered model.

        Call this from ``AppConfig.ready()`` so the cold-start cost is paid
        once at process startup rather than on the first user request.
        """
        logger.info(
            "Preloading all LLM models.",
            extra={"models": list(self.MODEL_REGISTRY.keys())},
        )
        for model_name in self.MODEL_REGISTRY:
            self.load_model(model_name)

    def is_available(self, model_name: Optional[str] = None) -> bool:
        """
        Check whether a model is ready for inference, loading it if needed.

        Args:
            model_name: Model to check. ``None`` uses ``DEFAULT_MODEL``.

        Returns:
            ``True`` if the model is loaded and ready. ``False`` if it is not
            loaded and the load attempt failed.
        """
        model_name = model_name or self.DEFAULT_MODEL
        if self.PIPELINE_REGISTRY.get(model_name) is not None:
            return True
        logger.debug(
            "Model not loaded — attempting lazy load.",
            extra={"model_name": model_name},
        )
        return self.load_model(model_name)

    def unload_model(self, model_name: str) -> None:
        """
        Remove a model from memory and free GPU cache if applicable.

        Safe to call for an already-unloaded model (no-op).

        Args:
            model_name: Registry key of the model to unload.
        """
        if model_name not in self.PIPELINE_REGISTRY:
            logger.debug(
                "unload_model called for unknown model — ignoring.",
                extra={"model_name": model_name},
            )
            return

        if self.PIPELINE_REGISTRY[model_name] is None:
            logger.debug(
                "Model already unloaded — nothing to do.",
                extra={"model_name": model_name},
            )
            return

        try:
            # Delete references so the GC can collect them.
            del self.PIPELINE_REGISTRY[model_name]
            del self.MODEL_REGISTRY[model_name]
            del self.TOKENIZER_REGISTRY[model_name]

            # Re-insert None so the registry keys remain consistent.
            self.PIPELINE_REGISTRY[model_name] = None
            self.MODEL_REGISTRY[model_name] = None
            self.TOKENIZER_REGISTRY[model_name] = None

            if torch.cuda.is_available():
                torch.cuda.empty_cache()
                logger.debug("GPU cache cleared.", extra={"model_name": model_name})

            logger.info("Model unloaded.", extra={"model_name": model_name})

        except Exception as exc:
            logger.error(
                "Error while unloading model.",
                extra={"model_name": model_name, "error": str(exc)},
                exc_info=True,
            )

    # ──────────────────────────────────────────────────────────────────────────
    # Inference
    # ──────────────────────────────────────────────────────────────────────────

    def generate_answer(
        self,
        query: str,
        context: str,
        model_name: Optional[str] = None,
        max_tokens: Optional[int] = None,
    ) -> Tuple[str, bool]:
        """
        Generate an answer grounded in *context*.

        Tries LLM inference first; falls back to extractive summarisation if
        the model is unavailable or inference throws.

        Args:
            query:      The user's natural-language question.
            context:    Retrieved document text to ground the answer.
            model_name: Model to use. ``None`` uses ``DEFAULT_MODEL``.
            max_tokens: Maximum new tokens to generate (LLM path only).
                        Falls back to settings value if not provided.

        Returns:
            A ``(answer, used_llm)`` tuple where ``used_llm`` is ``True`` when
            the LLM produced the answer and ``False`` when the extractive
            fallback was used.
        """
        model_name = model_name or self.DEFAULT_MODEL
        max_tokens = max_tokens or self.INFERENCE_PARAMS["max_new_tokens"]

        if self.is_available(model_name):
            logger.debug(
                "Attempting LLM generation.",
                extra={"model_name": model_name, "max_tokens": max_tokens},
            )
            try:
                return self._generate_with_llm(query, context, model_name, max_tokens)
            except Exception as exc:
                logger.warning(
                    "LLM generation failed — falling back to extractive.",
                    extra={"model_name": model_name, "error": str(exc)},
                    exc_info=True,
                )
        else:
            logger.warning(
                "LLM unavailable — using extractive fallback.",
                extra={"model_name": model_name},
            )

        return self._generate_extractive(query, context), False

    def _generate_with_llm(
        self,
        query: str,
        context: str,
        model_name: str,
        max_tokens: int,
    ) -> Tuple[str, bool]:
        """
        Run inference through the loaded pipeline.

        Args:
            query:      User question.
            context:    Retrieved context text.
            model_name: Registry key of the loaded model.
            max_tokens: Maximum new tokens.

        Returns:
            ``(answer_text, True)``

        Raises:
            ValueError: If the model returns an empty or malformed response.
            Exception:  Propagated from the HuggingFace pipeline on failure.
        """
        tokenizer = self.TOKENIZER_REGISTRY[model_name]
        pipe = self.PIPELINE_REGISTRY[model_name]

        prompt = self._build_prompt(query, context, tokenizer)
        start_time = time.time()

        result = pipe(
            prompt,
            max_new_tokens=max_tokens,
            temperature=self.INFERENCE_PARAMS["temperature"],
            top_p=self.INFERENCE_PARAMS["top_p"],
            do_sample=self.INFERENCE_PARAMS["do_sample"],
            repetition_penalty=self.INFERENCE_PARAMS["repetition_penalty"],
            pad_token_id=tokenizer.eos_token_id,
        )

        if not result or "generated_text" not in result[0]:
            raise ValueError(
                f"Model '{model_name}' returned an empty or malformed response. "
                f"raw result: {result!r}"
            )

        full_text = result[0]["generated_text"]
        answer = full_text[len(prompt):].strip()

        if not answer:
            raise ValueError(
                f"Model '{model_name}' produced an empty answer after stripping the prompt."
            )

        elapsed = time.time() - start_time
        logger.info(
            "LLM answer generated.",
            extra={
                "model_name": model_name,
                "generation_time_seconds": round(elapsed, 2),
                "answer_tokens": len(answer.split()),
            },
        )
        return answer, True

    def _generate_extractive(self, query: str, context: str) -> str:
        """
        Extractive fallback: return the first three sentences of *context*.

        Used when the LLM is unavailable or fails.  No model inference is
        performed.

        Args:
            query:   The original user question (unused, kept for call-site
                     symmetry with ``_generate_with_llm``).
            context: Retrieved document text.

        Returns:
            A string containing up to three sentences from *context*, or a
            "no information found" message when *context* is empty.
        """
        if not context.strip():
            logger.debug("Extractive fallback: context is empty.")
            return "No relevant information found in the document database."

        sentences = [s.strip() for s in context.replace("\n", " ").split(".") if s.strip()]
        if not sentences:
            return "No relevant information found in the document database."

        answer = ". ".join(sentences[:3]) + "."
        logger.debug(
            "Extractive fallback answer produced.",
            extra={"sentences_used": min(3, len(sentences)), "total_sentences": len(sentences)},
        )
        return answer

    def _build_prompt(self, query: str, context: str, tokenizer) -> str:
        """
        Format the query and context into a chat-template prompt string.

        The system prompt is intentionally strict: it instructs the model to
        answer ONLY from the provided context and to explicitly deny claims
        that are not supported — critical for small models that tend to
        hallucinate rather than refuse.

        Args:
            query:     The user's question.
            context:   Retrieved document text.
            tokenizer: The loaded tokenizer for the target model.

        Returns:
            A formatted prompt string ready for the pipeline.
        """
        messages = [
            {
                "role": "system",
                "content": (
                    "You are a precise assistant that answers questions ONLY using "
                    "the context provided below. Rules you must follow:\n"
                    "1. If the context does NOT mention something, you MUST say it is "
                    "not mentioned — never guess or assume.\n"
                    "2. If asked whether someone has a skill or experience that does "
                    "NOT appear in the context, answer: 'No, it is not mentioned in "
                    "the provided documents.'\n"
                    "3. Never add information from your own knowledge.\n"
                    "4. Be concise and factual."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Context:\n{context}\n\n"
                    f"Question: {query}\n\n"
                    "Answer based strictly on the context above. "
                    "If the information is not in the context, say so explicitly."
                ),
            },
        ]
        return tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True,
        )


# Module-level singleton — import and call directly.
llm_service = LLMService()