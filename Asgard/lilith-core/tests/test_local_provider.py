"""Tests for LocalProvider."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from lilith_core.config import Config
from lilith_core.exceptions import LLMError
from lilith_core.providers.local_provider import LocalProvider


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------


def _make_httpx_response(json_body: dict, status_code: int = 200) -> MagicMock:
    """Build a lightweight object that mimics httpx.Response."""
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_body
    resp.raise_for_status = MagicMock()
    return resp


def _sample_completion() -> dict:
    """Return a typical /chat/completions JSON payload."""
    return {
        "model": "local-model",
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": "hi there"},
                "finish_reason": "stop",
            }
        ],
        "usage": {
            "prompt_tokens": 8,
            "completion_tokens": 3,
            "total_tokens": 11,
        },
    }


# ------------------------------------------------------------------
# Tests
# ------------------------------------------------------------------


def test_local_provider_init(tmp_path):
    """LocalProvider uses Config to derive its base_url."""
    config = Config(root_path=tmp_path)
    provider = LocalProvider(config=config)
    assert provider.base_url == config.get("lm_studio_url")
    assert provider.list_models() == [provider.base_url]


@pytest.mark.asyncio
async def test_complete_mock(tmp_path):
    """complete() posts to the local server and returns normalised dict."""
    config = Config(root_path=tmp_path)
    provider = LocalProvider(config=config)

    fake_resp = _make_httpx_response(_sample_completion())

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    mock_client.post = AsyncMock(return_value=fake_resp)

    with patch("lilith_core.providers.local_provider.httpx.AsyncClient", return_value=mock_client):
        result = await provider.complete(
            messages=[{"role": "user", "content": "hello"}],
        )

    assert result["content"] == "hi there"
    assert result["model"] == "local-model"
    assert result["usage"]["total_tokens"] == 11
    assert result["finish_reason"] == "stop"


@pytest.mark.asyncio
async def test_complete_http_error(tmp_path):
    """complete() raises LLMError on httpx failures."""
    config = Config(root_path=tmp_path)
    provider = LocalProvider(config=config)

    import httpx

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    mock_client.post = AsyncMock(side_effect=httpx.ConnectError("refused"))

    with (
        patch("lilith_core.providers.local_provider.httpx.AsyncClient", return_value=mock_client),
        pytest.raises(LLMError, match="Local provider request failed"),
    ):
        await provider.complete(
            messages=[{"role": "user", "content": "fail"}],
        )
