"""Music Prompt Agent — generates optimized prompts for Suno and Udio AI music generation."""

import json
import re
from pathlib import Path
from typing import Any

from agents.base_agent import BaseAgent

PROMPTS_DIR = Path(__file__).parent / "prompts"

SUNO_STYLE_MAP = {
    "aarav": {
        "base_style_tags": "dark cinematic bollywood, emotional hindi pop, lo-fi midnight, ambient trap soul",
        "vocal_tags": "male vocal, warm raspy voice, emotional delivery, intimate, breathy",
        "production_tags": "sparse piano, acoustic guitar, deep bass, string swells, vinyl texture",
        "mood_tags": "melancholic, heartbreak, cinematic, introspective",
    },
    "aarohi": {
        "base_style_tags": "spiritual folk pop, cinematic hindi female, ambient devotional, dream pop",
        "vocal_tags": "female vocal, airy ethereal voice, emotional whisper, expressive chorus",
        "production_tags": "fingerpicked guitar, soft piano, bansuri flute, orchestral strings, ambient pads",
        "mood_tags": "longing, healing, spiritual, ethereal, golden",
    },
}

MOOD_TO_BPM = {
    "melancholic": (65, 80),
    "heartbreak": (70, 85),
    "healing": (75, 90),
    "spiritual": (70, 88),
    "longing": (68, 82),
    "cinematic": (60, 80),
    "midnight": (65, 78),
    "golden": (78, 95),
}

MOOD_TO_KEY = {
    "melancholic": ["D minor", "A minor", "E minor"],
    "heartbreak": ["D minor", "B minor", "F# minor"],
    "healing": ["G major", "D major", "A major"],
    "spiritual": ["G major", "E major", "D major"],
    "longing": ["A minor", "E minor", "B minor"],
    "cinematic": ["D minor", "C minor", "G minor"],
    "midnight": ["B minor", "E minor", "A minor"],
    "golden": ["G major", "A major", "C major"],
}


