#!/usr/bin/env python3
"""End-to-end Phase 1 pipeline smoke test — runs without real API calls."""

import json
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from orchestrator.pipeline_runner import PipelineRunner


def run_smoke_test(artist_id: str, theme: str) -> bool:
    print(f"\n{'='*60}")
    print(f"Smoke Test: artist={artist_id} | theme={theme}")
    print("="*60)

    runner = PipelineRunner(gemini_client=None, firestore_client=None)
    result = runner.run(
        artist_id=artist_id,
        theme=theme,
        language=None,
        song_type="full_song",
        emotion_intensity=8,
    )

    if result.get("status") == "failed":
        print(f"[FAIL] Pipeline failed: {result.get('error')}")
        return False

    print(f"[PASS] Pipeline status: {result['status']}")
    print(f"  Song title: {result['song_title']}")
    print(f"  Hook line:  {result['lyrics']['hook_line']}")
    print(f"  SEO score:  {result['metadata']['seo_score']}/100")
    print(f"  Suno prompt (first 100 chars):")
    suno = result['music_prompts']['suno_prompt']
    print(f"    {suno[:100]}...")

    # Save output for inspection
    out_path = Path("storage") / artist_id / "songs"
    out_path.mkdir(parents=True, exist_ok=True)
    output_file = out_path / f"test_{theme}_output.json"
    output_file.write_text(json.dumps(result, indent=2, ensure_ascii=False))
    print(f"\n  Full output saved: {output_file}")
    return True


def main():
    tests = [
        ("aarav", "heartbreak_rain"),
        ("aarav", "midnight_loneliness"),
        ("aarohi", "spiritual_longing"),
    ]

    results = []
    for artist_id, theme in tests:
        passed = run_smoke_test(artist_id, theme)
        results.append((artist_id, theme, passed))

    print("\n" + "="*60)
    print("SMOKE TEST SUMMARY")
    print("="*60)
    all_pass = True
    for artist_id, theme, passed in results:
        status = "PASS" if passed else "FAIL"
        print(f"  [{status}] {artist_id} / {theme}")
        if not passed:
            all_pass = False

    if all_pass:
        print("\nAll Phase 1 pipeline smoke tests passed ✓")
        sys.exit(0)
    else:
        print("\nSome tests failed ✗")
        sys.exit(1)


if __name__ == "__main__":
    main()
