"""FastAPI orchestration entry point — Phase 1 + Phase 2 endpoints."""

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from agents.cover_song import CoverSongAgent
from orchestrator.pipeline_runner import PipelineRunner

app = FastAPI(
    title="Aarav AI Music — Orchestrator",
    description="Pipeline orchestration API for Aarav & Aarohi AI Music ecosystem",
    version="0.3.0",
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


@app.post("/music/webhook")
def music_webhook(payload: dict):
    """Music generation completion callback — stores result for async polling."""
    music_job_id = payload.get("id", "")
    if not music_job_id:
        raise HTTPException(status_code=400, detail="Missing 'id' in payload")
    webhook_path = Path("storage") / "webhooks" / f"{music_job_id}.json"
    webhook_path.parent.mkdir(parents=True, exist_ok=True)
    webhook_path.write_text(json.dumps(payload, indent=2))
    return {"received": True, "music_job_id": music_job_id}


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


# ── Cover Song request models ─────────────────────────────────────────────────

class CoverRunRequest(BaseModel):
    artist_id: str = Field(..., pattern="^(aarav|aarohi)$")
    song_id: str = Field(..., description="Catalog song_id e.g. 'ng_001' or 'mj_001'")
    catalog_type: str = Field(..., pattern="^(nepali|global)$")
    language: str | None = Field(default=None)
    emotion_intensity: int = Field(default=8, ge=1, le=10)
    publish_at: str | None = Field(default=None)
    shorts_count: int = Field(default=2, ge=0, le=5)


class CoverBatchRequest(BaseModel):
    artist_id: str = Field(..., pattern="^(aarav|aarohi)$")
    catalog_type: str = Field(..., pattern="^(nepali|global)$")
    song_ids: list[str] = Field(..., max_length=10, description="Up to 10 song_ids")
    emotion_intensity: int = Field(default=8, ge=1, le=10)


# ── Cover Song endpoints ──────────────────────────────────────────────────────

@app.post("/covers/run")
def run_cover(request: CoverRunRequest) -> dict[str, Any]:
    """Generate a single cover-inspired original song (Phase 1)."""
    result = runner.run_cover(
        artist_id=request.artist_id,
        song_id=request.song_id,
        catalog_type=request.catalog_type,
        language=request.language,
        emotion_intensity=request.emotion_intensity,
        publish_at=request.publish_at,
        shorts_count=request.shorts_count,
    )
    if result.get("status") == "failed":
        raise HTTPException(status_code=500, detail=result)
    return result


@app.post("/covers/batch")
def run_cover_batch(request: CoverBatchRequest) -> dict[str, Any]:
    """Generate up to 10 cover songs in sequence."""
    results = []
    errors = []
    for song_id in request.song_ids:
        result = runner.run_cover(
            artist_id=request.artist_id,
            song_id=song_id,
            catalog_type=request.catalog_type,
            emotion_intensity=request.emotion_intensity,
        )
        if result.get("status") == "failed":
            errors.append({"song_id": song_id, "error": result.get("error")})
        else:
            results.append(result)
    return {
        "total_requested": len(request.song_ids),
        "succeeded": len(results),
        "failed": len(errors),
        "results": results,
        "errors": errors,
    }


@app.get("/covers/catalog/{catalog_type}")
def get_cover_catalog(
    catalog_type: str,
    artist_id: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=100),
) -> dict[str, Any]:
    """Return paginated catalog entries. Optionally filter by reference artist_id."""
    if catalog_type not in ("nepali", "global"):
        raise HTTPException(status_code=400, detail="catalog_type must be 'nepali' or 'global'")

    covers_dir = Path("config/covers") / catalog_type
    index_path = covers_dir / "index.json"
    if not index_path.exists():
        raise HTTPException(status_code=404, detail=f"Catalog '{catalog_type}' not found")

    index = json.loads(index_path.read_text())
    all_songs: list[dict] = []

    for entry in index.get("artists", []):
        if artist_id and entry["reference_artist_id"] != artist_id:
            continue
        artist_file = covers_dir / entry["file"]
        if not artist_file.exists():
            continue
        artist_data = json.loads(artist_file.read_text())
        for song in artist_data.get("songs", []):
            all_songs.append(
                {
                    **song,
                    "reference_artist_id": artist_data["reference_artist_id"],
                    "reference_artist_name": artist_data["reference_artist_name"],
                    "catalog_type": catalog_type,
                }
            )

    total = len(all_songs)
    start = (page - 1) * per_page
    page_songs = all_songs[start : start + per_page]

    return {
        "catalog_type": catalog_type,
        "total": total,
        "page": page,
        "per_page": per_page,
        "songs": page_songs,
    }


