"""Pipeline Runner — orchestrates agents in sequence for Phase 1 MVP."""

import json
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from agents.base_agent import AgentStatus
from agents.lyrics import LyricsAgent
from agents.metadata import MetadataAgent
from agents.music_prompt import MusicPromptAgent

logger = logging.getLogger(__name__)

CONFIG_DIR = Path(__file__).parent.parent / "config"


class PipelineRunner:
    """Phase 1 linear pipeline: Lyrics → Music Prompt + Metadata → done.

    Phase 2 will extend this with Visual Prompt, Shorts, Branding,
    Publishing agents and an async event-bus orchestration model.
    """

    def __init__(self, gemini_client=None, firestore_client=None):
        self._gemini = gemini_client
        self._db = firestore_client
        self._lyrics_agent = LyricsAgent(gemini_client=gemini_client)
        self._music_prompt_agent = MusicPromptAgent(gemini_client=gemini_client)
        self._metadata_agent = MetadataAgent(gemini_client=gemini_client)

    def run(
        self,
        artist_id: str,
        theme: str,
        language: str | None = None,
        song_type: str = "full_song",
        emotion_intensity: int = 7,
        title_hint: str = "",
        genre_preference: str = "",
        job_id: str | None = None,
    ) -> dict[str, Any]:
        job_id = job_id or str(uuid.uuid4())
        started_at = datetime.now(timezone.utc).isoformat()

        job_record = {
            "job_id": job_id,
            "artist_id": artist_id,
            "status": "in_progress",
            "current_step": "lyrics",
            "steps": {},
            "error_log": [],
            "started_at": started_at,
        }
        self._persist_job(job_record)

        logger.info(f"[{job_id}] Pipeline starting | artist={artist_id} theme={theme}")

        # ── Step 1: Lyrics ──────────────────────────────────────────────────
        lyrics_result = self._lyrics_agent.run(
            artist_id=artist_id,
            job_id=job_id,
            context_payload={
                "theme": theme,
                "language": language,
                "song_type": song_type,
                "emotion_intensity": emotion_intensity,
                "title_hint": title_hint,
            },
        )
        job_record["steps"]["lyrics"] = lyrics_result.to_dict()

        if lyrics_result.status != AgentStatus.COMPLETED:
            return self._fail_job(job_record, "lyrics", lyrics_result.error)

        lyrics_output = lyrics_result.result_payload
        song_title = (
            lyrics_output.get("suggested_titles", ["Untitled"])[0]
        )
        logger.info(f"[{job_id}] Lyrics complete | title='{song_title}'")

        # ── Step 2: Music Prompt ────────────────────────────────────────────
        music_result = self._music_prompt_agent.run(
            artist_id=artist_id,
            job_id=job_id,
            context_payload={
                "lyrics_output": lyrics_output,
                "genre_preference": genre_preference,
                "platform_target": "suno",
            },
        )
        job_record["steps"]["music_prompt"] = music_result.to_dict()

        if music_result.status != AgentStatus.COMPLETED:
            return self._fail_job(job_record, "music_prompt", music_result.error)

        music_prompt_output = music_result.result_payload
        logger.info(f"[{job_id}] Music prompt complete")

        # ── Step 3: Metadata ────────────────────────────────────────────────
        metadata_result = self._metadata_agent.run(
            artist_id=artist_id,
            job_id=job_id,
            context_payload={
                "lyrics_output": lyrics_output,
                "music_prompt_output": music_prompt_output,
                "song_title": song_title,
                "platform_target": "youtube",
            },
        )
        job_record["steps"]["metadata"] = metadata_result.to_dict()

        if metadata_result.status != AgentStatus.COMPLETED:
            return self._fail_job(job_record, "metadata", metadata_result.error)

        metadata_output = metadata_result.result_payload
        logger.info(f"[{job_id}] Metadata complete | seo_score={metadata_output.get('seo_score')}")

        # ── Finalize ────────────────────────────────────────────────────────
        job_record["status"] = "completed_phase1"
        job_record["current_step"] = "awaiting_media_generation"
        job_record["completed_at"] = datetime.now(timezone.utc).isoformat()

        pipeline_output = {
            "job_id": job_id,
            "artist_id": artist_id,
            "song_title": song_title,
            "status": "phase1_complete",
            "lyrics": lyrics_output,
            "music_prompts": music_prompt_output,
            "metadata": metadata_output,
            "next_steps": [
                "Submit suno_prompt to Suno API → store audio_url",
                "Submit video prompts to Veo/Runway API → store video_url",
                "Run FFmpeg media processing",
                "Run Shorts Agent",
                "Run Branding Validation",
                "Human approval gate",
                "Publishing Agent → YouTube upload",
            ],
        }

        self._persist_job(job_record)
        self._persist_song_draft(artist_id, job_id, song_title, pipeline_output)

        logger.info(f"[{job_id}] Phase 1 pipeline complete ✓")
        return pipeline_output

    def _fail_job(self, job_record: dict, failed_step: str, error: str) -> dict:
        job_record["status"] = "failed"
        job_record["current_step"] = failed_step
        job_record["error_log"].append({"step": failed_step, "error": error})
        job_record["failed_at"] = datetime.now(timezone.utc).isoformat()
        self._persist_job(job_record)
        logger.error(f"[{job_record['job_id']}] Pipeline failed at step '{failed_step}': {error}")
        return {
            "job_id": job_record["job_id"],
            "status": "failed",
            "failed_step": failed_step,
            "error": error,
        }

    def _persist_job(self, job_record: dict) -> None:
        if self._db:
            try:
                self._db.collection("pipeline_jobs").document(job_record["job_id"]).set(
                    job_record, merge=True
                )
            except Exception as e:
                logger.warning(f"Firestore job persist failed: {e}")
        else:
            log_path = Path("storage") / "pipeline_jobs" / f"{job_record['job_id']}.json"
            log_path.parent.mkdir(parents=True, exist_ok=True)
            log_path.write_text(json.dumps(job_record, indent=2))

    def _persist_song_draft(
        self,
        artist_id: str,
        job_id: str,
        song_title: str,
        pipeline_output: dict,
    ) -> None:
        if self._db:
            try:
                import uuid as _uuid
                song_id = str(_uuid.uuid4())
                self._db.collection("songs").document(song_id).set(
                    {
                        "song_id": song_id,
                        "artist_id": artist_id,
                        "title": song_title,
                        "status": "draft",
                        "pipeline_job_id": job_id,
                        "lyrics": pipeline_output.get("lyrics", {}),
                        "metadata": pipeline_output.get("metadata", {}),
                        "generation_params": {
                            "suno_prompt": pipeline_output.get("music_prompts", {}).get("suno_prompt", ""),
                            "udio_prompt": pipeline_output.get("music_prompts", {}).get("udio_prompt", ""),
                        },
                        "created_at": datetime.now(timezone.utc).isoformat(),
                    }
                )
            except Exception as e:
                logger.warning(f"Firestore song draft persist failed: {e}")
        else:
            out_path = Path("storage") / artist_id / "songs" / f"{job_id}_draft.json"
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(json.dumps(pipeline_output, indent=2, ensure_ascii=False))
