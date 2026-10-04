from providers import (
    PROVIDER_CATALOG,
    ask_with_fallback,
    call_openai_provider,
    free_provider_names,
)


def test_free_provider_order_excludes_trial_and_account_dependent_providers():
    names = free_provider_names()

    assert names[:4] == ["gemini", "groq", "openrouter", "mistral"]
    assert "zai" in names
    assert "nvidia" not in names
    assert "cerebras" not in names


def test_fallback_skips_unavailable_free_providers_without_calling_paid_ones(
    monkeypatch,
):
    from unittest.mock import patch

    names = free_provider_names()
    for name in names:
        provider = next(item for item in PROVIDER_CATALOG if item["id"] == name)
        monkeypatch.setenv(provider["env"], "test-key")
    monkeypatch.setenv("NVIDIA_API_KEY", "test-key")
    monkeypatch.setenv("CEREBRAS_API_KEY", "test-key")
    monkeypatch.setenv("CLOUDFLARE_ACCOUNT_ID", "test-account")

    with patch("providers.ask_provider", side_effect=RuntimeError("quota")) as ask:
        result = ask_with_fallback("hello")

    assert result["provider"] is None
    assert [call.args[0] for call in ask.call_args_list] == names


def test_zai_model_can_be_configured(monkeypatch):
    from unittest.mock import patch

    class Response:
        def raise_for_status(self):
            pass

        def json(self):
            return {"choices": [{"message": {"content": "ok"}}]}

    monkeypatch.setenv("ZAI_API_KEY", "test-key")
    monkeypatch.setenv("ZAI_MODEL", "configured-model")

    with patch("providers.requests.post", return_value=Response()) as post:
        assert call_openai_provider("zai", "hello") == "ok"

    assert post.call_args.args[0] == "https://api.z.ai/api/paas/v4/chat/completions"
    assert post.call_args.kwargs["json"]["model"] == "configured-model"


def test_google_api_key_alias_is_used_for_gemini(monkeypatch):
    from unittest.mock import patch

    from resilience import RESILIENT_ROUTER

    class Response:
        def raise_for_status(self):
            pass

        def json(self):
            return {"choices": [{"message": {"content": "ok"}}]}

    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.setenv("GOOGLE_API_KEY", "test-key")

    assert RESILIENT_ROUTER._provider_configured("gemini")
    with patch("providers.requests.post", return_value=Response()) as post:
        assert call_openai_provider("gemini", "hello") == "ok"

    assert post.call_args.kwargs["headers"]["Authorization"] == "Bearer test-key"


def test_cloudflare_workers_ai_uses_token_and_account_id(monkeypatch):
    from unittest.mock import patch
    from resilience import RESILIENT_ROUTER

    class Response:
        def raise_for_status(self):
            pass

        def json(self):
            return {"result": {"response": "ok"}, "success": True}

    monkeypatch.setenv("CLOUDFLARE_API_TOKEN", "test-token")
    monkeypatch.setenv("CLOUDFLARE_ACCOUNT_ID", "test-account")
    monkeypatch.setenv("CLOUDFLARE_MODEL", "@cf/test-model")

    assert RESILIENT_ROUTER._provider_configured("cloudflare")
    with patch("providers.requests.post", return_value=Response()) as post:
        assert call_openai_provider("cloudflare", "hello", system="system") == "ok"

    assert post.call_args.args[0] == (
        "https://api.cloudflare.com/client/v4/accounts/test-account/ai/run/@cf/test-model"
    )
    assert post.call_args.kwargs["headers"]["Authorization"] == "Bearer test-token"
    assert post.call_args.kwargs["json"]["messages"] == [
        {"role": "system", "content": "system"},
        {"role": "user", "content": "hello"},
    ]
