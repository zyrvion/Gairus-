import os
import json
import requests


class LLMClient:
    """
    Client LLM générique pour Gaïrus.

    Backends compatibles :
    - Ollama
    - OpenAI-compatible
    - LM Studio
    - llama.cpp server
    - autres serveurs exposant une API compatible
    """

    def __init__(self):
        self.provider = os.getenv("GAIRUS_LLM_PROVIDER", "auto").lower()
        self.base_url = os.getenv(
            "GAIRUS_LLM_URL",
            "http://127.0.0.1:11434"
        ).rstrip("/")

        self.api_key = os.getenv("GAIRUS_LLM_API_KEY", "")
        self.model = os.getenv(
            "GAIRUS_LLM_MODEL",
            "deepseek"
        )

        self.timeout = int(
            os.getenv("GAIRUS_LLM_TIMEOUT", "120")
        )

    def _headers(self):
        headers = {
            "Content-Type": "application/json"
        }

        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        return headers

    def _get(self, path):
        try:
            response = requests.get(
                f"{self.base_url}{path}",
                headers=self._headers(),
                timeout=5
            )

            if response.ok:
                return response.json()

        except Exception:
            pass

        return None

    def _detect_provider(self):
        if self.provider != "auto":
            return self.provider

        if "11434" in self.base_url:
            return "ollama"

        return "openai"

    def available(self):
        return bool(self.models())

    def models(self):
        provider = self._detect_provider()

        if provider == "ollama":
            data = self._get("/api/tags")

            if not data:
                return []

            models = data.get("models", [])

            return [
                item.get("name")
                for item in models
                if item.get("name")
            ]

        if provider in {"openai", "lmstudio", "llamacpp"}:
            data = self._get("/v1/models")

            if not data:
                return []

            return [
                item.get("id")
                for item in data.get("data", [])
                if item.get("id")
            ]

        return []

    def _select_model(self, requested=None):
        installed = self.models()

        requested = requested or self.model

        if requested in installed:
            return requested

        if installed:
            return installed[0]

        return requested

    def chat(
        self,
        messages,
        model=None,
        temperature=0.2,
        stream=False
    ):
        provider = self._detect_provider()
        selected_model = self._select_model(model)

        if provider == "ollama":
            payload = {
                "model": selected_model,
                "messages": messages,
                "stream": stream,
                "options": {
                    "temperature": temperature
                }
            }

            try:
                response = requests.post(
                    f"{self.base_url}/api/chat",
                    headers=self._headers(),
                    json=payload,
                    timeout=self.timeout
                )

                response.raise_for_status()

                data = response.json()

                return {
                    "status": "success",
                    "provider": "ollama",
                    "model": selected_model,
                    "content": data.get(
                        "message",
                        {}
                    ).get(
                        "content",
                        ""
                    ),
                    "raw": data
                }

            except Exception as exc:
                return {
                    "status": "error",
                    "provider": "ollama",
                    "model": selected_model,
                    "error": str(exc)
                }

        payload = {
            "model": selected_model,
            "messages": messages,
            "temperature": temperature,
            "stream": stream
        }

        try:
            response = requests.post(
                f"{self.base_url}/v1/chat/completions",
                headers=self._headers(),
                json=payload,
                timeout=self.timeout
            )

            response.raise_for_status()

            data = response.json()

            choices = data.get("choices", [])

            content = ""

            if choices:
                content = (
                    choices[0]
                    .get("message", {})
                    .get("content", "")
                )

            return {
                "status": "success",
                "provider": provider,
                "model": selected_model,
                "content": content,
                "raw": data
            }

        except Exception as exc:
            return {
                "status": "error",
                "provider": provider,
                "model": selected_model,
                "error": str(exc)
            }
