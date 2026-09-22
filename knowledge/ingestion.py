from pathlib import Path


class Ingestion:
    def load_text(self, path):
        return Path(path).read_text(encoding="utf-8")

    def chunk(self, text, size=1000):
        return [
            text[i:i + size]
            for i in range(0, len(text), size)
        ]
