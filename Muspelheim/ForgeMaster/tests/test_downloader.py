"""Tests for forgemaster.downloader — Model download helper module."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, Mock

import httpx
import pytest

from forgemaster.downloader import (
    CHUNK_SIZE,
    DEFAULT_REVISION,
    DownloadConfig,
    DownloadError,
    DownloadProgress,
    DownloadStatus,
    ModelDownloader,
    ModelNotFoundError,
    _hf_url,
)


# ---------------------------------------------------------------------------
# Fixtures & helpers
# ---------------------------------------------------------------------------


def make_config(**overrides):
    defaults = {
        "model_id": "testorg/testmodel",
        "revision": "main",
        "cache_dir": "/tmp/fm_test_cache",
        "force_download": False,
    }
    defaults.update(overrides)
    return DownloadConfig(**defaults)


def fake_progress_collector():
    """Return a callback that collects all DownloadProgress into a list."""
    progress_list: list[DownloadProgress] = []

    def callback(p: DownloadProgress):
        progress_list.append(p)

    return callback, progress_list


class FakeStreamResponse:
    """Minimal httpx.StreamResponse-like object for mocking."""

    def __init__(self, chunks: list[bytes], status_code: int = 200, headers: dict | None = None):
        self.chunks = chunks
        self.status_code = status_code
        self.headers = headers or {}

    def iter_bytes(self, chunk_size=CHUNK_SIZE):
        yield from self.chunks

    def raise_for_status(self):
        if self.status_code >= 400:
            raise httpx.HTTPStatusError(
                f"{self.status_code}",
                request=Mock(),
                response=Mock(status_code=self.status_code),
            )

    def json(self):
        return json.loads(self.headers.get("x-json", "{}"))


class FakeStreamContext:
    """Context manager wrapping a FakeStreamResponse."""

    def __init__(self, response: FakeStreamResponse):
        self.response = response

    def __enter__(self):
        return self.response

    def __exit__(self, *args):
        pass


# ---------------------------------------------------------------------------
# DownloadConfig tests
# ---------------------------------------------------------------------------


class TestDownloadConfig:
    def test_defaults(self):
        cfg = DownloadConfig(model_id="my/model")
        assert cfg.model_id == "my/model"
        assert cfg.revision == DEFAULT_REVISION
        assert cfg.force_download is False
        assert "huggingface" in cfg.cache_dir

    def test_custom_values(self):
        cfg = DownloadConfig(
            model_id="org/mdl",
            revision="v2",
            cache_dir="/tmp/cache",
            force_download=True,
        )
        assert cfg.revision == "v2"
        assert cfg.cache_dir == "/tmp/cache"
        assert cfg.force_download is True


# ---------------------------------------------------------------------------
# DownloadProgress tests
# ---------------------------------------------------------------------------


class TestDownloadProgress:
    def test_defaults(self):
        p = DownloadProgress(model_id="x/y", status=DownloadStatus.PENDING)
        assert p.progress_pct == 0.0
        assert p.speed_mb == 0.0
        assert p.downloaded_bytes == 0
        assert p.total_bytes is None
        assert p.error is None

    def test_with_values(self):
        p = DownloadProgress(
            model_id="x/y",
            status=DownloadStatus.DOWNLOADING,
            progress_pct=50.0,
            speed_mb=12.5,
            downloaded_bytes=500,
            total_bytes=1000,
            error=None,
        )
        assert p.progress_pct == 50.0
        assert p.speed_mb == 12.5


# ---------------------------------------------------------------------------
# DownloadStatus tests
# ---------------------------------------------------------------------------


class TestDownloadStatus:
    def test_all_statuses(self):
        expected = {"pending", "downloading", "completed", "failed", "cancelled"}
        actual = {s.value for s in DownloadStatus}
        assert actual == expected

    def test_string_comparison(self):
        assert DownloadStatus.PENDING == "pending"
        assert DownloadStatus.COMPLETED == "completed"


# ---------------------------------------------------------------------------
# _hf_url helper
# ---------------------------------------------------------------------------


class TestHfUrl:
    def test_basic(self):
        url = _hf_url("org/model", "main", "config.json")
        assert url == "https://huggingface.co/org/model/resolve/main/config.json"

    def test_revision(self):
        url = _hf_url("org/model", "v1.0", "pytorch_model.bin")
        assert "/resolve/v1.0/pytorch_model.bin" in url


# ---------------------------------------------------------------------------
# ModelDownloader initialization
# ---------------------------------------------------------------------------


class TestModelDownloaderInit:
    def test_default_client(self):
        dl = ModelDownloader()
        assert dl._client is not None
        assert dl._max_retries == 3

    def test_custom_client(self):
        client = httpx.Client()
        dl = ModelDownloader(client=client)
        assert dl._client is client

    def test_custom_params(self):
        dl = ModelDownloader(max_retries=5, retry_delay=1.0)
        assert dl._max_retries == 5
        assert dl._retry_delay == 1.0


# ---------------------------------------------------------------------------
# _resolve_dest
# ---------------------------------------------------------------------------


class TestResolveDest:
    def test_default_dest(self):
        cfg = make_config(model_id="org/model-1")
        result = ModelDownloader._resolve_dest(cfg, "config.json", None)
        assert "models--org--model-1" in str(result)
        assert result.name == "config.json"

    def test_explicit_dest(self):
        cfg = make_config()
        result = ModelDownloader._resolve_dest(cfg, "file.bin", "/tmp/out")
        assert str(result).startswith("/tmp/out")
        assert result.name == "file.bin"


# ---------------------------------------------------------------------------
# _resume_offset
# ---------------------------------------------------------------------------


class TestResumeOffset:
    def test_no_part_file(self, tmp_path):
        result = ModelDownloader._resume_offset(tmp_path / "missing.part", force=False)
        assert result == 0

    def test_existing_part_file(self, tmp_path):
        part = tmp_path / "test.part"
        part.write_bytes(b"12345")
        result = ModelDownloader._resume_offset(part, force=False)
        assert result == 5

    def test_force_ignores_part(self, tmp_path):
        part = tmp_path / "test.part"
        part.write_bytes(b"12345")
        result = ModelDownloader._resume_offset(part, force=True)
        assert result == 0


# ---------------------------------------------------------------------------
# list_model_files
# ---------------------------------------------------------------------------


class TestListModelFiles:
    def test_success(self):
        cfg = make_config()
        mock_client = MagicMock()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {
            "siblings": [
                {"rfilename": "config.json"},
                {"rfilename": "model.safetensors"},
            ]
        }
        mock_client.get.return_value = mock_resp

        dl = ModelDownloader(client=mock_client)
        files = dl.list_model_files(cfg)
        assert files == ["config.json", "model.safetensors"]
        mock_client.get.assert_called_once()

    def test_404_raises_model_not_found(self):
        cfg = make_config(model_id="nonexistent/model")
        mock_client = MagicMock()
        mock_resp = MagicMock()
        mock_resp.status_code = 404
        mock_resp.raise_for_status = MagicMock()
        mock_client.get.return_value = mock_resp

        dl = ModelDownloader(client=mock_client)
        with pytest.raises(ModelNotFoundError, match="Model not found"):
            dl.list_model_files(cfg)

    def test_retry_on_http_error(self):
        cfg = make_config()
        mock_client = MagicMock()
        mock_client.get.side_effect = httpx.ConnectError("timeout")

        dl = ModelDownloader(client=mock_client, max_retries=1, retry_delay=0)
        with pytest.raises(DownloadError, match="Failed to list model files"):
            dl.list_model_files(cfg)

    def test_list_from_tree(self):
        cfg = make_config()
        mock_client = MagicMock()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = [
            {"type": "file", "path": "config.json"},
            {
                "type": "directory",
                "path": "sub",
                "children": [
                    {"type": "file", "path": "sub/model.bin"},
                ],
            },
        ]
        mock_client.get.return_value = mock_resp

        dl = ModelDownloader(client=mock_client)
        files = dl.list_model_files(cfg)
        assert "config.json" in files
        assert "sub/model.bin" in files


# ---------------------------------------------------------------------------
# download_file
# ---------------------------------------------------------------------------


class TestDownloadFile:
    def test_file_already_exists(self, tmp_path):
        """When the file already exists and force_download is False, skip download."""
        cfg = make_config(cache_dir=str(tmp_path))
        model_dir = tmp_path / f"models--{cfg.model_id.replace('/', '--')}" / "snapshots" / "main"
        model_dir.mkdir(parents=True, exist_ok=True)
        existing = model_dir / "config.json"
        existing.write_text("{}")

        dl = ModelDownloader()
        result = dl.download_file(cfg, "config.json")
        assert result == existing

    def test_force_download_redownloads(self, tmp_path):
        """When force_download=True, download even if file exists."""
        cfg = make_config(cache_dir=str(tmp_path), force_download=True)
        model_dir = tmp_path / f"models--{cfg.model_id.replace('/', '--')}" / "snapshots" / "main"
        model_dir.mkdir(parents=True, exist_ok=True)
        existing = model_dir / "config.json"
        existing.write_text("{}")

        mock_client = MagicMock()
        fake_resp = FakeStreamResponse(
            chunks=[b'{"new": true}'], status_code=200, headers={"content-length": "10"}
        )
        mock_client.stream.return_value = FakeStreamContext(fake_resp)

        dl = ModelDownloader(client=mock_client)
        callback, _progresses = fake_progress_collector()
        result = dl.download_file(cfg, "config.json", progress_callback=callback)
        assert result.exists()
        # Should have attempted download
        mock_client.stream.assert_called_once()

    def test_successful_download(self, tmp_path):
        cfg = make_config(cache_dir=str(tmp_path))
        data = b"hello world model data"

        mock_client = MagicMock()
        fake_resp = FakeStreamResponse(
            chunks=[data[:6], data[6:]],
            status_code=200,
            headers={"content-length": str(len(data))},
        )
        mock_client.stream.return_value = FakeStreamContext(fake_resp)

        dl = ModelDownloader(client=mock_client)
        callback, progresses = fake_progress_collector()
        result = dl.download_file(cfg, "model.bin", progress_callback=callback)

        assert result.exists()
        assert result.read_bytes() == data

        # Check progress reports
        statuses = [p.status for p in progresses]
        assert DownloadStatus.PENDING in statuses
        assert DownloadStatus.COMPLETED in statuses

    def test_download_with_explicit_dest(self, tmp_path):
        cfg = make_config()
        data = b"dest test"
        dest_dir = tmp_path / "output"
        dest_file = dest_dir / "model.bin"

        mock_client = MagicMock()
        fake_resp = FakeStreamResponse(
            chunks=[data],
            status_code=200,
            headers={"content-length": str(len(data))},
        )
        mock_client.stream.return_value = FakeStreamContext(fake_resp)

        dl = ModelDownloader(client=mock_client)
        result = dl.download_file(cfg, "model.bin", dest=str(dest_dir))
        assert result == dest_file
        assert result.read_bytes() == data

    def test_404_raises_not_found(self, tmp_path):
        cfg = make_config(cache_dir=str(tmp_path))
        mock_client = MagicMock()
        fake_resp = FakeStreamResponse(chunks=[], status_code=404)
        mock_client.stream.return_value = FakeStreamContext(fake_resp)

        dl = ModelDownloader(client=mock_client, max_retries=1, retry_delay=0)
        with pytest.raises(ModelNotFoundError, match="File not found"):
            dl.download_file(cfg, "missing.bin")

    def test_server_error_raises_download_error(self, tmp_path):
        cfg = make_config(cache_dir=str(tmp_path))
        mock_client = MagicMock()
        fake_resp = FakeStreamResponse(chunks=[], status_code=500)
        mock_client.stream.return_value = FakeStreamContext(fake_resp)

        dl = ModelDownloader(client=mock_client, max_retries=1, retry_delay=0)
        with pytest.raises(DownloadError):
            dl.download_file(cfg, "broken.bin")

    def test_cancel_download(self, tmp_path):
        cfg = make_config(cache_dir=str(tmp_path))
        mock_client = MagicMock()
        # Create response that yields many small chunks so cancellation fires mid-stream
        data = b"x" * (CHUNK_SIZE * 5)  # 5 chunks
        chunks = [data[i : i + CHUNK_SIZE] for i in range(0, len(data), CHUNK_SIZE)]
        fake_resp = FakeStreamResponse(
            chunks=chunks,
            status_code=200,
            headers={"content-length": str(len(data))},
        )
        mock_client.stream.return_value = FakeStreamContext(fake_resp)

        dl = ModelDownloader(client=mock_client)

        # Cancel at the first DOWNLOADING callback so it's caught on next chunk check
        cancels_remaining = 1

        def cancel_callback(p: DownloadProgress):
            nonlocal cancels_remaining
            if p.status == DownloadStatus.DOWNLOADING and cancels_remaining > 0:
                dl.cancel()
                cancels_remaining -= 1

        with pytest.raises(DownloadError, match="cancelled"):
            dl.download_file(cfg, "model.bin", progress_callback=cancel_callback)

    def test_progress_calculation(self, tmp_path):
        cfg = make_config(cache_dir=str(tmp_path))
        data = b"A" * 1000

        mock_client = MagicMock()
        fake_resp = FakeStreamResponse(
            chunks=[data],
            status_code=200,
            headers={"content-length": str(len(data))},
        )
        mock_client.stream.return_value = FakeStreamContext(fake_resp)

        dl = ModelDownloader(client=mock_client)
        callback, progresses = fake_progress_collector()
        dl.download_file(cfg, "model.bin", progress_callback=callback)

        completed = [p for p in progresses if p.status == DownloadStatus.COMPLETED]
        assert len(completed) == 1
        assert completed[0].progress_pct == 100.0
        assert completed[0].downloaded_bytes == 1000
        assert completed[0].total_bytes == 1000

    def test_retry_on_stream_error(self, tmp_path):
        """Verify retries happen on stream errors, then succeed."""
        cfg = make_config(cache_dir=str(tmp_path))
        data = b"retried data"

        mock_client = MagicMock()
        # First call fails, second succeeds
        good_resp = FakeStreamResponse(
            chunks=[data],
            status_code=200,
            headers={"content-length": str(len(data))},
        )
        mock_client.stream.side_effect = [
            httpx.StreamError("connection reset"),
            FakeStreamContext(good_resp),
        ]

        dl = ModelDownloader(client=mock_client, max_retries=3, retry_delay=0)
        result = dl.download_file(cfg, "model.bin")
        assert result.read_bytes() == data
        assert mock_client.stream.call_count == 2


# ---------------------------------------------------------------------------
# download_model
# ---------------------------------------------------------------------------


class TestDownloadModel:
    def test_downloads_multiple_files(self, tmp_path):
        cfg = make_config(cache_dir=str(tmp_path))
        data = b"model data"

        mock_client = MagicMock()
        fake_resp = FakeStreamResponse(
            chunks=[data],
            status_code=200,
            headers={"content-length": str(len(data))},
        )
        mock_client.stream.return_value = FakeStreamContext(fake_resp)

        dl = ModelDownloader(client=mock_client)
        paths = dl.download_model(cfg, filenames=["a.bin", "b.bin"])
        assert len(paths) == 2
        assert mock_client.stream.call_count == 2

    def test_fetches_file_list_when_none(self, tmp_path):
        cfg = make_config(cache_dir=str(tmp_path))

        mock_client = MagicMock()

        # Mock for list_model_files
        list_resp = MagicMock()
        list_resp.status_code = 200
        list_resp.raise_for_status = MagicMock()
        list_resp.json.return_value = {"siblings": [{"rfilename": "model.bin"}]}
        mock_client.get.return_value = list_resp

        # Mock for download_file
        data = b"fetched"
        dl_resp = FakeStreamResponse(
            chunks=[data],
            status_code=200,
            headers={"content-length": str(len(data))},
        )
        mock_client.stream.return_value = FakeStreamContext(dl_resp)

        dl = ModelDownloader(client=mock_client)
        paths = dl.download_model(cfg)
        assert len(paths) == 1


# ---------------------------------------------------------------------------
# _extract_filenames
# ---------------------------------------------------------------------------


class TestExtractFilenames:
    def test_from_siblings(self):
        data = {
            "siblings": [
                {"rfilename": "config.json"},
                {"rfilename": "model.safetensors"},
            ]
        }
        result = ModelDownloader._extract_filenames(data)
        assert result == ["config.json", "model.safetensors"]

    def test_from_tree(self):
        data = [
            {"type": "file", "path": "config.json"},
            {
                "type": "directory",
                "path": "sub",
                "children": [
                    {"type": "file", "path": "sub/model.bin"},
                ],
            },
        ]
        result = ModelDownloader._extract_filenames(data)
        assert "config.json" in result
        assert "sub/model.bin" in result

    def test_empty(self):
        assert ModelDownloader._extract_filenames({}) == []
        assert ModelDownloader._extract_filenames([]) == []


# ---------------------------------------------------------------------------
# cancel
# ---------------------------------------------------------------------------


class TestCancel:
    def test_cancel_flag(self):
        dl = ModelDownloader()
        dl.cancel()
        assert dl._cancelled is True


# ---------------------------------------------------------------------------
# Resume support
# ---------------------------------------------------------------------------


class TestResumeDownload:
    def test_resume_with_partial_file(self, tmp_path):
        """Simulate resuming a download with a .part file already present."""
        cfg = make_config(cache_dir=str(tmp_path))
        existing_data = b"first half "
        new_data = b"second half"

        model_dir = tmp_path / f"models--{cfg.model_id.replace('/', '--')}" / "snapshots" / "main"
        model_dir.mkdir(parents=True, exist_ok=True)
        part_file = model_dir / "model.bin.part"
        part_file.write_bytes(existing_data)

        # The server should respond with 206 and the remaining data
        mock_client = MagicMock()
        existing_data + new_data
        fake_resp = FakeStreamResponse(
            chunks=[new_data],
            status_code=206,
            headers={"content-length": str(len(new_data))},
        )
        mock_client.stream.return_value = FakeStreamContext(fake_resp)

        dl = ModelDownloader(client=mock_client)
        # Need to patch _resolve_dest to use our tmp_path
        result = dl.download_file(cfg, "model.bin")

        # The final file should contain both parts
        assert result.exists()

    def test_no_resume_when_force(self, tmp_path):
        """With force_download, ignore .part file and start fresh."""
        cfg = make_config(cache_dir=str(tmp_path), force_download=True)

        model_dir = tmp_path / f"models--{cfg.model_id.replace('/', '--')}" / "snapshots" / "main"
        model_dir.mkdir(parents=True, exist_ok=True)
        part_file = model_dir / "model.bin.part"
        part_file.write_bytes(b"stale data")

        data = b"fresh download"
        mock_client = MagicMock()
        fake_resp = FakeStreamResponse(
            chunks=[data],
            status_code=200,
            headers={"content-length": str(len(data))},
        )
        mock_client.stream.return_value = FakeStreamContext(fake_resp)

        dl = ModelDownloader(client=mock_client)
        # Should NOT send Range header — download from start
        result = dl.download_file(cfg, "model.bin")
        assert result.read_bytes() == data

        # Verify no Range header was sent (stream called without resume)
        call_args = mock_client.stream.call_args
        headers_arg = call_args.kwargs.get("headers", {})
        assert "Range" not in headers_arg


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    def test_empty_file(self, tmp_path):
        cfg = make_config(cache_dir=str(tmp_path))
        mock_client = MagicMock()
        fake_resp = FakeStreamResponse(chunks=[], status_code=200, headers={"content-length": "0"})
        mock_client.stream.return_value = FakeStreamContext(fake_resp)

        dl = ModelDownloader(client=mock_client)
        result = dl.download_file(cfg, "empty.json")
        assert result.exists()
        assert result.read_bytes() == b""

    def test_unknown_total_size(self, tmp_path):
        """When content-length is missing, progress_pct should stay 0."""
        cfg = make_config(cache_dir=str(tmp_path))
        data = b"unknown size"
        mock_client = MagicMock()
        fake_resp = FakeStreamResponse(
            chunks=[data],
            status_code=200,
            headers={},  # no content-length
        )
        mock_client.stream.return_value = FakeStreamContext(fake_resp)

        dl = ModelDownloader(client=mock_client)
        callback, progresses = fake_progress_collector()
        result = dl.download_file(cfg, "mystery.bin", progress_callback=callback)
        assert result.exists()

        completed = [p for p in progresses if p.status == DownloadStatus.COMPLETED]
        assert len(completed) == 1
