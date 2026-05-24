"""FastAPI orchestration entry point."""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from orchestrator.pipeline_runner import PipelineRunner

app = FastAPI(
    title="Aarav AI Music — Orchestrator",
    description="Pipeline orchestration API for Aarav & Aarohi AI Music ecosystem",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

runner = PipelineRunner()


class PipelineRequest(BaseModel):
    artist_id: str = Field(..., pattern="^(aarav|aarohi)$")
    theme: str = Field(default="heartbreak_rain")
    language: str | None = Field(default=None)
    song_type: str = Field(default="full_song")
    emotion_intensity: int = Field(default=7, ge=1, le=10)
    title_hint: str = Field(default="")
    genre_preference: str = Field(default="")


@app.get("/health")
def health():
    return {"status": "ok", "service": "aarav-ai-music-orchestrator"}


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
    import json
    from pathlib import Path
    config_path = Path("config/artists") / f"{artist_id}.json"
    if not config_path.exists():
        raise HTTPException(status_code=404, detail=f"Artist '{artist_id}' not found")
    return json.loads(config_path.read_text())
