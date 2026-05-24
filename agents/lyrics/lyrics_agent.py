"""Lyrics Agent — generates emotionally resonant song lyrics via Gemini."""

import json
import re
from pathlib import Path
from typing import Any

from agents.base_agent import BaseAgent

PROMPTS_DIR = Path(__file__).parent / "prompts"

THEMES = {
    "heartbreak_rain": "heartbreak and rain, the aftermath of love ending on a rainy night",
    "midnight_loneliness": "the quiet devastation of 3am loneliness, city lights and silence",
    "nostalgia_memories": "nostalgic memories of someone who is gone, bittersweet remembrance",
    "healing_slowly": "the slow painful process of healing after heartbreak",
    "long_distance": "love that survives distance and separation",
    "unrequited_love": "loving someone who doesn't love you back, quietly",
    "last_conversation": "the final conversation before a relationship ends",
    "spiritual_longing": "spiritual yearning, longing for a divine connection or reunion",
    "feminine_strength": "quiet feminine resilience rising from emotional pain",
    "renewal_hope": "finding hope and light after darkness, gentle rebirth",
}

LANGUAGE_INSTRUCTIONS = {
    "hindi": "Write entirely in Devanagari Hindi script with occasional Urdu-influenced poetic vocabulary.",
    "hinglish": "Write in Hinglish — a natural blend of Hindi (Devanagari) and English, as spoken by Indian youth. Keep it authentic, not forced.",
    "english": "Write entirely in English with poetic, emotionally cinematic language.",
    "urdu": "Write in Urdu (Roman or Nastaliq script) with ghazal-influenced poetic sensibility.",
}


