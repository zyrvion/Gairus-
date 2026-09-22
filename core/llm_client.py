import json
import os
import urllib.request
import urllib.error


class LLMClient:
    def __init__(self):
        self.base_url = os.getenv(
            "GAIRUS_LLM_URL",
            "http://127.0.0.1:11434"
        ).rstrip("/")

        self.model = os.getenv(
            "GAIRUS_DEFAULT_MODEL",
            "deepseek"
        )

    def available(self):
        try:
            request = urllib.request.Request(
                f"{self.base_url}/api/tags",
                method="GET"
            )

            with urllib.request.urlopen(
                request,
                timeout=3
            ) as response:
                return response.status == 200

        except Exception:
            return False

    def models(self):
        try:
            request = urllib.request.Request(
                f"{self.base_url}/api/tags",
                method="GET"
            )

            with urllib.request.urlopen(
                request,
                timeout=5
            ) as response:
                data = json.loads(
                    response.read().decode("utf-8")
                )

            return [
                model.get("name")
                for model in data.get("models", [])
                if model.get("name")
            ]

        except Exception:
            return []

    def model_available(self, model):
        return model in self.models()

    def chat(
        self,
        messages,
        model=None,
        temperature=0.2,
        stream=False
    ):
        selected_model = model or self.model

        payload = {
            "model": selected_model,
            "messages": messages,
            "stream": stream,
            "options": {
                "temperature": temperature
            }
        }

        request = urllib.request.Request(
            f"{self.base_url}/api/chat",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json"
            },
            method="POST"
        )

        try:
            with urllib.request.urlopen(
                request,
                timeout=300
            ) as response:
                data = json.loads(
                    response.read().decode("utf-8")
                )

            return data.get("message", {}).get(
                "content",
                ""
            )

        except urllib.error.HTTPError as exc:
            body = exc.read().decode(
                "utf-8",
                errors="replace"
            )

            raise RuntimeError(
                f"LLM HTTP {exc.code}: {body}"
            ) from exc
