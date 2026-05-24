"""Google Lyria music generation client via Vertex AI.

Replaces SunoClient. Uses the same interface so pipeline_runner.py
calls generate_song() identically — only the provider changes.

Auth: GOOGLE_APPLICATION_CREDENTIALS service account (already in .env.example).
No new API key needed — uses the same GCP project as Gemini and Firebase.
"""

import json
import logging
import os
import subprocess
import uuid
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

MOCK_AUDIO_PATH = "storage/mock_audio/silence_3min.mp3"

# Lyria supports up to 30s per call; we concatenate segments for longer songs
LYRIA_MAX_SEGMENT_SECONDS = 30
LYRIA_MODEL = "lyria-002"


class LyriaClient:
    """Client for Google DeepMind Lyria via Vertex AI Prediction API.

    Falls back to mock mode automatically when GOOGLE_CLOUD_PROJECT is absent,
    matching the pattern of other clients in this codebase.
    """

    def __init__(
        self,
        project_id: str | None = None,
        location: str = "us-central1",
        mock_mode: bool = False,
    ):
        self._project_id = project_id or os.environ.get("GOOGLE_CLOUD_PROJECT", "")
        self._location = location
        self._mock_mode = mock_mode or not self._project_id
        self._endpoint = (
            f"projects/{self._project_id}/locations/{self._location}"
            f"/publishers/google/models/{LYRIA_MODEL}"
        )

        if self._mock_mode:
            logger.info("LyriaClient: running in mock mode (no GOOGLE_CLOUD_PROJECT)")
        else:
            self._verify_dependencies()

    def generate_song(
        self,
        prompt: str,
        negative_prompt: str = "",
        duration_seconds: int = 210,
        guidance_scale: float = 3.0,
        job_id: str | None = None,
        artist_id: str = "aarav",
        storage_dir: str = "storage",
    ) -> dict[str, Any]:
        """Generate a full song. For durations > 30s, makes multiple Lyria calls
        and concatenates segments into one MP3.

        Returns dict with keys: lyria_job_id, audio_url, audio_file,
        duration, status, provider.
        """
        job_id = job_id or str(uuid.uuid4())

        if self._mock_mode:
            return self._mock_generate(prompt, job_id, artist_id, storage_dir)

        segments_needed = max(1, -(-duration_seconds // LYRIA_MAX_SEGMENT_SECONDS))
        logger.info(f"Lyria: generating {segments_needed} segment(s) for {duration_seconds}s song")

        segment_paths = []
        out_dir = Path(storage_dir) / artist_id / "audio"
        out_dir.mkdir(parents=True, exist_ok=True)

        for i in range(segments_needed):
            seg_duration = min(LYRIA_MAX_SEGMENT_SECONDS, duration_seconds - i * LYRIA_MAX_SEGMENT_SECONDS)
            wav_bytes = self._call_vertex_api(
                prompt=prompt,
                negative_prompt=negative_prompt,
                duration_seconds=seg_duration,
                guidance_scale=guidance_scale,
            )
            seg_wav = out_dir / f"{job_id}_seg_{i}.wav"
            seg_wav.write_bytes(wav_bytes)
            segment_paths.append(str(seg_wav))

        raw_mp3 = str(out_dir / f"{job_id}_raw.mp3")
        if len(segment_paths) == 1:
            self._wav_to_mp3(segment_paths[0], raw_mp3)
        else:
            concatenated_wav = str(out_dir / f"{job_id}_concat.wav")
            self._concatenate_wavs(segment_paths, concatenated_wav)
            self._wav_to_mp3(concatenated_wav, raw_mp3)
            # Clean up intermediate files
            for p in segment_paths:
                Path(p).unlink(missing_ok=True)
            Path(concatenated_wav).unlink(missing_ok=True)

        logger.info(f"Lyria generation complete → {raw_mp3}")
        return {
            "lyria_job_id": job_id,
            "audio_url": "",
            "audio_file": raw_mp3,
            "duration": float(duration_seconds),
            "status": "complete",
            "provider": "lyria",
            "segments_generated": segments_needed,
        }

    # ── Vertex AI API call ────────────────────────────────────────────────────

    def _call_vertex_api(
        self,
        prompt: str,
        negative_prompt: str,
        duration_seconds: int,
        guidance_scale: float,
    ) -> bytes:
        """Call Vertex AI Lyria prediction endpoint and return raw WAV bytes."""
        try:
            import google.auth
            import google.auth.transport.requests
            import urllib.request as urlreq

            creds, _ = google.auth.default(
                scopes=["https://www.googleapis.com/auth/cloud-platform"]
            )
            creds.refresh(google.auth.transport.requests.Request())
            token = creds.token
        except Exception as e:
            raise RuntimeError(f"GCP auth failed: {e}")

        endpoint_url = (
            f"https://{self._location}-aiplatform.googleapis.com/v1/"
            f"{self._endpoint}:predict"
        )

        payload = json.dumps({
            "instances": [{
                "prompt": prompt,
                "negative_prompt": negative_prompt,
                "duration_seconds": duration_seconds,
                "guidance_scale": guidance_scale,
            }]
        }).encode("utf-8")

        req = urlreq.Request(
            endpoint_url,
            data=payload,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            method="POST",
        )

        try:
            with urlreq.urlopen(req, timeout=120) as resp:
                result = json.loads(resp.read())
        except Exception as e:
            raise RuntimeError(f"Lyria API call failed: {e}")

        # Vertex AI returns base64-encoded audio in predictions[0]["bytesBase64Encoded"]
        import base64
        predictions = result.get("predictions", [])
        if not predictions:
            raise RuntimeError(f"Lyria returned no predictions: {result}")

        audio_b64 = predictions[0].get("bytesBase64Encoded", "")
        if not audio_b64:
            raise RuntimeError("Lyria prediction missing bytesBase64Encoded field")

        return base64.b64decode(audio_b64)

    # ── Audio format helpers ──────────────────────────────────────────────────

    def _wav_to_mp3(self, wav_path: str, mp3_path: str) -> None:
        """Convert WAV to MP3 using FFmpeg."""
        cmd = [
            "ffmpeg", "-i", wav_path,
            "-codec:a", "libmp3lame", "-qscale:a", "2",
            "-y", mp3_path,
        ]
        result = subprocess.run(cmd, capture_output=True)
        if result.returncode != 0:
            raise RuntimeError(f"WAV→MP3 conversion failed: {result.stderr[-300:]}")

    def _concatenate_wavs(self, wav_paths: list[str], output_path: str) -> None:
        """Concatenate multiple WAV segments into one via FFmpeg concat demuxer."""
        list_file = Path(output_path).with_suffix(".txt")
        list_file.write_text("\n".join(f"file '{p}'" for p in wav_paths))
        cmd = [
            "ffmpeg",
            "-f", "concat", "-safe", "0",
            "-i", str(list_file),
            "-c", "copy",
            "-y", output_path,
        ]
        result = subprocess.run(cmd, capture_output=True)
        list_file.unlink(missing_ok=True)
        if result.returncode != 0:
            raise RuntimeError(f"WAV concatenation failed: {result.stderr[-300:]}")

    # ── Mock ──────────────────────────────────────────────────────────────────

    def _mock_generate(
        self, prompt: str, job_id: str, artist_id: str, storage_dir: str
    ) -> dict[str, Any]:
        mock_path = Path(MOCK_AUDIO_PATH)
        if not mock_path.exists():
            logger.warning(f"Mock audio not found at {mock_path}")
        return {
            "lyria_job_id": f"MOCK_{job_id[:8]}",
            "audio_url": "",
            "audio_file": str(mock_path) if mock_path.exists() else "",
            "duration": 210.0,
            "status": "complete",
            "provider": "mock",
            "prompt_used": prompt[:120],
        }

    # ── Dependency check ──────────────────────────────────────────────────────

    def _verify_dependencies(self) -> None:
        try:
            import google.auth  # noqa
        except ImportError:
            raise ImportError(
                "google-auth is not installed. Run: pip install google-auth"
            )
