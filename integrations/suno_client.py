"""Suno API client — submit music generation job, poll for completion, download audio."""

import json
import logging
import os
import time
import uuid
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

try:
    import httpx
    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False

SUNO_BASE_URL = "https://studio-api.suno.ai/api"
MOCK_AUDIO_PATH = "storage/mock_audio/silence_3min.mp3"


class SunoClient:
    """Client for Suno AI music generation API.

    Falls back to mock mode automatically when SUNO_API_KEY is absent,
    matching the pattern used by LyricsAgent._mock_response().
    """

    def __init__(self, api_key: str | None = None, mock_mode: bool = False):
        self._api_key = api_key or os.environ.get("SUNO_API_KEY", "")
        self._mock_mode = mock_mode or not self._api_key
        if self._mock_mode:
            logger.info("SunoClient: running in mock mode (no SUNO_API_KEY)")

    def generate_song(
        self,
        prompt: str,
        negative_prompt: str = "",
        duration_seconds: int | None = None,
        make_instrumental: bool = False,
        model: str = "chirp-v3-5",
        job_id: str | None = None,
        artist_id: str = "aarav",
        storage_dir: str = "storage",
    ) -> dict[str, Any]:
        """Submit a generation job and block until audio is ready.

        Returns dict with keys: suno_job_id, audio_url, audio_file,
        duration, status, provider.
        """
        job_id = job_id or str(uuid.uuid4())

        if self._mock_mode:
            return self._mock_generate(prompt, job_id, artist_id, storage_dir)

        if not HTTPX_AVAILABLE:
            logger.warning("httpx not available — falling back to mock mode")
            return self._mock_generate(prompt, job_id, artist_id, storage_dir)

        suno_job_id = self._submit_job({
            "prompt": prompt,
            "tags": negative_prompt,
            "make_instrumental": make_instrumental,
            "model": model,
        })
        result = self._poll_until_done(suno_job_id)
        audio_url = result.get("audio_url", "")

        audio_file = ""
        if audio_url:
            dest = Path(storage_dir) / artist_id / "audio" / f"{job_id}_raw.mp3"
            dest.parent.mkdir(parents=True, exist_ok=True)
            audio_file = self._download_audio(audio_url, dest)

        return {
            "suno_job_id": suno_job_id,
            "audio_url": audio_url,
            "audio_file": audio_file,
            "duration": result.get("duration", 0.0),
            "status": "complete",
            "provider": "suno",
            "raw_response": result,
        }

    def _submit_job(self, payload: dict) -> str:
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        with httpx.Client(timeout=30) as client:
            resp = client.post(f"{SUNO_BASE_URL}/generate", json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            # Suno returns a list of clips; take the first job ID
            if isinstance(data, list) and data:
                return data[0].get("id", "")
            if isinstance(data, dict):
                return data.get("id", "")
            raise RuntimeError(f"Unexpected Suno response shape: {data}")

    def _poll_until_done(
        self,
        suno_job_id: str,
        max_wait_seconds: int = 600,
        initial_interval: int = 15,
    ) -> dict[str, Any]:
        headers = {"Authorization": f"Bearer {self._api_key}"}
        interval = initial_interval
        elapsed = 0

        while elapsed < max_wait_seconds:
            # Check local webhook file first (avoids unnecessary HTTP polls)
            webhook_path = Path(f"storage/webhooks/{suno_job_id}.json")
            if webhook_path.exists():
                try:
                    return json.loads(webhook_path.read_text())
                except json.JSONDecodeError:
                    pass

            with httpx.Client(timeout=30) as client:
                resp = client.get(
                    f"{SUNO_BASE_URL}/feed/",
                    params={"ids": suno_job_id},
                    headers=headers,
                )
                resp.raise_for_status()
                items = resp.json()
                item = items[0] if isinstance(items, list) and items else {}
                status = item.get("status", "")
                logger.info(f"Suno [{suno_job_id}] status={status} elapsed={elapsed}s")

                if status == "complete":
                    return item
                if status in ("error", "failed"):
                    raise RuntimeError(f"Suno generation failed: {item}")

            time.sleep(interval)
            elapsed += interval
            interval = min(interval * 2, 60)  # cap at 60s

        raise TimeoutError(f"Suno job {suno_job_id} did not complete within {max_wait_seconds}s")

    def _download_audio(self, url: str, dest_path: Path) -> str:
        with httpx.Client(timeout=120, follow_redirects=True) as client:
            with client.stream("GET", url) as resp:
                resp.raise_for_status()
                with open(dest_path, "wb") as f:
                    for chunk in resp.iter_bytes(chunk_size=8192):
                        f.write(chunk)
        logger.info(f"Audio downloaded → {dest_path}")
        return str(dest_path)

    def _mock_generate(
        self, prompt: str, job_id: str, artist_id: str, storage_dir: str
    ) -> dict[str, Any]:
        mock_path = Path(MOCK_AUDIO_PATH)
        if not mock_path.exists():
            logger.warning(f"Mock audio not found at {mock_path}. Run: scripts/create_mock_audio.sh")
        return {
            "suno_job_id": f"MOCK_{job_id[:8]}",
            "audio_url": "",
            "audio_file": str(mock_path) if mock_path.exists() else "",
            "duration": 210.0,
            "status": "complete",
            "provider": "mock",
            "prompt_used": prompt[:100],
        }
