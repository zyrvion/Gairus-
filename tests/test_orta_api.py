import json
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

os.environ["GAIRUS_AUTONOMY"] = "false"
os.environ["GAIRUS_ORTA_API_KEY"] = "test-orta-key"
os.environ["GAIRUS_DATA_DIR"] = tempfile.mkdtemp(prefix="gairus-orta-test-")

from app import app


def test_orta_endpoint_requires_bearer_key():
    client = app.test_client()

    response = client.post(
        "/api/orta/chat",
        json={"system_prompt": "system", "input_text": "hello"},
    )

    assert response.status_code == 401


def test_orta_endpoint_fails_closed_without_configured_key(monkeypatch):
    client = app.test_client()
    monkeypatch.delenv("GAIRUS_ORTA_API_KEY")

    response = client.post(
        "/api/orta/chat",
        headers={"Authorization": "Bearer test-orta-key"},
        json={"system_prompt": "system", "input_text": "hello"},
    )

    assert response.status_code == 503


def test_orta_endpoint_returns_normalized_structured_output():
    client = app.test_client()
    model_output = {
        "reply": "Je vous aide.",
        "intent": "order",
        "itemQuery": "riz",
        "quantity": 2,
        "amount": 1500,
    }

    with patch(
        "app.ask_with_fallback",
        return_value={"provider": "groq", "reply": json.dumps(model_output)},
    ) as ask:
        response = client.post(
            "/api/orta/chat",
            headers={"Authorization": "Bearer test-orta-key"},
            json={"system_prompt": "Réponds en JSON.", "input_text": "Je veux du riz."},
        )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["reply"] == "Je vous aide."
    assert payload["intent"] == "order"
    assert payload["itemQuery"] == "riz"
    assert payload["quantity"] == 2
    assert payload["vendorQuery"] == ""
    ask.assert_called_once()


def test_orta_endpoint_reports_provider_unavailable():
    client = app.test_client()

    with patch(
        "app.ask_with_fallback",
        return_value={"provider": None, "reply": "Aucun fournisseur IA disponible."},
    ):
        response = client.post(
            "/api/orta/chat",
            headers={"Authorization": "Bearer test-orta-key"},
            json={"system_prompt": "system", "input_text": "hello"},
        )

    assert response.status_code == 503
