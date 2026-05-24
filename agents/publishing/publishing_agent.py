"""Publishing Agent — assembles media package and executes YouTube upload."""

import json
import logging
import os
import uuid
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

from agents.base_agent import BaseAgent, AgentStatus

logger = logging.getLogger(__name__)

PLATFORMS_CONFIG_DIR = Path("config/platforms")
IST_OFFSET = timedelta(hours=5, minutes=30)

DAY_ORDER = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


class PublishingAgent(BaseAgent):
    def __init__(
        self,
        youtube_adapter=None,
        firestore_client=None,
        require_approval: bool = True,
        mock_mode: bool = False,
    ):
        super().__init__("PublishingAgent")
        self._youtube = youtube_adapter
        self._db = firestore_client
        self._require_approval = (
            require_approval
            and os.environ.get("REQUIRE_HUMAN_APPROVAL", "true").lower() != "false"
        )
        self._mock_mode = mock_mode or youtube_adapter is None

    def _execute(
        self,
        artist_id: str,
        artist_config: dict,
        context: dict[str, Any],
        job_id: str,
    ) -> dict[str, Any]:
        # Check approval gate first
        if self._require_approval and not context.get("skip_approval"):
            approval = self._check_approval_gate(job_id, artist_id)
            if approval != "approved":
                self.logger.info(f"[{job_id}] Awaiting human approval (status={approval})")
                return {
                    "status": "awaiting_approval",
                    "job_id": job_id,
                    "message": (
                        f"Approve at POST /approvals/{job_id}/approve "
                        f"or set REQUIRE_HUMAN_APPROVAL=false for testing"
                    ),
                }

        package = self._assemble_upload_package(artist_id, artist_config, context)

        if self._mock_mode:
            upload_result = self._mock_upload(package, job_id)
        else:
            upload_result = self._execute_upload(package, artist_config)

        self._write_upload_receipt(
            artist_id=artist_id,
            job_id=job_id,
            song_title=context.get("song_title", "Untitled"),
            upload_result=upload_result,
            package=package,
        )

        self.logger.info(
            f"[{job_id}] Published → {upload_result.get('url', 'mock')} "
            f"(status={upload_result.get('privacy_status', 'mock')})"
        )
        return upload_result

    # ── Approval gate ─────────────────────────────────────────────────────────

    def _check_approval_gate(self, job_id: str, artist_id: str) -> str:
        # Check Firestore first
        if self._db:
            try:
                doc = self._db.collection("approvals").document(job_id).get()
                if doc.exists:
                    return doc.to_dict().get("status", "pending")
            except Exception as e:
                self.logger.warning(f"Firestore approval check failed: {e}")

        # Fall back to local file
        approval_path = Path("storage") / "approvals" / f"{job_id}.json"
        if approval_path.exists():
            try:
                data = json.loads(approval_path.read_text())
                return data.get("status", "pending")
            except Exception:
                pass

        return "pending"

    # ── Package assembly ──────────────────────────────────────────────────────

    def _assemble_upload_package(
        self,
        artist_id: str,
        artist_config: dict,
        context: dict,
    ) -> dict[str, Any]:
        metadata = context.get("metadata_output", {})
        video_path = context.get("video_path", "")
        thumbnail_path = context.get("thumbnail_path", "")
        song_title = context.get("song_title", metadata.get("title", "Untitled"))

        yt_config = {}
        yt_config_path = PLATFORMS_CONFIG_DIR / "youtube.json"
        if yt_config_path.exists():
            yt_config = json.loads(yt_config_path.read_text())

        publish_at = context.get("publish_at") or self._calc_next_publish_time(artist_config)
        playlist_id = (
            artist_config.get("social_profiles", {}).get("youtube_main_playlist_id") or None
        )

        return {
            "video_path": video_path,
            "thumbnail_path": thumbnail_path if Path(thumbnail_path).exists() else None,
            "title": metadata.get("title", song_title),
            "description": metadata.get("description", ""),
            "tags": metadata.get("tags", []),
            "publish_at": publish_at,
            "playlist_id": playlist_id,
            "category_id": yt_config.get("category_id", "10"),
            "made_for_kids": yt_config.get("made_for_kids", False),
            "shorts_clips": context.get("shorts_clips", []),
            "artist_id": artist_id,
        }

    # ── Upload execution ──────────────────────────────────────────────────────

    def _execute_upload(self, package: dict, artist_config: dict) -> dict[str, Any]:
        if not Path(package["video_path"]).exists():
            raise FileNotFoundError(f"Video file not found: {package['video_path']}")

        result = self._youtube.upload_video(
            video_path=package["video_path"],
            title=package["title"],
            description=package["description"],
            tags=package["tags"],
            thumbnail_path=package.get("thumbnail_path"),
            publish_at=package.get("publish_at"),
            category_id=package.get("category_id", "10"),
            made_for_kids=package.get("made_for_kids", False),
            notify_subscribers=True,
            playlist_id=package.get("playlist_id"),
        )
        return result

    def _mock_upload(self, package: dict, job_id: str) -> dict[str, Any]:
        mock_id = f"MOCK_{job_id[:8].upper()}"
        return {
            "video_id": mock_id,
            "url": f"https://www.youtube.com/watch?v={mock_id}",
            "title": package["title"],
            "privacy_status": "private",
            "publish_at": package.get("publish_at"),
            "provider": "mock",
        }

    # ── Receipt writing ───────────────────────────────────────────────────────

    def _write_upload_receipt(
        self,
        artist_id: str,
        job_id: str,
        song_title: str,
        upload_result: dict,
        package: dict,
    ) -> None:
        upload_id = str(uuid.uuid4())
        receipt = {
            "upload_id": upload_id,
            "job_id": job_id,
            "artist_id": artist_id,
            "song_title": song_title,
            "platform": "youtube",
            "video_id": upload_result.get("video_id", ""),
            "url": upload_result.get("url", ""),
            "privacy_status": upload_result.get("privacy_status", "private"),
            "publish_at": upload_result.get("publish_at"),
            "thumbnail_path": package.get("thumbnail_path", ""),
            "video_path": package.get("video_path", ""),
            "metadata_title": package.get("title", ""),
            "status": "scheduled" if upload_result.get("publish_at") else "published",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        if self._db:
            try:
                self._db.collection("uploads").document(upload_id).set(receipt)
                return
            except Exception as e:
                self.logger.warning(f"Firestore receipt write failed: {e}")

        out_path = Path("storage") / artist_id / "uploads" / f"{job_id}_receipt.json"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(receipt, indent=2))

    # ── Schedule helper ───────────────────────────────────────────────────────

    def _calc_next_publish_time(self, artist_config: dict) -> str:
        schedule = artist_config.get("upload_schedule", {})
        preferred_days = schedule.get("preferred_days", ["Tuesday", "Thursday"])
        time_ist_str = schedule.get("preferred_time_ist", "15:30")

        now_utc = datetime.now(timezone.utc)
        now_ist = now_utc + IST_OFFSET
        h, m = map(int, time_ist_str.split(":"))
        today_idx = now_ist.weekday()

        for offset in range(1, 8):
            candidate_idx = (today_idx + offset) % 7
            day_name = DAY_ORDER[candidate_idx]
            if day_name in preferred_days:
                publish_ist = (now_ist + timedelta(days=offset)).replace(
                    hour=h, minute=m, second=0, microsecond=0
                )
                publish_utc = publish_ist - IST_OFFSET
                return publish_utc.strftime("%Y-%m-%dT%H:%M:%S.000Z")

        # Fallback: 48 hours from now
        return (now_utc + timedelta(hours=48)).strftime("%Y-%m-%dT%H:%M:%S.000Z")
