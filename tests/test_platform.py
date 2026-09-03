from unittest.mock import Mock, patch

import pytest

from app.modules.platform import digest_payload, send_digest


def test_digest_payload_keeps_delivery_stats() -> None:
    payload = digest_payload("daily", "2026-08-10", "digest", [{"ticker": "ES"}], ["source failed"], 12)
    assert payload["period"] == "daily"
    assert payload["signals_count"] == 1
    assert payload["bars_count"] == 12


def test_send_digest_posts_bearer_authenticated_payload() -> None:
    settings = {
        "platform_digest_enabled": True,
        "platform_api_url": "https://platform.example",
        "platform_ingest_token": "secret",
    }
    response = Mock()
    with patch("app.modules.platform.requests.post", return_value=response) as post:
        send_digest(settings, {"period": "daily"})
    post.assert_called_once_with(
        "https://platform.example/api/v1/insider/digests",
        json={"period": "daily"},
        headers={"Authorization": "Bearer secret"},
        timeout=15,
    )
    response.raise_for_status.assert_called_once()


def test_enabled_delivery_fails_closed_when_config_is_missing() -> None:
    with pytest.raises(RuntimeError):
        send_digest(
            {"platform_digest_enabled": True, "platform_api_url": "", "platform_ingest_token": ""},
            {},
        )
