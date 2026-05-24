"""Pipeline Runner — Phase 1 + Phase 2 orchestration."""

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
from agents.publishing import PublishingAgent
from agents.shorts import ShortsAgent
from media_processing.lyric_video_generator import LyricVideoGenerator
from media_processing.thumbnail_generator import ThumbnailGenerator

logger = logging.getLogger(__name__)

CONFIG_DIR = Path(__file__).parent.parent / "config"


class PipelineRunner:
    """Full pipeline: Lyrics → MusicPrompt → Metadata (Phase 1)
    then: Suno → Normalize → LyricVideo → Thumbnail → Shorts → Publish (Phase 2).

    Calling run() alone gives Phase 1 output (prompts + metadata, no media).
    Calling run_full() runs both phases end-to-end.
    """

    def __init__(
        self,
        gemini_client=None,
        firestore_client=None,
        suno_client=None,
        ffmpeg_processor=None,
        require_approval: bool = True,
        mock_mode: bool = False,
    ):
        self._gemini = gemini_client
        self._db = firestore_client
        self._suno = suno_client
        self._ffmpeg = ffmpeg_processor
        self._mock_mode = mock_mode

        # Phase 1 agents
        self._lyrics_agent = LyricsAgent(gemini_client=gemini_client)
        self._music_prompt_agent = MusicPromptAgent(gemini_client=gemini_client)
        self._metadata_agent = MetadataAgent(gemini_client=gemini_client)

        # Phase 2 agents
        self._shorts_agent = ShortsAgent(ffmpeg_processor=ffmpeg_processor, mock_mode=mock_mode)
        self._publishing_agent = PublishingAgent(
            youtube_adapter=None,
            firestore_client=firestore_client,
            require_approval=require_approval,
            mock_mode=mock_mode,
        )
        self._lyric_video_gen = LyricVideoGenerator(
            ffmpeg_processor=ffmpeg_processor, output_dir="storage"
        )
        self._thumbnail_gen = ThumbnailGenerator(output_dir="storage")

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

    # ── Phase 2 ───────────────────────────────────────────────────────────────

    def run_phase2(
        self,
        phase1_output: dict,
        publish_at: str | None = None,
        shorts_count: int = 3,
        burn_captions: bool = False,
    ) -> dict[str, Any]:
        """Extend a Phase 1 result with audio generation, lyric video, thumbnail,
        Shorts, and YouTube publishing.  Each step is error-isolated so a Shorts
        failure does not block the upload.
        """
        job_id = phase1_output["job_id"]
        artist_id = phase1_output["artist_id"]
        song_title = phase1_output["song_title"]
        lyrics_output = phase1_output["lyrics"]
        music_prompts = phase1_output["music_prompts"]
        metadata_output = phase1_output["metadata"]

        artist_config = self._lyrics_agent.load_artist_config(artist_id)

        job_record = self._load_job(job_id) or {
            "job_id": job_id,
            "artist_id": artist_id,
            "status": "in_progress_phase2",
            "steps": phase1_output.get("_steps", {}),
            "error_log": [],
        }
        job_record["status"] = "in_progress_phase2"
        job_record["current_step"] = "suno_generation"

        # ── Step 4: Suno audio generation ────────────────────────────────────
        suno_client = self._suno
        if suno_client is None:
            from integrations.suno_client import SunoClient
            suno_client = SunoClient()

        try:
            suno_result = suno_client.generate_song(
                prompt=music_prompts.get("suno_prompt", ""),
                negative_prompt=music_prompts.get("negative_prompt", ""),
                job_id=job_id,
                artist_id=artist_id,
            )
            raw_audio = suno_result.get("audio_file", "")
            job_record["steps"]["suno_generation"] = suno_result
            logger.info(f"[{job_id}] Suno complete | provider={suno_result.get('provider')}")
        except Exception as e:
            return self._fail_job(job_record, "suno_generation", str(e))

        # ── Step 5: Audio normalization ───────────────────────────────────────
        normalized_audio = raw_audio
        if raw_audio and Path(raw_audio).exists() and self._ffmpeg:
            try:
                norm_path = str(Path(raw_audio).with_name(f"{job_id}_normalized.mp3"))
                normalized_audio = self._ffmpeg.normalize_audio(raw_audio, norm_path)
                job_record["steps"]["audio_normalize"] = {"output": normalized_audio}
            except Exception as e:
                logger.warning(f"[{job_id}] Audio normalize failed (continuing): {e}")
                normalized_audio = raw_audio

        audio_duration = 210.0
        if self._ffmpeg and normalized_audio and Path(normalized_audio).exists():
            audio_duration = self._ffmpeg.get_duration(normalized_audio)

        # ── Step 6: Lyric video ───────────────────────────────────────────────
        job_record["current_step"] = "lyric_video"
        lyric_video_path = ""
        try:
            lyric_video_path = self._lyric_video_gen.generate(
                artist_id=artist_id,
                artist_config=artist_config,
                lyrics_text=lyrics_output.get("lyrics_text", ""),
                audio_path=normalized_audio or "storage/mock_audio/silence_3min.mp3",
                job_id=job_id,
                video_type="full",
                mock_mode=self._mock_mode,
            )
            job_record["steps"]["lyric_video"] = {"output": lyric_video_path}
            logger.info(f"[{job_id}] Lyric video → {lyric_video_path}")
        except Exception as e:
            logger.warning(f"[{job_id}] Lyric video failed (continuing): {e}")
            job_record["error_log"].append({"step": "lyric_video", "error": str(e)})

        # ── Step 7: Thumbnail ─────────────────────────────────────────────────
        job_record["current_step"] = "thumbnail"
        thumbnail_path = ""
        try:
            thumbnail_path = self._thumbnail_gen.generate(
                artist_id=artist_id,
                artist_config=artist_config,
                song_title=song_title,
                hook_line=lyrics_output.get("hook_line", ""),
                mood_tags=lyrics_output.get("mood_tags", []),
                job_id=job_id,
            )
            job_record["steps"]["thumbnail"] = {"output": thumbnail_path}
            logger.info(f"[{job_id}] Thumbnail → {thumbnail_path}")
        except Exception as e:
            logger.warning(f"[{job_id}] Thumbnail failed (continuing): {e}")
            job_record["error_log"].append({"step": "thumbnail", "error": str(e)})

        # ── Step 8: Shorts ────────────────────────────────────────────────────
        job_record["current_step"] = "shorts"
        shorts_output: dict = {"clips": [], "total_clips": 0}
        try:
            shorts_result = self._shorts_agent.run(
                artist_id=artist_id,
                job_id=job_id,
                context_payload={
                    "lyrics_output": lyrics_output,
                    "audio_path": normalized_audio,
                    "video_path": lyric_video_path,
                    "audio_duration": audio_duration,
                    "shorts_count": shorts_count,
                    "burn_captions": burn_captions,
                },
            )
            if shorts_result.status == AgentStatus.COMPLETED:
                shorts_output = shorts_result.result_payload
            job_record["steps"]["shorts"] = shorts_result.to_dict()
            logger.info(f"[{job_id}] Shorts prepared: {shorts_output.get('total_clips', 0)} clips")
        except Exception as e:
            logger.warning(f"[{job_id}] Shorts agent failed (continuing): {e}")
            job_record["error_log"].append({"step": "shorts", "error": str(e)})

        # ── Step 9: Publishing ────────────────────────────────────────────────
        job_record["current_step"] = "publishing"
        pub_result = self._publishing_agent.run(
            artist_id=artist_id,
            job_id=job_id,
            context_payload={
                "video_path": lyric_video_path,
                "thumbnail_path": thumbnail_path,
                "metadata_output": metadata_output,
                "song_title": song_title,
                "publish_at": publish_at,
                "shorts_clips": shorts_output.get("clips", []),
            },
        )
        pub_payload = pub_result.result_payload

        if pub_payload.get("status") == "awaiting_approval":
            job_record["status"] = "awaiting_approval"
            self._persist_job(job_record)
            return {
                "job_id": job_id,
                "status": "awaiting_approval",
                "message": pub_payload.get("message", ""),
                "resume_endpoint": f"POST /pipeline/resume/{job_id}",
            }

        if pub_result.status != AgentStatus.COMPLETED:
            return self._fail_job(job_record, "publishing", pub_result.error or "unknown")

        job_record["steps"]["publishing"] = pub_result.to_dict()
        job_record["status"] = "completed_phase2"
        job_record["current_step"] = "done"
        job_record["completed_at"] = datetime.now(timezone.utc).isoformat()
        self._persist_job(job_record)

        phase2_output = {
            "job_id": job_id,
            "artist_id": artist_id,
            "song_title": song_title,
            "status": "phase2_complete",
            "audio_file": normalized_audio,
            "lyric_video": lyric_video_path,
            "thumbnail": thumbnail_path,
            "shorts": shorts_output.get("clips", []),
            "upload": pub_payload,
            "metadata": metadata_output,
        }
        logger.info(f"[{job_id}] Phase 2 pipeline complete ✓ → {pub_payload.get('url', 'mock')}")
        return phase2_output

    def run_full(
        self,
        artist_id: str,
        theme: str,
        language: str | None = None,
        song_type: str = "full_song",
        emotion_intensity: int = 7,
        title_hint: str = "",
        genre_preference: str = "",
        publish_at: str | None = None,
        shorts_count: int = 3,
        job_id: str | None = None,
    ) -> dict[str, Any]:
        """Convenience method: run Phase 1 then Phase 2 in sequence."""
        phase1 = self.run(
            artist_id=artist_id,
            theme=theme,
            language=language,
            song_type=song_type,
            emotion_intensity=emotion_intensity,
            title_hint=title_hint,
            genre_preference=genre_preference,
            job_id=job_id,
        )
        if phase1.get("status") == "failed":
            return phase1

        return self.run_phase2(
            phase1_output=phase1,
            publish_at=publish_at,
            shorts_count=shorts_count,
        )

    def run_from_step(self, job_id: str, from_step: str = "publishing") -> dict[str, Any]:
        """Resume a pipeline from a specific step.  Used for approval-gate unblocking."""
        job_record = self._load_job(job_id)
        if not job_record:
            return {"job_id": job_id, "status": "failed", "error": "Job record not found"}

        artist_id = job_record.get("artist_id", "")
        # Reconstruct minimal phase1 output from persisted job record
        steps = job_record.get("steps", {})

        lyrics_step = steps.get("lyrics", {}).get("result_payload", {})
        music_step = steps.get("music_prompt", {}).get("result_payload", {})
        metadata_step = steps.get("metadata", {}).get("result_payload", {})
        song_title = lyrics_step.get("suggested_titles", ["Untitled"])[0]

        phase1_output = {
            "job_id": job_id,
            "artist_id": artist_id,
            "song_title": song_title,
            "status": "phase1_complete",
            "lyrics": lyrics_step,
            "music_prompts": music_step,
            "metadata": metadata_step,
            "_steps": steps,
        }

        if from_step == "publishing":
            # Skip to publishing using already-generated media paths
            lyric_video_path = steps.get("lyric_video", {}).get("output", "")
            thumbnail_path = steps.get("thumbnail", {}).get("output", "")
            shorts_output = steps.get("shorts", {}).get("result_payload", {})

            pub_result = self._publishing_agent.run(
                artist_id=artist_id,
                job_id=job_id,
                context_payload={
                    "video_path": lyric_video_path,
                    "thumbnail_path": thumbnail_path,
                    "metadata_output": metadata_step,
                    "song_title": song_title,
                    "shorts_clips": shorts_output.get("clips", []),
                    "skip_approval": True,
                },
            )
            pub_payload = pub_result.result_payload
            job_record["steps"]["publishing"] = pub_result.to_dict()
            job_record["status"] = "completed_phase2"
            self._persist_job(job_record)
            return {"job_id": job_id, "status": "phase2_complete", "upload": pub_payload}

        # Default: re-run full Phase 2 from the top
        return self.run_phase2(phase1_output)

    def _load_job(self, job_id: str) -> dict | None:
        if self._db:
            try:
                doc = self._db.collection("pipeline_jobs").document(job_id).get()
                return doc.to_dict() if doc.exists else None
            except Exception:
                pass
        job_path = Path("storage") / "pipeline_jobs" / f"{job_id}.json"
        if job_path.exists():
            try:
                return json.loads(job_path.read_text())
            except Exception:
                pass
        return None

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