class LyricsAgent(BaseAgent):
    def __init__(self, gemini_client=None):
        super().__init__("LyricsAgent")
        self._gemini = gemini_client

    def _execute(
        self,
        artist_id: str,
        artist_config: dict,
        context: dict[str, Any],
        job_id: str,
    ) -> dict[str, Any]:
        theme = context.get("theme", "heartbreak_rain")
        language = context.get("language", artist_config.get("primary_language", "hindi"))
        song_type = context.get("song_type", "full_song")
        emotion_intensity = context.get("emotion_intensity", 7)
        title_hint = context.get("title_hint", "")

        theme_description = THEMES.get(theme, theme)
        language_instruction = LANGUAGE_INSTRUCTIONS.get(language, LANGUAGE_INSTRUCTIONS["hindi"])

        system_prompt = self._load_system_prompt(artist_id)
        user_prompt = self._build_user_prompt(
            artist_config=artist_config,
            theme=theme,
            theme_description=theme_description,
            language_instruction=language_instruction,
            song_type=song_type,
            emotion_intensity=emotion_intensity,
            title_hint=title_hint,
        )

        if self._gemini:
            raw_response = self._gemini.generate(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                model="gemini-1.5-pro",
                temperature=0.85,
                max_tokens=2000,
            )
        else:
            raw_response = self._mock_response(artist_id, theme, language)

        return self._parse_response(raw_response, theme, language, song_type)

    def _load_system_prompt(self, artist_id: str) -> str:
        prompt_file = PROMPTS_DIR / f"{artist_id}_lyrics_system.txt"
        if prompt_file.exists():
            return prompt_file.read_text(encoding="utf-8")
        return "You are an emotionally intelligent AI music lyricist."

    def _build_user_prompt(
        self,
        artist_config: dict,
        theme: str,
        theme_description: str,
        language_instruction: str,
        song_type: str,
        emotion_intensity: int,
        title_hint: str,
    ) -> str:
        personality = artist_config.get("personality", "")
        keywords = ", ".join(artist_config.get("theme_keywords", [])[:6])
        emotion_range = artist_config.get("emotion_range", "melancholic → accepting")

        title_line = f"Suggested title direction: {title_hint}\n" if title_hint else ""

        structure_note = (
            "Generate the full song structure: Verse 1, Pre-Chorus, Chorus, Verse 2, "
            "Pre-Chorus, Chorus, Bridge, Final Chorus, Outro."
            if song_type == "full_song"
            else "Generate a SHORT CLIP version: one verse, one chorus, outro only."
        )

        return f"""Generate complete song lyrics for the following:

THEME: {theme_description}
EMOTIONAL INTENSITY: {emotion_intensity}/10
{title_line}
LANGUAGE: {language_instruction}
ARTIST PERSONALITY: {personality}
EMOTIONAL KEYWORDS: {keywords}
EMOTIONAL ARC: {emotion_range}

{structure_note}

After the lyrics, provide a JSON block with this exact format:
```json
{{
  "suggested_titles": ["Title 1", "Title 2", "Title 3"],
  "hook_line": "The single most emotionally powerful singable line",
  "mood_tags": ["tag1", "tag2", "tag3", "tag4"],
  "estimated_duration_seconds": 210,
  "language_detected": "{{}}"
}}
```

Write the lyrics first, then the JSON block."""

    def _parse_response(
        self, raw: str, theme: str, language: str, song_type: str
    ) -> dict[str, Any]:
        metadata = {
            "suggested_titles": [f"Untitled — {theme}"],
            "hook_line": "",
            "mood_tags": [],
            "estimated_duration_seconds": 210 if song_type == "full_song" else 45,
            "language_detected": language,
        }

        json_match = re.search(r"```json\s*(\{.*?\})\s*```", raw, re.DOTALL)
        if json_match:
            try:
                parsed = json.loads(json_match.group(1))
                metadata.update(parsed)
            except json.JSONDecodeError:
                self.logger.warning("Failed to parse metadata JSON from lyrics response")

        lyrics_text = re.sub(r"```json.*?```", "", raw, flags=re.DOTALL).strip()

        return {
            "lyrics_text": lyrics_text,
            "hook_line": metadata.get("hook_line", ""),
            "suggested_titles": metadata.get("suggested_titles", []),
            "mood_tags": metadata.get("mood_tags", []),
            "estimated_duration_seconds": metadata.get("estimated_duration_seconds", 210),
            "language_detected": metadata.get("language_detected", language),
            "theme": theme,
            "song_type": song_type,
        }

    def _mock_response(self, artist_id: str, theme: str, language: str) -> str:
        """Returns a mock response for testing without a live Gemini connection."""
        if artist_id == "aarav":
            lyrics = """[VERSE 1]
Khidki ke sheeshe pe barish ki lakeeren,
Tere jaane ke baad aayi hain ye rateein.
Cigarette ki raakh, khali pyaala chai,
Main hun, meri tanhai hai, aur kuch nahi.

[PRE-CHORUS]
Kuch alfaaz the jo kehne the tujhko,
Ab woh alfaaz bhi mujhse chhoot gaye...

[CHORUS]
Barsaat mein kho gaya tera khayal,
Phir bhi bheeg raha hun, phir bhi.
Raat ka ye sukoon, ye dard ka jaal,
Phir bhi jeeta hun, phir bhi.

[VERSE 2]
Phone ki screen pe teri photos hain,
Delete karna chahta hun, par haath ruk jaate hain.
Teri mehk abhi tak mere kamre mein hai,
Kaise bataaun, main kahan hun abhi.

[PRE-CHORUS]
Kuch alfaaz the jo kehne the tujhko,
Ab woh alfaaz bhi mujhse chhoot gaye...

[CHORUS]
Barsaat mein kho gaya tera khayal,
Phir bhi bheeg raha hun, phir bhi.
Raat ka ye sukoon, ye dard ka jaal,
Phir bhi jeeta hun, phir bhi.

[BRIDGE]
Subah hogi, main jaanta hun.
Par abhi raat hai, aur tu nahi.
Bas itna hi kafi hai dard ke liye.
Bas itna hi.

[FINAL CHORUS]
Barsaat mein kho gaya tera khayal,
Phir bhi bheeg raha hun, phir bhi.
Raat ka ye sukoon, ye dard ka jaal,
Phir bhi jeeta hun... phir bhi.

[OUTRO]
Barsaat rukegi kabhi na kabhi.
Magar tu... tu nahi aayega.

```json
{
  "suggested_titles": ["Barsaat Mein Kho Gaya", "Phir Bhi", "Raat Ka Sukoon"],
  "hook_line": "Barsaat mein kho gaya tera khayal",
  "mood_tags": ["melancholic", "midnight", "rain", "heartbreak", "cinematic"],
  "estimated_duration_seconds": 215,
  "language_detected": "hinglish"
}
```"""
        else:
            lyrics = """[VERSE 1]
Suraj ke pehle kiran se pehle,
Main uthti hun, tujhe yaad karte.
Phoolon ki mehk mein teri aawaz,
Kab aayega, main wait karti.

[PRE-CHORUS]
Ye intezaar bhi ek dua hai,
Tujhse milne ki, tujhse milne ki...

[CHORUS]
Tere liye ruk gayi hain saansein meri,
Phir bhi chalti hain, phir bhi.
Teri yaad mein dhalti hain roshni,
Phir bhi jalti hain, phir bhi.

[VERSE 2]
Nadi ke kinare baithe baithe,
Teri parchhain dhundhti hun paani mein.
Ye khuli hawa jo chhu ke jaaye,
Lagta hai tu hi hai is kahaani mein.

[PRE-CHORUS]
Ye intezaar bhi ek dua hai,
Tujhse milne ki, tujhse milne ki...

[CHORUS]
Tere liye ruk gayi hain saansein meri,
Phir bhi chalti hain, phir bhi.
Teri yaad mein dhalti hain roshni,
Phir bhi jalti hain, phir bhi.

[BRIDGE]
Jo door hai woh paas bhi hai.
Jo kho gaya woh mila bhi hai.
Yahi to hai ishq ki reet...

[FINAL CHORUS]
Tere liye ruk gayi hain saansein meri,
Phir bhi chalti hain, phir bhi.
Teri yaad mein dhalti hain roshni,
Phir bhi jalti hain... phir bhi.

[OUTRO]
Suraj uthega kal bhi.
Aur main... main phir duaon mein tujhe dhundhuungi.

```json
{
  "suggested_titles": ["Phir Bhi Chalti Hain", "Teri Yaad Ki Roshni", "Intezaar Ki Dua"],
  "hook_line": "Tere liye ruk gayi hain saansein meri",
  "mood_tags": ["longing", "spiritual", "healing", "golden", "feminine_strength"],
  "estimated_duration_seconds": 220,
  "language_detected": "hinglish"
}
```"""
        return lyrics
