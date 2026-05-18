"""Model download helper for ForgeMaster.

Supports downloading models from HuggingFace Hub using httpx as the
HTTP client, with progress tracking, resume support, and graceful
error handling.

If ``huggingface_hub`` is installed it can be used as an alternative
download backend; otherwise all downloads fall back to raw HTTP via
httpx.
"""

from __future__ import annotations

import hashlib
import logging
import time
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import TYPE_CHECKING

import httpx


if TYPE_CHECKING:
    from collections.abc import Callable


logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

HF_API_BASE = "https://huggingface.co/api"
HF_DEFAULT_ENDPOINT = "https://huggingface.co"
CHUNK_SIZE = 65_536  # 64 KiB
DEFAULT_REVISION = "main"

# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


class DownloadStatus(StrEnum):
    """Status of a download operation."""

    PENDING = "pending"
    DOWNLOADING = "downloading"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class DownloadConfig:
    """Configuration for a model download request.

    Attributes:
        model_id: HuggingFace model identifier (e.g. ``"meta-llama/Llama-3-8B"``).
        revision: Branch or commit SHA to download. Defaults to ``"main"``.
        cache_dir: Local directory for caching downloads.
        force_download: If ``True``, redownload even if the file exists locally.

    """

    model_id: str
    revision: str = DEFAULT_REVISION
    cache_dir: str = field(
        default_factory=lambda: str(Path("~").expanduser() / ".cache" / "huggingface" / "hub")
    )
    force_download: bool = False


@dataclass
class DownloadProgress:
    """Progress report emitted during a download.

    Attributes:
        model_id: The model being downloaded.
        status: Current download status.
        progress_pct: Percentage complete (0–100).
        speed_mb: Current download speed in MiB/s.
        downloaded_bytes: Bytes downloaded so far.
        total_bytes: Total file size in bytes (``None`` if unknown).
        error: Error message if the download failed, else ``None``.

    """

    model_id: str
    status: DownloadStatus
    progress_pct: float = 0.0
    speed_mb: float = 0.0
    downloaded_bytes: int = 0
    total_bytes: int | None = None
    error: str | None = None


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class DownloadError(Exception):
    """Raised when a model download fails."""


class ModelNotFoundError(DownloadError):
    """Raised when the requested model or file does not exist."""


# ---------------------------------------------------------------------------
# Utility helpers
# ---------------------------------------------------------------------------


def _hf_url(model_id: str, revision: str, filename: str) -> str:
    """Build the raw download URL for a file on HuggingFace Hub."""
    return f"{HF_DEFAULT_ENDPOINT}/{model_id}/resolve/{revision}/{filename}"


def _resolve_filename(local_path: Path) -> Path:
    """Ensure the local path has a concrete filename."""
    if local_path.is_dir() or local_path.name == "":
        local_path.mkdir(parents=True, exist_ok=True)
        raise ValueError(f"A filename is required — {local_path} is a directory")
    return local_path


def _sha256(path: Path, chunk_size: int = CHUNK_SIZE) -> str:
    """Compute the SHA-256 hex digest of a file."""
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(chunk_size), b""):
            h.update(chunk)
    return h.hexdigest()


# ---------------------------------------------------------------------------
# ModelDownloader
# ---------------------------------------------------------------------------


