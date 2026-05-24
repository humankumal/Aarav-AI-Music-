"""YouTube Data API v3 adapter — handles upload, thumbnail, chapters, scheduling."""

import logging
import os
import time
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

try:
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    GOOGLE_API_AVAILABLE = True
except ImportError:
    GOOGLE_API_AVAILABLE = False
    logger.warning("google-api-python-client not installed")

YOUTUBE_SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube",
]

UPLOAD_CHUNK_SIZE = 256 * 1024  # 256 KB resumable upload chunks


class YouTubeAdapter:
    def __init__(self, credentials_path: str | None = None, token_path: str | None = None):
        self._credentials_path = credentials_path or os.environ.get("YOUTUBE_CREDENTIALS_PATH", "")
        self._token_path = token_path or os.environ.get("YOUTUBE_TOKEN_PATH", "")
        self._service = None

    def _get_service(self):
        if self._service:
            return self._service
        if not GOOGLE_API_AVAILABLE:
            raise RuntimeError("google-api-python-client is not installed")

        creds = None
        if self._token_path and Path(self._token_path).exists():
            creds = Credentials.from_authorized_user_file(self._token_path, YOUTUBE_SCOPES)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                raise RuntimeError(
                    f"Valid YouTube OAuth token not found at '{self._token_path}'. "
                    "Run the OAuth flow to generate a token."
                )

        self._service = build("youtube", "v3", credentials=creds)
        return self._service

    def upload_video(
        self,
        video_path: str,
        title: str,
        description: str,
        tags: list[str],
        thumbnail_path: str | None = None,
        publish_at: str | None = None,
        category_id: str = "10",
        made_for_kids: bool = False,
        notify_subscribers: bool = True,
        playlist_id: str | None = None,
    ) -> dict[str, Any]:
        service = self._get_service()

        privacy_status = "private" if publish_at else "public"

        body = {
            "snippet": {
                "title": title[:100],
                "description": description[:5000],
                "tags": tags[:500],
                "categoryId": category_id,
                "defaultLanguage": "hi",
            },
            "status": {
                "privacyStatus": privacy_status,
                "madeForKids": made_for_kids,
                "selfDeclaredMadeForKids": made_for_kids,
            },
        }

        if publish_at:
            body["status"]["publishAt"] = publish_at
            body["status"]["privacyStatus"] = "private"

        media = MediaFileUpload(
            video_path,
            chunksize=UPLOAD_CHUNK_SIZE,
            resumable=True,
            mimetype="video/mp4",
        )

        logger.info(f"Starting YouTube upload: '{title}'")
        request = service.videos().insert(
            part="snippet,status",
            body=body,
            media_body=media,
            notifySubscribers=notify_subscribers if not publish_at else False,
        )

        response = None
        while response is None:
            status, response = request.next_chunk()
            if status:
                progress = int(status.progress() * 100)
                logger.info(f"Upload progress: {progress}%")

        video_id = response["id"]
        logger.info(f"Upload complete — video_id={video_id}")

        if thumbnail_path and Path(thumbnail_path).exists():
            self.set_thumbnail(video_id, thumbnail_path)

        if playlist_id:
            self.add_to_playlist(video_id, playlist_id)

        return {
            "video_id": video_id,
            "url": f"https://www.youtube.com/watch?v={video_id}",
            "title": title,
            "privacy_status": privacy_status,
            "publish_at": publish_at,
        }

    def set_thumbnail(self, video_id: str, thumbnail_path: str) -> None:
        service = self._get_service()
        try:
            service.thumbnails().set(
                videoId=video_id,
                media_body=MediaFileUpload(thumbnail_path, mimetype="image/jpeg"),
            ).execute()
            logger.info(f"Thumbnail set for video_id={video_id}")
        except Exception as e:
            logger.error(f"Failed to set thumbnail for {video_id}: {e}")

    def update_chapters(self, video_id: str, description_with_chapters: str) -> None:
        service = self._get_service()
        try:
            service.videos().update(
                part="snippet",
                body={
                    "id": video_id,
                    "snippet": {"description": description_with_chapters},
                },
            ).execute()
            logger.info(f"Chapters updated for video_id={video_id}")
        except Exception as e:
            logger.error(f"Failed to update chapters for {video_id}: {e}")

    def add_to_playlist(self, video_id: str, playlist_id: str) -> None:
        service = self._get_service()
        try:
            service.playlistItems().insert(
                part="snippet",
                body={
                    "snippet": {
                        "playlistId": playlist_id,
                        "resourceId": {
                            "kind": "youtube#video",
                            "videoId": video_id,
                        },
                    }
                },
            ).execute()
            logger.info(f"Video {video_id} added to playlist {playlist_id}")
        except Exception as e:
            logger.error(f"Failed to add to playlist: {e}")

    def schedule_publish(self, video_id: str, publish_at_iso: str) -> None:
        service = self._get_service()
        try:
            service.videos().update(
                part="status",
                body={
                    "id": video_id,
                    "status": {
                        "privacyStatus": "private",
                        "publishAt": publish_at_iso,
                    },
                },
            ).execute()
            logger.info(f"Video {video_id} scheduled for {publish_at_iso}")
        except Exception as e:
            logger.error(f"Failed to schedule video {video_id}: {e}")

    def get_video_status(self, video_id: str) -> dict[str, Any]:
        service = self._get_service()
        response = service.videos().list(
            part="status,statistics",
            id=video_id,
        ).execute()
        if response.get("items"):
            item = response["items"][0]
            return {
                "video_id": video_id,
                "privacy_status": item.get("status", {}).get("privacyStatus"),
                "upload_status": item.get("status", {}).get("uploadStatus"),
                "statistics": item.get("statistics", {}),
            }
        return {"video_id": video_id, "error": "not_found"}
