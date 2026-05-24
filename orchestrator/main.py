"""FastAPI orchestration entry point — Phase 1 + Phase 2 endpoints."""

import json
import os
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from orchestrator.pipeline_runner import PipelineRunner

app = FastAPI(
    title="Aarav AI Music — Orchestrator",
    description="Pipeline orchestration API for Aarav & Aarohi AI Music ecosystem",
    version="0.2.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

runner = PipelineRunner(mock_mode=True)


# ── Request models ────────────────────────────────────────────────────────────

class PipelineRequest(BaseModel):
    artist_id: str = Field(..., pattern="^(aarav|aarohi)$")
    theme: str = Field(default="heartbreak_rain")
    language: str | None = Field(default=None)
    song_type: str = Field(default="full_song")
    emotion_intensity: int = Field(default=7, ge=1, le=10)
    title_hint: str = Field(default="")
    genre_preference: str = Field(default="")


class FullPipelineRequest(BaseModel):
    artist_id: str = Field(..., pattern="^(aarav|aarohi)$")
    theme: str = Field(default="heartbreak_rain")
    language: str | None = Field(default=None)
    song_type: str = Field(default="full_song")
    emotion_intensity: int = Field(default=7, ge=1, le=10)
    title_hint: str = Field(default="")
    genre_preference: str = Field(default="")
    publish_at: str | None = Field(default=None)
    shorts_count: int = Field(default=3, ge=0, le=5)
    burn_captions: bool = Field(default=False)
    skip_approval: bool = Field(default=False)


# ── Existing Phase 1 endpoint (unchanged) ────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "ok", "service": "aarav-ai-music-orchestrator", "version": "0.2.0"}


@app.post("/pipeline/run")
def run_pipeline(request: PipelineRequest):
    result = runner.run(
        artist_id=request.artist_id,
        theme=request.theme,
        language=request.language,
        song_type=request.song_type,
        emotion_intensity=request.emotion_intensity,
        title_hint=request.title_hint,
        genre_preference=request.genre_preference,
    )
    if result.get("status") == "failed":
        raise HTTPException(status_code=500, detail=result)
    return result


@app.get("/artists/{artist_id}/config")
def get_artist_config(artist_id: str):
    config_path = Path("config/artists") / f"{artist_id}.json"
    if not config_path.exists():
        raise HTTPException(status_code=404, detail=f"Artist '{artist_id}' not found")
    return json.loads(config_path.read_text())


# ── Phase 2 endpoints ─────────────────────────────────────────────────────────

@app.post("/pipeline/run_full")
def run_full_pipeline(request: FullPipelineRequest):
    """Full pipeline: Phase 1 (lyrics → prompts → metadata) + Phase 2 (audio → video → publish)."""
    result = runner.run_full(
        artist_id=request.artist_id,
        theme=request.theme,
        language=request.language,
        song_type=request.song_type,
        emotion_intensity=request.emotion_intensity,
        title_hint=request.title_hint,
        genre_preference=request.genre_preference,
        publish_at=request.publish_at,
        shorts_count=request.shorts_count,
    )
    if result.get("status") == "failed":
        raise HTTPException(status_code=500, detail=result)
    return result


@app.post("/pipeline/resume/{job_id}")
def resume_pipeline(job_id: str, from_step: str = "publishing"):
    """Resume a pipeline that was blocked at the approval gate."""
    result = runner.run_from_step(job_id=job_id, from_step=from_step)
    if result.get("status") == "failed":
        raise HTTPException(status_code=500, detail=result)
    return result


@app.post("/approvals/{job_id}/approve")
def approve_job(job_id: str, notes: str = ""):
    """Admin endpoint: mark a pipeline job as approved for publishing."""
    approval = {
        "job_id": job_id,
        "status": "approved",
        "reviewer": "admin",
        "notes": notes,
        "decided_at": datetime.now(timezone.utc).isoformat(),
    }
    approval_path = Path("storage") / "approvals" / f"{job_id}.json"
    approval_path.parent.mkdir(parents=True, exist_ok=True)
    approval_path.write_text(json.dumps(approval, indent=2))
    return {"job_id": job_id, "status": "approved", "message": f"POST /pipeline/resume/{job_id} to publish"}


@app.post("/approvals/{job_id}/reject")
def reject_job(job_id: str, notes: str = ""):
    approval = {
        "job_id": job_id,
        "status": "rejected",
        "reviewer": "admin",
        "notes": notes,
        "decided_at": datetime.now(timezone.utc).isoformat(),
    }
    approval_path = Path("storage") / "approvals" / f"{job_id}.json"
    approval_path.parent.mkdir(parents=True, exist_ok=True)
    approval_path.write_text(json.dumps(approval, indent=2))
    return {"job_id": job_id, "status": "rejected"}


@app.post("/suno/webhook")
def suno_webhook(payload: dict):
    """Suno completion callback — stores result so SunoClient stops polling."""
    suno_job_id = payload.get("id", "")
    if not suno_job_id:
        raise HTTPException(status_code=400, detail="Missing 'id' in payload")
    webhook_path = Path("storage") / "webhooks" / f"{suno_job_id}.json"
    webhook_path.parent.mkdir(parents=True, exist_ok=True)
    webhook_path.write_text(json.dumps(payload, indent=2))
    return {"received": True, "suno_job_id": suno_job_id}


@app.get("/uploads/{artist_id}")
def list_uploads(artist_id: str):
    """List upload receipts for an artist."""
    uploads_dir = Path("storage") / artist_id / "uploads"
    if not uploads_dir.exists():
        return []
    receipts = []
    for f in sorted(uploads_dir.glob("*.json"), reverse=True):
        try:
            receipts.append(json.loads(f.read_text()))
        except Exception:
            pass
    return receipts
