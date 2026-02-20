import os
import numpy as np
from transformers import AutoTokenizer
from optimum.onnxruntime import ORTModelForFeatureExtraction

class EmbeddingService:

    MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
    # Cache the converted ONNX model locally so it's not re-converted on every restart
    ONNX_CACHE_DIR = "/app/models/onnx/all-MiniLM-L6-v2"

    _tokenizer = None
    _model = None

    def load(self):
        if self._model is not None:
            return self._tokenizer, self._model

        already_exported = os.path.exists(
            os.path.join(self.ONNX_CACHE_DIR, "model.onnx")
        )

        if already_exported:
            # Load from local ONNX cache — no re-conversion
            self._tokenizer = AutoTokenizer.from_pretrained(self.ONNX_CACHE_DIR)
            self._model = ORTModelForFeatureExtraction.from_pretrained(
                self.ONNX_CACHE_DIR,
                provider="CPUExecutionProvider",
            )
        else:
            # First run: convert and save so future startups are fast
            os.makedirs(self.ONNX_CACHE_DIR, exist_ok=True)
            self._tokenizer = AutoTokenizer.from_pretrained(self.MODEL_NAME)
            self._model = ORTModelForFeatureExtraction.from_pretrained(
                self.MODEL_NAME,
                export=True,
                provider="CPUExecutionProvider",
            )
            self._model.save_pretrained(self.ONNX_CACHE_DIR)
            self._tokenizer.save_pretrained(self.ONNX_CACHE_DIR)

        return self._tokenizer, self._model

    def mean_pooling(self, token_embeddings, attention_mask):
        mask = np.expand_dims(attention_mask, axis=-1)
        summed = np.sum(token_embeddings * mask, axis=1)
        counts = np.clip(mask.sum(axis=1), a_min=1e-9, a_max=None)
        return summed / counts

    def normalize(self, embeddings):
        norm = np.linalg.norm(embeddings, axis=1, keepdims=True)
        return embeddings / norm

    def embed_text(self, text: str):
        return self.embed_batch([text])[0]

    def embed_batch(self, texts: list):
        if not texts:
            return []

        tokenizer, model = self.load()

        inputs = tokenizer(
            texts,
            padding=True,
            truncation=True,
            return_tensors="np",
        )

        outputs = model(**inputs)
        embeddings = self.mean_pooling(outputs.last_hidden_state, inputs["attention_mask"])
        embeddings = self.normalize(embeddings)
        return embeddings.tolist()


embedding_service = EmbeddingService()