class MusicPromptAgent(BaseAgent):
    def __init__(self, gemini_client=None):
        super().__init__("MusicPromptAgent")
        self._gemini = gemini_client

    def _execute(
        self,
        artist_id: str,
        artist_config: dict,
        context: dict[str, Any],
        job_id: str,
    ) -> dict[str, Any]:
        lyrics_output = context.get("lyrics_output", {})
        mood_tags = lyrics_output.get("mood_tags", [])
        hook_line = lyrics_output.get("hook_line", "")
        lyrics_text = lyrics_output.get("lyrics_text", "")
        genre_preference = context.get("genre_preference", "")
        platform_target = context.get("platform_target", "suno")

        bpm_range = self._derive_bpm(mood_tags)
        key = self._derive_key(mood_tags, artist_config)
        style_profile = SUNO_STYLE_MAP.get(artist_id, SUNO_STYLE_MAP["aarav"])

        if self._gemini and lyrics_text:
            prompts = self._generate_via_gemini(
                artist_id=artist_id,
                artist_config=artist_config,
                lyrics_text=lyrics_text,
                hook_line=hook_line,
                mood_tags=mood_tags,
                genre_preference=genre_preference,
                bpm_range=bpm_range,
                key=key,
                style_profile=style_profile,
                platform_target=platform_target,
            )
        else:
            prompts = self._build_template_prompts(
                artist_id=artist_id,
                mood_tags=mood_tags,
                bpm_range=bpm_range,
                key=key,
                style_profile=style_profile,
                genre_preference=genre_preference,
            )

        return {
            "suno_prompt": prompts["suno_prompt"],
            "udio_prompt": prompts["udio_prompt"],
            "negative_prompt": prompts["negative_prompt"],
            "production_notes": {
                "bpm_range": bpm_range,
                "key": key,
                "mood_tags": mood_tags,
                "instrumentation": style_profile["production_tags"],
            },
            "expected_genre_tags": self._extract_genre_tags(style_profile, genre_preference),
            "platform_target": platform_target,
        }

    def _derive_bpm(self, mood_tags: list[str]) -> tuple[int, int]:
        for mood in mood_tags:
            if mood in MOOD_TO_BPM:
                return MOOD_TO_BPM[mood]
        return (70, 85)

    def _derive_key(self, mood_tags: list[str], artist_config: dict) -> str:
        for mood in mood_tags:
            if mood in MOOD_TO_KEY:
                candidates = MOOD_TO_KEY[mood]
                preferred = artist_config.get("music_aesthetic", {}).get("preferred_keys", [])
                for key in candidates:
                    if key in preferred:
                        return key
                return candidates[0]
        preferred = artist_config.get("music_aesthetic", {}).get("preferred_keys", ["D minor"])
        return preferred[0]

    def _build_template_prompts(
        self,
        artist_id: str,
        mood_tags: list[str],
        bpm_range: tuple,
        key: str,
        style_profile: dict,
        genre_preference: str,
    ) -> dict[str, str]:
        mood_str = ", ".join(mood_tags[:4]) if mood_tags else "melancholic, cinematic"
        bpm_str = f"{bpm_range[0]}-{bpm_range[1]} BPM"

        genre_extra = f", {genre_preference}" if genre_preference else ""

        suno_prompt = (
            f"[{style_profile['base_style_tags']}{genre_extra}] "
            f"[{style_profile['vocal_tags']}] "
            f"[{style_profile['production_tags']}] "
            f"[mood: {mood_str}] "
            f"[key: {key}] [{bpm_str}] "
            f"[emotional, cinematic, commercially modern]"
        )

        udio_prompt = (
            f"Genre: {style_profile['base_style_tags']}{genre_extra}. "
            f"Vocals: {style_profile['vocal_tags']}. "
            f"Instrumentation: {style_profile['production_tags']}. "
            f"Mood: {mood_str}. Key: {key}. Tempo: {bpm_str}. "
            f"Production quality: professional, emotionally resonant, cinematic."
        )

        negative_prompt = (
            "no autotune robotics, no harsh distortion, no comedy tone, "
            "no upbeat club music, no explicit content, no EDM drops, "
            "no plagiarized melody from existing copyrighted songs"
        )

        return {
            "suno_prompt": suno_prompt,
            "udio_prompt": udio_prompt,
            "negative_prompt": negative_prompt,
        }

    def _generate_via_gemini(
        self,
        artist_id: str,
        artist_config: dict,
        lyrics_text: str,
        hook_line: str,
        mood_tags: list[str],
        genre_preference: str,
        bpm_range: tuple,
        key: str,
        style_profile: dict,
        platform_target: str,
    ) -> dict[str, str]:
        persona = artist_config.get("personality", "")
        instrumentation = artist_config.get("music_aesthetic", {}).get(
            "instrumentation_signature", []
        )
        instru_str = ", ".join(instrumentation[:5])

        user_prompt = f"""Based on these song lyrics, generate optimized AI music generation prompts.

ARTIST PERSONA: {persona}
MOOD TAGS: {", ".join(mood_tags)}
HOOK LINE: {hook_line}
KEY: {key}
BPM RANGE: {bpm_range[0]}-{bpm_range[1]}
INSTRUMENTATION SIGNATURE: {instru_str}
STYLE BASE: {style_profile['base_style_tags']}
VOCAL STYLE: {style_profile['vocal_tags']}

LYRICS EXCERPT (first 8 lines):
{chr(10).join(lyrics_text.split(chr(10))[:8])}

Generate a JSON response with this exact structure:
```json
{{
  "suno_prompt": "Complete Suno-format prompt with style tags in brackets",
  "udio_prompt": "Complete Udio-format prompt as descriptive sentences",
  "negative_prompt": "Elements to avoid in generation"
}}
```"""

        raw = self._gemini.generate(
            system_prompt="You are an expert AI music prompt engineer specializing in Suno and Udio.",
            user_prompt=user_prompt,
            model="gemini-1.5-flash",
            temperature=0.7,
            max_tokens=800,
        )

        json_match = re.search(r"```json\s*(\{.*?\})\s*```", raw, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass

        return self._build_template_prompts(
            artist_id=artist_id,
            mood_tags=mood_tags,
            bpm_range=bpm_range,
            key=key,
            style_profile=style_profile,
            genre_preference=genre_preference,
        )

    def _extract_genre_tags(self, style_profile: dict, genre_preference: str) -> list[str]:
        base = style_profile["base_style_tags"].split(", ")
        if genre_preference:
            base.append(genre_preference)
        return base[:6]
