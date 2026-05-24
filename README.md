# Aarav AI Music Ecosystem

A fully autonomous AI-powered music entertainment ecosystem featuring two fictional AI artists:

| Artist | Identity | Sound |
|--------|----------|-------|
| **Aarav AI Music** | Mysterious, cinematic, emotionally deep male | Dark pop · Ambient trap · Cinematic Bollywood |
| **Aarohi AI Music** | Elegant, dreamy, spiritually rooted female | Spiritual folk pop · Cinematic female · Dream pop |

---

## Architecture

```
Frontend Dashboard (Next.js 14)
        ↓
Orchestration Core (FastAPI)
        ↓
┌───────────────────────────────┐
│  Lyrics → MusicPrompt         │  Phase 1 ✓
│         → Metadata            │
└───────────────────────────────┘
┌───────────────────────────────┐
│  VisualPrompt → Shorts        │  Phase 2
│  Branding → Publishing        │
└───────────────────────────────┘
```

**Full architecture doc:** See `/docs/architecture.md` (generated from planning phase).

---

## Quick Start

```bash
# 1. Clone and enter project
cd Aarav-AI-Music-

# 2. Set up Python environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 3. Configure environment
cp .env.example .env
# Edit .env — add GEMINI_API_KEY at minimum

# 4. Run Phase 1 pipeline smoke test (no API keys needed)
python3 scripts/test_pipeline.py

# 5. Start orchestrator API
uvicorn orchestrator.main:app --reload --port 8000
```

---

## Phase 1 — What Works Now

| Component | Status |
|-----------|--------|
| Artist config system (Aarav + Aarohi) | ✅ |
| Lyrics Agent (mock + Gemini) | ✅ |
| Music Prompt Agent (Suno + Udio prompts) | ✅ |
| Metadata Agent (YouTube SEO) | ✅ |
| Pipeline Runner (linear orchestrator) | ✅ |
| Local file persistence fallback | ✅ |
| FastAPI REST endpoint | ✅ |
| YouTube upload adapter | ✅ |
| FFmpeg media processor | ✅ |
| Smoke test suite | ✅ |

---

## Phase 2 — Next Up

- Visual Prompt Agent (Veo/Runway video prompts)
- Shorts Agent (viral clip automation)
- Branding Agent (visual consistency validation)
- Publishing Agent (YouTube upload automation)
- Aarohi AI Music full launch
- TikTok + Instagram adapters
- React frontend dashboard

---

## Folder Structure

```
/config         ← Artist profiles, pipeline configs, platform settings
/agents         ← 7 modular AI agents
/orchestrator   ← FastAPI pipeline runner
/integrations   ← Gemini, Suno, YouTube, Firebase clients
/media_processing ← FFmpeg audio/video processing
/backend        ← Node.js API server (Phase 2)
/frontend       ← Next.js dashboard (Phase 2)
/firebase       ← Firestore rules, indexes, Cloud Functions
/storage        ← Local dev asset mirror
/scripts        ← Utilities, smoke tests, seeding
```

---

## Artist Configs

Edit `config/artists/aarav.json` and `config/artists/aarohi.json` to customize:
- Personality, themes, emotional range
- Voice configuration (ElevenLabs)
- Visual style, color palette, brand rules
- Social profile IDs
- Upload schedule and SEO tags

---

## API

```
POST /pipeline/run
{
  "artist_id": "aarav",
  "theme": "heartbreak_rain",
  "language": "hinglish",
  "emotion_intensity": 8
}

GET /artists/{artist_id}/config
GET /health
```

---

## Monetization Roadmap

| Stream | Timeline |
|--------|----------|
| YouTube Partner Program | Month 3–4 |
| Spotify Streaming | Month 4–5 |
| Brand Partnerships | Month 6+ |
| Merchandise | Month 8+ |
| Music Licensing | Month 10+ |

Target: `$2,000–5,000/month` by Month 12 across both artists.

---

## AI Disclosure

All content is AI-generated with human creative direction. Every upload includes `#AIMusic` disclosure per YouTube's AI content policies.

---

*"A fully autonomous emotional AI music entertainment ecosystem."*
