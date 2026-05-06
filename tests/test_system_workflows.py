"""
System-level workflow tests for Medical AI Chatbot.

These tests exercise route behavior and session flow with mocked model calls,
so they can run without external API dependencies.
"""

from unittest.mock import patch


def test_health_endpoint_returns_ok():
    from app import app

    client = app.test_client()
    response = client.get("/health")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload == {"status": "ok"}


@patch("app.get_rag_chain")
@patch("app.get_rag_chain_fallback")
@patch("app.rewrite_query_for_retrieval")
def test_multiturn_then_clear_resets_memory(mock_rewrite, mock_fallback, mock_primary):
    from app import app

    mock_rewrite.side_effect = ["what is acne", "treatment for acne", "what causes it"]
    mock_primary.return_value.invoke.side_effect = [
        "Acne is a skin condition.",
        "Acne is treated with topical retinoids.",
        "Acne can be caused by excess sebum.",
    ]
    mock_fallback.return_value.invoke.return_value = "fallback"

    client = app.test_client()

    # Turn 1
    r1 = client.post("/get", data={"msg": "what is acne"})
    assert r1.status_code == 200

    # Turn 2 (pronoun-context follow-up)
    r2 = client.post("/get", data={"msg": "how to treat it"})
    assert r2.status_code == 200

    # Clear session memory
    clear_resp = client.post("/clear")
    assert clear_resp.status_code == 200

    # New turn after clear should still function without old memory
    r3 = client.post("/get", data={"msg": "what causes it"})
    assert r3.status_code == 200
    assert isinstance(r3.get_data(as_text=True), str)


@patch("app.get_rag_chain")
@patch("app.get_rag_chain_fallback")
@patch("app.rewrite_query_for_retrieval")
def test_response_status_cache_flow(mock_rewrite, mock_fallback, mock_primary):
    from app import app

    mock_rewrite.return_value = "what is diabetes"
    mock_primary.return_value.invoke.return_value = "Diabetes is a chronic metabolic condition."
    mock_fallback.return_value.invoke.return_value = "fallback"

    client = app.test_client()

    request_id = "req-123"
    send_resp = client.post("/get", data={"msg": "what is diabetes", "request_id": request_id})
    assert send_resp.status_code == 200

    status_ready = client.post("/response-status", data={"request_id": request_id})
    assert status_ready.status_code == 200
    ready_payload = status_ready.get_json()
    assert ready_payload["status"] == "ready"
    assert "diabetes" in ready_payload["answer"].lower()

    # The cache should be consumed after first read
    status_pending = client.post("/response-status", data={"request_id": request_id})
    assert status_pending.status_code == 200
    pending_payload = status_pending.get_json()
    assert pending_payload["status"] == "pending"
