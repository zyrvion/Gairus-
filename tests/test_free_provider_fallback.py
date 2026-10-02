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
