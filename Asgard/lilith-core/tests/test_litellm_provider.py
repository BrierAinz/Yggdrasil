"""Tests for LiteLLMProvider."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from lilith_core.config import Config
from lilith_core.exceptions import LLMError
from lilith_core.providers.litellm_provider import LiteLLMProvider


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------


def _make_response(content: str = "hello", model: str = "test-model") -> MagicMock:
    """Build a lightweight object that mimics litellm.ModelResponse."""
    choice = MagicMock()
    choice.message.content = content
    choice.finish_reason = "stop"

    usage = MagicMock()
    usage.prompt_tokens = 10
    usage.completion_tokens = 5
    usage.total_tokens = 15

    resp = MagicMock()
    resp.choices = [choice]
    resp.model = model
    resp.usage = usage
    return resp


# ------------------------------------------------------------------
# Tests
# ------------------------------------------------------------------


def test_litellm_import():
    """Verify that litellm can be imported (it's listed as a dependency)."""
    import litellm  # noqa: F401

    assert True


def test_provider_init(tmp_path):
    """LiteLLMProvider initialises with a Config and resolves defaults."""
    config = Config(root_path=tmp_path)
    provider = LiteLLMProvider(config=config)
    assert provider.config is config
    assert provider.list_models() == [f"openai/{config.get('lm_studio_url')}"]


@pytest.mark.asyncio
async def test_complete_mock(tmp_path):
    """complete() returns a normalised dict and delegates to litellm.acompletion."""
    config = Config(root_path=tmp_path)
    provider = LiteLLMProvider(config=config)

    fake_resp = _make_response(content="world", model="gpt-4")

    with patch("lilith_core.providers.litellm_provider.litellm") as mock_litellm:
        mock_litellm.acompletion = AsyncMock(return_value=fake_resp)
        result = await provider.complete(
            messages=[{"role": "user", "content": "hi"}],
            model="gpt-4",
        )

    assert result["content"] == "world"
    assert result["model"] == "gpt-4"
    assert result["usage"]["total_tokens"] == 15
    assert result["finish_reason"] == "stop"


@pytest.mark.asyncio
async def test_fallback_to_local(tmp_path):
    """When model='auto' the provider routes to the local LM Studio URL."""
    config = Config(root_path=tmp_path)
    provider = LiteLLMProvider(config=config)

    fake_resp = _make_response(content="local-reply", model="openai/local")

    with patch("lilith_core.providers.litellm_provider.litellm") as mock_litellm:
        mock_litellm.acompletion = AsyncMock(return_value=fake_resp)
        result = await provider.complete(
            messages=[{"role": "user", "content": "hi"}],
            model="auto",
        )

    called_model = mock_litellm.acompletion.call_args.kwargs.get(
        "model", mock_litellm.acompletion.call_args[1].get("model")
    )
    expected = f"openai/{config.get('lm_studio_url')}"
    assert called_model == expected
    assert result["content"] == "local-reply"


@pytest.mark.asyncio
async def test_complete_retries_on_failure(tmp_path):
    """complete() retries up to _MAX_RETRIES times before raising LLMError."""
    config = Config(root_path=tmp_path)
    provider = LiteLLMProvider(config=config)

    call_count = 0

    async def _flaky_completion(**kwargs: Any):
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise RuntimeError("transient failure")
        return _make_response(content="recovered")

    with (
        patch("lilith_core.providers.litellm_provider.litellm") as mock_litellm,
        patch("lilith_core.providers.litellm_provider.asyncio.sleep", new_callable=AsyncMock),
    ):
        mock_litellm.acompletion = _flaky_completion
        result = await provider.complete(
            messages=[{"role": "user", "content": "retry me"}],
        )

    assert call_count == 3
    assert result["content"] == "recovered"


@pytest.mark.asyncio
async def test_complete_exhausts_retries(tmp_path):
    """When all retries fail, LLMError is raised."""
    config = Config(root_path=tmp_path)
    provider = LiteLLMProvider(config=config)

    with (
        patch("lilith_core.providers.litellm_provider.litellm") as mock_litellm,
        patch("lilith_core.providers.litellm_provider.asyncio.sleep", new_callable=AsyncMock),
        pytest.raises(LLMError, match="LiteLLM failed after"),
    ):
        mock_litellm.acompletion = AsyncMock(side_effect=RuntimeError("boom"))
        await provider.complete(
            messages=[{"role": "user", "content": "fail"}],
        )
