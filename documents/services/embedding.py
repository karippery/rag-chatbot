import numpy as np

from transformers import AutoTokenizer
from optimum.onnxruntime import ORTModelForFeatureExtraction

class EmbeddingService:

    MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"

    _tokenizer = None
    _model = None


    def load(self):

        if self._model is None:

            self._tokenizer = AutoTokenizer.from_pretrained(
                self.MODEL_NAME
            )

            self._model = ORTModelForFeatureExtraction.from_pretrained(
                self.MODEL_NAME,
                export=True,  # converts to ONNX automatically
                provider="CPUExecutionProvider"
            )

        return self._tokenizer, self._model


    def mean_pooling(self, token_embeddings, attention_mask):

        mask = np.expand_dims(attention_mask, axis=-1)

        summed = np.sum(token_embeddings * mask, axis=1)

        counts = np.clip(mask.sum(axis=1), a_min=1e-9, a_max=None)

        return summed / counts


    def normalize(self, embeddings):

        norm = np.linalg.norm(embeddings, axis=1, keepdims=True)

        return embeddings / norm


    def embed_text(self, text):

        return self.embed_batch([text])[0]


    def embed_batch(self, texts):

        if not texts:
            return []

        tokenizer, model = self.load()

        inputs = tokenizer(
            texts,
            padding=True,
            truncation=True,
            return_tensors="np"
        )

        outputs = model(**inputs)

        token_embeddings = outputs.last_hidden_state

        embeddings = self.mean_pooling(
            token_embeddings,
            inputs["attention_mask"]
        )

        embeddings = self.normalize(embeddings)

        return embeddings.tolist()


embedding_service = EmbeddingService()
