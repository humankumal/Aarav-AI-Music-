"""Sprint 1 smoke tests for the Cover Song pipeline.

Tests mock mode (no API keys required):
  1. Nepali song — Aarav
  2. Nepali song — Aarohi
  3. Global song — Aarav
  4. Global song — Aarohi
  5. Catalog loader — nepali index
  6. Catalog loader — global index
  7. Missing song_id returns None
  8. Catalog counts: 20 Nepali artists × 20 songs + 20 Global artists × 20 songs
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from agents.cover_song import CoverSongAgent
from agents.base_agent import AgentStatus

PASS = "\033[92mPASS\033[0m"
FAIL = "\033[91mFAIL\033[0m"

results = []


def check(name: str, condition: bool, detail: str = "") -> None:
    label = PASS if condition else FAIL
    suffix = f"  ({detail})" if detail else ""
    print(f"  [{label}] {name}{suffix}")
    results.append(condition)


# ── Agent mock tests ────────────────────────────────────────────────────────

print("\nCoverSongAgent — mock mode")
agent = CoverSongAgent(gemini_client=None)

# Test 1: Nepali / Aarav
r1 = agent.run(
    artist_id="aarav",
    job_id="cov_test_001",
    context_payload={
        "reference_song_title": "Euta Manche Ko",
        "reference_artist_name": "Narayan Gopal",
        "catalog_type": "nepali",
        "song_id": "ng_001",
    },
)
check("Nepali/Aarav — status COMPLETED", r1.status == AgentStatus.COMPLETED)
check("Nepali/Aarav — song_type cover_inspired", r1.result_payload.get("song_type") == "cover_inspired")
check("Nepali/Aarav — lyrics_are_original True", r1.result_payload.get("lyrics_are_original") is True)
check("Nepali/Aarav — hook_line present", bool(r1.result_payload.get("hook_line")))
check("Nepali/Aarav — suggested_titles list", isinstance(r1.result_payload.get("suggested_titles"), list))

# Test 2: Nepali / Aarohi
r2 = agent.run(
    artist_id="aarohi",
    job_id="cov_test_002",
    context_payload={
        "reference_song_title": "Resham Firiri",
        "reference_artist_name": "Aruna Lama",
        "catalog_type": "nepali",
        "song_id": "al_001",
    },
)
check("Nepali/Aarohi — status COMPLETED", r2.status == AgentStatus.COMPLETED)
check("Nepali/Aarohi — hook_line differs from Aarav", r2.result_payload.get("hook_line") != r1.result_payload.get("hook_line"))

# Test 3: Global / Aarav
r3 = agent.run(
    artist_id="aarav",
    job_id="cov_test_003",
    context_payload={
        "reference_song_title": "Billie Jean",
        "reference_artist_name": "Michael Jackson",
        "catalog_type": "global",
        "song_id": "mj_001",
    },
)
check("Global/Aarav — status COMPLETED", r3.status == AgentStatus.COMPLETED)
check("Global/Aarav — catalog_type preserved", r3.result_payload.get("catalog_type") == "global")

# Test 4: Global / Aarohi
r4 = agent.run(
    artist_id="aarohi",
    job_id="cov_test_004",
    context_payload={
        "reference_song_title": "Hello",
        "reference_artist_name": "Adele",
        "catalog_type": "global",
        "song_id": "ade_001",
    },
)
check("Global/Aarohi — status COMPLETED", r4.status == AgentStatus.COMPLETED)

# ── Catalog loader tests ────────────────────────────────────────────────────

print("\nCatalog loader")

ng = CoverSongAgent.load_song_from_catalog("ng_001", "nepali")
check("Nepali ng_001 found", ng is not None)
check("Nepali ng_001 title correct", ng and ng.get("title") == "Euta Manche Ko", ng.get("title") if ng else "None")
check("Nepali ng_001 artist correct", ng and ng.get("reference_artist_name") == "Narayan Gopal")

mj = CoverSongAgent.load_song_from_catalog("mj_001", "global")
check("Global mj_001 found", mj is not None)
check("Global mj_001 title correct", mj and mj.get("title") == "Billie Jean", mj.get("title") if mj else "None")

bts = CoverSongAgent.load_song_from_catalog("bts_020", "global")
check("Global bts_020 found", bts is not None)

missing = CoverSongAgent.load_song_from_catalog("xx_999", "nepali")
check("Missing song_id returns None", missing is None)

# ── Catalog integrity ───────────────────────────────────────────────────────

print("\nCatalog integrity")

covers_dir = ROOT / "config" / "covers"

for catalog_type, expected_artists, expected_songs in [("nepali", 20, 400), ("global", 20, 400)]:
    index_path = covers_dir / catalog_type / "index.json"
    index = json.loads(index_path.read_text())
    artist_count = len(index["artists"])
    check(f"{catalog_type} — {expected_artists} artists in index", artist_count == expected_artists, str(artist_count))

    total = 0
    broken = []
    for entry in index["artists"]:
        artist_file = covers_dir / catalog_type / entry["file"]
        if not artist_file.exists():
            broken.append(entry["file"])
            continue
        data = json.loads(artist_file.read_text())
        songs = data.get("songs", [])
        total += len(songs)
        if len(songs) != 20:
            broken.append(f"{entry['file']} has {len(songs)} songs (expected 20)")

    check(f"{catalog_type} — {expected_songs} total songs", total == expected_songs, str(total))
    check(f"{catalog_type} — no broken artist files", len(broken) == 0, ", ".join(broken) if broken else "")

# ── Result summary ──────────────────────────────────────────────────────────

passed = sum(results)
total = len(results)
print(f"\n{'─' * 50}")
print(f"Cover pipeline smoke tests: {passed}/{total} passed")
if passed == total:
    print("Sprint 1 — ALL CLEAR\n")
    sys.exit(0)
else:
    print(f"FAILED: {total - passed} test(s)\n")
    sys.exit(1)