@app.get("/covers/{song_id}/status")
def get_cover_status(song_id: str, artist_id: str = Query(...)) -> dict[str, Any]:
    """Return generation status for a specific cover song."""
    gen_path = Path("storage") / "cover_generations" / f"{song_id}_{artist_id}.json"
    if not gen_path.exists():
        # Song exists in catalog but hasn't been generated yet
        song_entry = CoverSongAgent.load_song_from_catalog(
            song_id, _infer_catalog_type(song_id)
        )
        if not song_entry:
            raise HTTPException(status_code=404, detail=f"song_id '{song_id}' not found")
        return {
            "song_id": song_id,
            "artist_id": artist_id,
            "status": "not_started",
            "reference_song_title": song_entry["title"],
            "reference_artist_name": song_entry["reference_artist_name"],
        }
    return json.loads(gen_path.read_text())


@app.get("/covers/{song_id}/draft")
def get_cover_draft(song_id: str, artist_id: str = Query(...)) -> dict[str, Any]:
    """Return the full pipeline draft (lyrics, metadata, anchors) for a generated cover."""
    gen_path = Path("storage") / "cover_generations" / f"{song_id}_{artist_id}.json"
    if not gen_path.exists():
        raise HTTPException(status_code=404, detail=f"No generation record for {song_id}/{artist_id}")

    gen_record = json.loads(gen_path.read_text())
    job_id = gen_record.get("job_id")
    if not job_id:
        raise HTTPException(status_code=404, detail="Generation record has no job_id")

    covers_dir = Path("storage") / artist_id / "covers"
    if covers_dir.exists():
        for draft_file in covers_dir.glob(f"{job_id}_draft.json"):
            return json.loads(draft_file.read_text())

    raise HTTPException(status_code=404, detail=f"Draft file not found for job {job_id}")


@app.get("/covers/{artist_id}/generated")
def list_generated_covers(
    artist_id: str,
    catalog_type: str | None = Query(default=None),
    status: str | None = Query(default=None),
) -> list[dict]:
    """List all cover_generations records for an artist."""
    gen_dir = Path("storage") / "cover_generations"
    if not gen_dir.exists():
        return []
    records = []
    for f in sorted(gen_dir.glob(f"*_{artist_id}.json"), reverse=True):
        try:
            record = json.loads(f.read_text())
            if catalog_type and record.get("catalog_type") != catalog_type:
                continue
            if status and record.get("status") != status:
                continue
            records.append(record)
        except Exception:
            pass
    return records


@app.get("/covers/stats")
def get_cover_stats() -> dict[str, Any]:
    """Aggregate stats: catalog size, generated counts, status breakdown."""
    nepali_total = _count_catalog_songs("nepali")
    global_total = _count_catalog_songs("global")

    gen_dir = Path("storage") / "cover_generations"
    status_counts: dict[str, int] = {}
    if gen_dir.exists():
        for f in gen_dir.glob("*.json"):
            try:
                record = json.loads(f.read_text())
                s = record.get("status", "unknown")
                status_counts[s] = status_counts.get(s, 0) + 1
            except Exception:
                pass

    return {
        "catalog_total": nepali_total + global_total,
        "nepali_catalog": nepali_total,
        "global_catalog": global_total,
        "generated": sum(status_counts.values()),
        "status_breakdown": status_counts,
    }


# ── Cover endpoint helpers ────────────────────────────────────────────────────

def _infer_catalog_type(song_id: str) -> str:
    """Heuristic: Nepali song IDs use known Nepali artist prefixes."""
    nepali_prefixes = {
        "ng_", "bra_", "al_", "pdp_", "rkd_", "ds_", "kd_", "sr_",
        "1974_", "yk_", "ap_", "bm_", "rl_", "sp_", "ss_", "srv_",
        "ber_", "acd_", "nkb_", "obb_",
    }
    for prefix in nepali_prefixes:
        if song_id.startswith(prefix):
            return "nepali"
    return "global"


def _count_catalog_songs(catalog_type: str) -> int:
    index_path = Path("config/covers") / catalog_type / "index.json"
    if not index_path.exists():
        return 0
    try:
        index = json.loads(index_path.read_text())
        return index.get("total_songs", 0)
    except Exception:
        return 0
