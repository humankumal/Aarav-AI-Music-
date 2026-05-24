"""Music Prompt Agent — generates optimized prompts for Google Lyria (Vertex AI)."""

import json
import re
from pathlib import Path
from typing import Any

from agents.base_agent import BaseAgent

PROMPTS_DIR = Path(__file__).parent / "prompts"

# Natural-language style profiles for Google Lyria.
# Lyria expects descriptive prose, not bracket-style tags.
LYRIA_STYLE_MAP = {
    "aarav": {
        "genre": "dark cinematic Bollywood, emotional Hindi pop, lo-fi midnight, ambient trap soul",
        "vocals": "warm raspy male voice, intimate emotional delivery, breathy and expressive, realistic imperfections",
        "instrumentation": "sparse piano, fingerpicked acoustic guitar, deep 808 bass, orchestral string swells, vinyl crackle texture, atmospheric synth pads",
        "mood": "melancholic, heartbreak, cinematic, introspective, late-night",
    },
    "aarohi": {
        "genre": "spiritual folk pop, cinematic Hindi female vocal, ambient devotional, dream pop, world music fusion",
        "vocals": "airy ethereal female voice, emotional whisper to soar, expressive chorus, dreamy layered vocals",
        "instrumentation": "delicate fingerpicked guitar, ethereal piano, bansuri flute, soft orchestral strings, ambient pads, light percussive heartbeats",
        "mood": "longing, healing, spiritual, ethereal, golden, transcendent",
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
        platform_target = context.get("platform_target", "lyria")

        bpm_range = self._derive_bpm(mood_tags)
        key = self._derive_key(mood_tags, artist_config)
        style_profile = LYRIA_STYLE_MAP.get(artist_id, LYRIA_STYLE_MAP["aarav"])

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
            "lyria_prompt": prompts["lyria_prompt"],
            "negative_prompt": prompts["negative_prompt"],
            "production_notes": {
                "bpm_range": bpm_range,
                "key": key,
                "mood_tags": mood_tags,
                "instrumentation": style_profile["instrumentation"],
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
        bpm_mid = (bpm_range[0] + bpm_range[1]) // 2
        genre_extra = f", {genre_preference}" if genre_preference else ""

        # Google Lyria expects natural language, not bracket tags
        lyria_prompt = (
            f"Genre: {style_profile['genre']}{genre_extra}. "
            f"Vocals: {style_profile['vocals']}. "
            f"Instrumentation: {style_profile['instrumentation']}. "
            f"Mood: {mood_str}. "
            f"Key: {key}. Tempo: approximately {bpm_mid} BPM. "
            f"Production quality: professional, emotionally resonant, cinematic, "
            f"commercially modern Hindi music."
        )

        negative_prompt = (
            "no autotune robotics, no harsh distortion, no comedy tone, "
            "no upbeat club music, no explicit content, no EDM drops, "
            "no plagiarized melody from existing copyrighted songs"
        )

        return {
            "lyria_prompt": lyria_prompt,
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

        bpm_mid = (bpm_range[0] + bpm_range[1]) // 2

        user_prompt = f"""Based on these song lyrics, generate an optimized natural-language prompt for Google Lyria (Vertex AI music generation). Lyria expects descriptive prose — not bracket tags.

ARTIST PERSONA: {persona}
MOOD TAGS: {", ".join(mood_tags)}
HOOK LINE: {hook_line}
KEY: {key}
TEMPO: approximately {bpm_mid} BPM
INSTRUMENTATION: {instru_str}
GENRE BASE: {style_profile['genre']}
VOCAL STYLE: {style_profile['vocals']}

LYRICS EXCERPT (first 8 lines):
{chr(10).join(lyrics_text.split(chr(10))[:8])}

Generate a JSON response with this exact structure:
```json
{{
  "lyria_prompt": "Complete natural-language prompt describing genre, vocals, instrumentation, mood, key, tempo, and emotional quality for Google Lyria",
  "negative_prompt": "Elements to avoid in generation"
}}
```"""

        raw = self._gemini.generate(
            system_prompt="You are an expert AI music prompt engineer specializing in Google Lyria (Vertex AI).",
            user_prompt=user_prompt,
            model="gemini-1.5-flash",
            temperature=0.7,
            max_tokens=600,
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
        base = style_profile["genre"].split(", ")
        if genre_preference:
            base.append(genre_preference)
        return base[:6]
