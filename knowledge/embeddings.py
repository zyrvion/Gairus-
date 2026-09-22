class EmbeddingEngine:
    def embed(self, text):
        return {
            "text": text,
            "status": "embedding_adapter_ready",
        }