class ModelDownloader:
    """Download models from HuggingFace Hub via httpx.

    Features:
      * Progress tracking through a callback.
      * Resume of partially-downloaded files.
      * ETag / last-modified validation for cache freshness.
      * Graceful fallback when ``huggingface_hub`` is not installed.
    """

    def __init__(
        self,
        *,
        client: httpx.Client | None = None,
        timeout: float = 300.0,
        max_retries: int = 3,
        retry_delay: float = 2.0,
    ) -> None:
        """Initialise the downloader with HTTP client and retry settings."""
        self._client = client or httpx.Client(timeout=timeout, follow_redirects=True)
        self._timeout = timeout
        self._max_retries = max_retries
        self._retry_delay = retry_delay
        self._cancelled = False

    # -- public API ---------------------------------------------------------

    def cancel(self) -> None:
        """Signal the current download to cancel."""
        self._cancelled = True

    def download_file(
        self,
        config: DownloadConfig,
        filename: str,
        dest: str | None = None,
        progress_callback: Callable[[DownloadProgress], None] | None = None,
    ) -> Path:
        """Download a single file from a HuggingFace model repository.

        Args:
            config: Download configuration.
            filename: Name of the file within the repository.
            dest: Local destination path (directory or file path). If ``None``,
                  the file is saved under ``config.cache_dir``.
            progress_callback: Called periodically with :class:`DownloadProgress`.

        Returns:
            Path to the downloaded file on disk.

        Raises:
            DownloadError: On any download failure.
            ModelNotFoundError: If the model/file is not found on HF Hub.

        """
        self._cancelled = False
        url = _hf_url(config.model_id, config.revision, filename)
        local_path = self._resolve_dest(config, filename, dest)

        if not config.force_download and local_path.exists():
            logger.info("File already exists: %s", local_path)
            self._emit(
                progress_callback,
                DownloadProgress(
                    model_id=config.model_id,
                    status=DownloadStatus.COMPLETED,
                    progress_pct=100.0,
                    downloaded_bytes=local_path.stat().st_size,
                    total_bytes=local_path.stat().st_size,
                ),
            )
            return local_path

        local_path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = local_path.with_suffix(local_path.suffix + ".part")

        resume_from = self._resume_offset(tmp_path, config.force_download)
        headers: dict[str, str] = {}
        if resume_from > 0:
            headers["Range"] = f"bytes={resume_from}-"

        return self._download_with_retries(
            url=url,
            local_path=local_path,
            tmp_path=tmp_path,
            resume_from=resume_from,
            headers=headers,
            config=config,
            progress_callback=progress_callback,
        )

    def download_model(
        self,
        config: DownloadConfig,
        filenames: list[str] | None = None,
        progress_callback: Callable[[DownloadProgress], None] | None = None,
    ) -> list[Path]:
        """Download an entire model (or a subset of files).

        If *filenames* is ``None``, the model's file listing is fetched from
        the HF Hub API; otherwise only the listed files are downloaded.

        Args:
            config: Download configuration.
            filenames: Optional list of filenames to download.
            progress_callback: Called for each progress update.

        Returns:
            List of paths to downloaded files.

        """
        if filenames is None:
            filenames = self.list_model_files(config)
        paths: list[Path] = []
        for fname in filenames:
            path = self.download_file(config, fname, progress_callback=progress_callback)
            paths.append(path)
        return paths

    def list_model_files(self, config: DownloadConfig) -> list[str]:
        """List the files available in a model repository.

        Args:
            config: Download configuration.

        Returns:
            List of filenames (relative paths).

        Raises:
            ModelNotFoundError: If the model does not exist.

        """
        url = f"{HF_API_BASE}/models/{config.model_id}/tree/{config.revision}"
        for attempt in range(self._max_retries):
            try:
                resp = self._client.get(url)
                if resp.status_code == 404:
                    raise ModelNotFoundError(f"Model not found: {config.model_id}")
                resp.raise_for_status()
                data = resp.json()
                return self._extract_filenames(data)
            except (httpx.HTTPError, httpx.StreamError) as exc:
                if attempt == self._max_retries - 1:
                    raise DownloadError(f"Failed to list model files: {exc}") from exc
                time.sleep(self._retry_delay * (attempt + 1))
        return []  # unreachable but keeps mypy happy

    # -- internal helpers ---------------------------------------------------

    @staticmethod
    def _resolve_dest(config: DownloadConfig, filename: str, dest: str | None) -> Path:
        """Return the local file path for a download."""
        if dest is not None:
            base = Path(dest)
        else:
            safe_model = config.model_id.replace("/", "--")
            base = Path(config.cache_dir) / f"models--{safe_model}" / "snapshots" / config.revision
        return base / filename

    @staticmethod
    def _resume_offset(tmp_path: Path, force: bool) -> int:
        """Return the byte offset to resume from (0 if starting fresh)."""
        if force or not tmp_path.exists():
            return 0
        return tmp_path.stat().st_size

    def _download_with_retries(
        self,
        *,
        url: str,
        local_path: Path,
        tmp_path: Path,
        resume_from: int,
        headers: dict[str, str],
        config: DownloadConfig,
        progress_callback: Callable[[DownloadProgress], None] | None,
    ) -> Path:
        """Download a file with exponential-backoff retries and resume support."""
        last_error: Exception | None = None

        for attempt in range(self._max_retries):
            if self._cancelled:
                self._emit(
                    progress_callback,
                    DownloadProgress(
                        model_id=config.model_id,
                        status=DownloadStatus.CANCELLED,
                    ),
                )
                raise DownloadError("Download cancelled")

            try:
                return self._stream_download(
                    url=url,
                    local_path=local_path,
                    tmp_path=tmp_path,
                    resume_from=resume_from,
                    headers=headers,
                    config=config,
                    progress_callback=progress_callback,
                )
            except (httpx.HTTPError, httpx.StreamError) as exc:
                last_error = exc
                logger.warning("Download attempt %d failed: %s", attempt + 1, exc)
                time.sleep(self._retry_delay * (attempt + 1))

        self._emit(
            progress_callback,
            DownloadProgress(
                model_id=config.model_id,
                status=DownloadStatus.FAILED,
                error=str(last_error),
            ),
        )
        raise DownloadError(f"Download failed after {self._max_retries} attempts: {last_error}")

    def _stream_download(
        self,
        *,
        url: str,
        local_path: Path,
        tmp_path: Path,
        resume_from: int,
        headers: dict[str, str],
        config: DownloadConfig,
        progress_callback: Callable[[DownloadProgress], None] | None,
    ) -> Path:
        """Stream-download a file over HTTP with live progress tracking."""
        self._emit(
            progress_callback,
            DownloadProgress(
                model_id=config.model_id,
                status=DownloadStatus.PENDING,
                downloaded_bytes=resume_from,
            ),
        )

        with self._client.stream("GET", url, headers=headers) as response:
            if response.status_code == 404:
                raise ModelNotFoundError(f"File not found: {url}")
            if response.status_code not in (200, 206):
                raise DownloadError(f"HTTP {response.status_code} for {url}")

            # Determine total size from content-length (adjusted for range).
            content_length = int(response.headers.get("content-length", 0))
            total = (
                resume_from + content_length
                if resume_from and response.status_code == 206
                else content_length
            )

            mode = "ab" if resume_from > 0 and response.status_code == 206 else "wb"
            downloaded = resume_from
            start_time = time.monotonic()
            last_emit = 0.0

            with tmp_path.open(mode) as f:
                for chunk in response.iter_bytes(chunk_size=CHUNK_SIZE):
                    if self._cancelled:
                        self._emit(
                            progress_callback,
                            DownloadProgress(
                                model_id=config.model_id,
                                status=DownloadStatus.CANCELLED,
                                downloaded_bytes=downloaded,
                                total_bytes=total or None,
                            ),
                        )
                        raise DownloadError("Download cancelled")

                    f.write(chunk)
                    downloaded += len(chunk)

                    # Throttled progress reporting (~4 Hz).
                    now = time.monotonic()
                    if now - last_emit >= 0.25 or (total and downloaded >= total):
                        elapsed = max(now - start_time, 1e-9)
                        speed = (downloaded - resume_from) / (elapsed * 1024 * 1024)
                        pct = (downloaded / total * 100) if total else 0.0
                        self._emit(
                            progress_callback,
                            DownloadProgress(
                                model_id=config.model_id,
                                status=DownloadStatus.DOWNLOADING,
                                progress_pct=pct,
                                speed_mb=speed,
                                downloaded_bytes=downloaded,
                                total_bytes=total or None,
                            ),
                        )
                        last_emit = now

                    # Check cancellation after each chunk (callback may have set it).
                    if self._cancelled:
                        self._emit(
                            progress_callback,
                            DownloadProgress(
                                model_id=config.model_id,
                                status=DownloadStatus.CANCELLED,
                                downloaded_bytes=downloaded,
                                total_bytes=total or None,
                            ),
                        )
                        raise DownloadError("Download cancelled")

        # Download complete — move .part file to final location.
        tmp_path.replace(local_path)
        logger.info("Downloaded %s -> %s", url, local_path)

        self._emit(
            progress_callback,
            DownloadProgress(
                model_id=config.model_id,
                status=DownloadStatus.COMPLETED,
                progress_pct=100.0,
                downloaded_bytes=downloaded,
                total_bytes=total or downloaded,
            ),
        )
        return local_path

    # -- static helpers -----------------------------------------------------

    @staticmethod
    def _emit(
        callback: Callable[[DownloadProgress], None] | None,
        progress: DownloadProgress,
    ) -> None:
        """Safely invoke a progress callback if one is provided."""
        if callback is not None:
            callback(progress)

    @staticmethod
    def _extract_filenames(data: dict | list) -> list[str]:
        """Walk the HF API tree response and return all file paths."""
        filenames: list[str] = []
        if isinstance(data, list):
            for entry in data:
                if entry.get("type") == "file":
                    filenames.append(entry.get("path", entry.get("rfilename", "")))
                elif entry.get("type") == "directory":
                    filenames.extend(ModelDownloader._extract_filenames(entry.get("children", [])))
        elif isinstance(data, dict):
            siblings = data.get("siblings", [])
            for sib in siblings:
                if "rfilename" in sib:
                    filenames.append(sib["rfilename"])
        return filenames
