"""Cover Song Agent — rewrites a reference song's emotional DNA as an original
composition in Aarav or Aarohi's voice. Two-step Gemini call:
  1. Flash (low temp) — extract emotional anchors from the reference song
  2. Pro (high temp)  — write original lyrics using those anchors + artist persona
"""

import json
import re
from pathlib import Path
from typing import Any

from agents.base_agent import BaseAgent

PROMPTS_DIR = Path(__file__).parent / "prompts"
CATALOG_DIR = Path(__file__).parent.parent.parent / "config" / "covers"


class CoverSongAgent(BaseAgent):
    def __init__(self, gemini_client=None):
        super().__init__("CoverSongAgent")
        self._gemini = gemini_client

    def _execute(
        self,
        artist_id: str,
        artist_config: dict,
        context: dict[str, Any],
        job_id: str,
    ) -> dict[str, Any]:
        reference_song_title = context.get("reference_song_title", "")
        reference_artist_name = context.get("reference_artist_name", "")
        catalog_type = context.get("catalog_type", "global")
        song_id = context.get("song_id", "")
        emotion_intensity = context.get("emotion_intensity", 8)
        language = context.get("language") or artist_config.get("primary_language", "hinglish")

        # Load artist genre context from catalog file
        genre_tags = context.get("genre_tags", [])

        if self._gemini and reference_song_title and reference_artist_name:
            return self._generate_via_gemini(
                artist_id=artist_id,
                artist_config=artist_config,
                reference_song_title=reference_song_title,
                reference_artist_name=reference_artist_name,
                genre_tags=genre_tags,
                catalog_type=catalog_type,
                song_id=song_id,
                emotion_intensity=emotion_intensity,
                language=language,
                job_id=job_id,
            )

        return self._mock_response(
            artist_id=artist_id,
            reference_song_title=reference_song_title,
            reference_artist_name=reference_artist_name,
            catalog_type=catalog_type,
            song_id=song_id,
        )

    def _generate_via_gemini(
        self,
        artist_id: str,
        artist_config: dict,
        reference_song_title: str,
        reference_artist_name: str,
        genre_tags: list[str],
        catalog_type: str,
        song_id: str,
        emotion_intensity: int,
        language: str,
        job_id: str,
    ) -> dict[str, Any]:
        system_prompt = self._load_system_prompt(artist_id)
        persona = artist_config.get("personality", "")

        # ── Call 1: Emotional anchor extraction (Flash, low temp) ──────────────
        anchor_prompt = f"""A famous song titled "{reference_song_title}" by {reference_artist_name}
has a specific emotional world. Based on your knowledge of this song:

1. Identify the PRIMARY emotion the song makes listeners feel (1 word)
2. List 4 specific emotional anchors — concrete feelings or situations in the song
3. Describe the central human experience in one sentence (what is this song ABOUT at its deepest level?)
4. Suggest a Hindi/Hinglish thematic frame that captures the same emotion

Respond in JSON:
{{
  "primary_emotion": "...",
  "emotional_anchors": ["...", "...", "...", "..."],
  "core_human_experience": "...",
  "hindi_thematic_frame": "...",
  "suggested_mood_tags": ["...", "...", "..."]
}}"""

        anchor_raw = self._gemini.generate(
            system_prompt="You are an expert in global and South Asian music. Analyze songs with emotional precision.",
            user_prompt=anchor_prompt,
            model="gemini-1.5-flash",
            temperature=0.4,
            max_tokens=400,
        )

        anchors = self._parse_json_response(anchor_raw, {
            "primary_emotion": "longing",
            "emotional_anchors": ["heartbreak", "distance", "memory", "silence"],
            "core_human_experience": "The ache of loving someone you can no longer reach",
            "hindi_thematic_frame": "Jo door hai woh dil ke paas hai",
            "suggested_mood_tags": ["melancholic", "longing", "cinematic"],
        })

        # ── Call 2: Original lyric generation (Pro, high temp) ─────────────────
        mood_tags = anchors.get("suggested_mood_tags", ["melancholic", "longing"])
        core_experience = anchors.get("core_human_experience", "")
        hindi_frame = anchors.get("hindi_thematic_frame", "")
        emotional_anchor_list = anchors.get("emotional_anchors", [])

        lyric_prompt = f"""Write original song lyrics for {artist_id.upper()} AI MUSIC.

EMOTIONAL BRIEF:
- Core human experience to capture: {core_experience}
- Emotional anchors to write toward: {', '.join(emotional_anchor_list)}
- Hindi thematic frame: {hindi_frame}
- Emotion intensity: {emotion_intensity}/10
- Language: {language}

ARTIST PERSONA:
{persona}

CRITICAL: This must be 100% original. Do NOT reference, quote, or paraphrase "{reference_song_title}"
by {reference_artist_name}. You are writing a new song from the same emotional universe.

Write full structured lyrics with [VERSE 1], [CHORUS], [VERSE 2], [CHORUS], [BRIDGE], [CHORUS].
After the lyrics, on a new line, add:
HOOK: <the most emotionally resonant single line from the chorus>
TITLES: <3 possible song titles, comma-separated>"""

        lyrics_raw = self._gemini.generate(
            system_prompt=system_prompt,
            user_prompt=lyric_prompt,
            model="gemini-1.5-pro",
            temperature=0.9,
            max_tokens=1200,
        )

        lyrics_text, hook_line, suggested_titles = self._parse_lyrics_response(lyrics_raw)

        return {
            "lyrics_text": lyrics_text,
            "hook_line": hook_line,
            "suggested_titles": suggested_titles,
            "mood_tags": mood_tags,
            "estimated_duration_seconds": 210,
            "language_detected": language,
            "song_type": "cover_inspired",
            "reference_song_title": reference_song_title,
            "reference_artist_name": reference_artist_name,
            "catalog_type": catalog_type,
            "song_id": song_id,
            "emotional_anchors": emotional_anchor_list,
            "core_human_experience": core_experience,
            "lyrics_are_original": True,
        }

    def _mock_response(
        self,
        artist_id: str,
        reference_song_title: str,
        reference_artist_name: str,
        catalog_type: str,
        song_id: str,
    ) -> dict[str, Any]:
        if artist_id == "aarohi":
            lyrics = """[VERSE 1]
Subah ki roshni mein tera chehra yaad aata hai
Phoolon ki khushboo mein teri baatein mehak jaati hain
Jo beet gaya woh sapna tha, jo aana hai woh sach hai
Tere bina bhi zindagi meri chal jaati hai

[CHORUS]
Tere jaane ke baad bhi, teri yaadein mujhe jeeti hain
Har dhoop mein teri chhaya, har raat mein teri baatein
Jo toota hai woh jud jaata hai teri yaadon se
Tujhe bhula nahi sakti, yahi meri kahani hai

[VERSE 2]
Nadiyaan beh jaati hain apni raah chalti hain
Waqt ki dhara mein khud ko main paa jaati hoon
Har alvida mein ek naya safar chhupta hai
Tere bina bhi apni duniya main bana jaati hoon

[BRIDGE]
Yeh dard bhi ek tohfa hai tere pyaar ka
Har aansu mein teri yaad ka ek phool hai
Jo nahi raha woh kabhi gaya bhi nahi
Dil ke kisi kone mein woh hamesha rehta hai"""
            hook = "Tere jaane ke baad bhi, teri yaadein mujhe jeeti hain"
            titles = ["Teri Yaadein", "Jo Nahi Raha", "Yaadon Ka Phool"]
        else:
            lyrics = """[VERSE 1]
Raat ke teen baje woh purani baatein yaad aati hain
Cigarette ka dhuan aur teri tasveer — bas itna hi bacha hai
Dono hath khali hain par dil bhar gaya hai
Tujhe bhulana chahta tha, tujhe hi yaad kar raha hoon

[CHORUS]
Teri yaad ek zakhm hai jo bhar nahi sakta
Teri khamoshi ek awaaz hai jo sunai deti hai
Kya kahu tujhse, kya na kahu — sab kuch andhera hai
Baarish mein bheeg ke bhi sukha nahi hoon main

[VERSE 2]
Sheher ki roshniyan hain par ghar mein andhera hai
Teri awaaz ka silsila ab khwabon mein hi hai
Jo tha woh gaya, jo hai woh tujh mein tha kabhi
Meri tanhai ka ek naam tha — tera naam tha

[BRIDGE]
Na jaana tha itna — na paana tha itna
Phir bhi yeh dil dhoondta hai tujhe har gali mein
Woh pal jo the hamare — ab sirf mere hain
Akela hoon main — par teri yaad meri hai"""
            hook = "Teri yaad ek zakhm hai jo bhar nahi sakta"
            titles = ["Teri Yaad", "Teen Baje", "Khamoshi Ki Awaaz"]

        return {
            "lyrics_text": lyrics,
            "hook_line": hook,
            "suggested_titles": titles,
            "mood_tags": ["melancholic", "longing", "cinematic"],
            "estimated_duration_seconds": 210,
            "language_detected": "hinglish",
            "song_type": "cover_inspired",
            "reference_song_title": reference_song_title,
            "reference_artist_name": reference_artist_name,
            "catalog_type": catalog_type,
            "song_id": song_id,
            "emotional_anchors": ["heartbreak", "memory", "absence", "longing"],
            "core_human_experience": "The ache of loving someone you can no longer reach",
            "lyrics_are_original": True,
        }

    def _load_system_prompt(self, artist_id: str) -> str:
        prompt_file = PROMPTS_DIR / f"{artist_id}_cover_system.txt"
        if prompt_file.exists():
            return prompt_file.read_text(encoding="utf-8")
        fallback = PROMPTS_DIR / "aarav_cover_system.txt"
        if fallback.exists():
            return fallback.read_text(encoding="utf-8")
        return "You are a professional Hindi/Hinglish lyricist. Write original, emotionally resonant song lyrics."

    def _parse_json_response(self, raw: str, fallback: dict) -> dict:
        json_match = re.search(r"\{.*?\}", raw, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(0))
            except json.JSONDecodeError:
                pass
        return fallback

    def _parse_lyrics_response(self, raw: str) -> tuple[str, str, list[str]]:
        hook_match = re.search(r"^HOOK:\s*(.+)$", raw, re.MULTILINE)
        titles_match = re.search(r"^TITLES:\s*(.+)$", raw, re.MULTILINE)

        hook_line = hook_match.group(1).strip() if hook_match else ""
        suggested_titles = []
        if titles_match:
            suggested_titles = [t.strip() for t in titles_match.group(1).split(",")]

        lyrics_text = re.sub(r"^(HOOK|TITLES):.*$", "", raw, flags=re.MULTILINE).strip()

        if not hook_line and "[CHORUS]" in lyrics_text:
            chorus_lines = re.findall(r"\[CHORUS\]\n(.+)", lyrics_text)
            hook_line = chorus_lines[0].strip() if chorus_lines else ""

        if not suggested_titles:
            suggested_titles = ["Teri Yaad", "Jo Tha", "Andheri Raat"]

        return lyrics_text, hook_line, suggested_titles

    @staticmethod
    def load_song_from_catalog(song_id: str, catalog_type: str) -> dict | None:
        """Utility: look up a song by song_id from the catalog files."""
        catalog_dir = CATALOG_DIR / catalog_type
        index_path = catalog_dir / "index.json"
        if not index_path.exists():
            return None
        index = json.loads(index_path.read_text())
        for artist_entry in index.get("artists", []):
            artist_file = catalog_dir / artist_entry["file"]
            if not artist_file.exists():
                continue
            artist_data = json.loads(artist_file.read_text())
            for song in artist_data.get("songs", []):
                if song["song_id"] == song_id:
                    return {
                        **song,
                        "reference_artist_id": artist_data["reference_artist_id"],
                        "reference_artist_name": artist_data["reference_artist_name"],
                        "origin": artist_data.get("origin", ""),
                        "primary_language": artist_data.get("primary_language", ""),
                        "genre_tags": artist_data.get("genre_tags", []),
                        "catalog_type": catalog_type,
                    }
        return None
