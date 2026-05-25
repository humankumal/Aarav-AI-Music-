"""Metadata Agent — generates SEO-optimized titles, descriptions, tags, and hashtags."""

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from agents.base_agent import BaseAgent

SEO_RULES_PATH = Path(__file__).parent / "seo_rules.json"
CURRENT_YEAR = datetime.now().year


class MetadataAgent(BaseAgent):
    def __init__(self, gemini_client=None):
        super().__init__("MetadataAgent")
        self._gemini = gemini_client
        self._seo_rules = json.loads(SEO_RULES_PATH.read_text())

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
        suggested_titles = lyrics_output.get("suggested_titles", [])
        language = lyrics_output.get("language_detected", "hindi")
        duration_seconds = lyrics_output.get("estimated_duration_seconds", 210)

        music_prompt_output = context.get("music_prompt_output", {})
        genre_tags = music_prompt_output.get("expected_genre_tags", [])

        platform_target = context.get("platform_target", "youtube")
        song_title = context.get("song_title") or (
            suggested_titles[0] if suggested_titles else "Untitled"
        )
        cover_mode = bool(context.get("cover_mode"))
        reference_song_title = context.get("reference_song_title", "")
        reference_artist_name = context.get("reference_artist_name", "")

        if self._gemini:
            result = self._generate_via_gemini(
                artist_id=artist_id,
                artist_config=artist_config,
                song_title=song_title,
                hook_line=hook_line,
                mood_tags=mood_tags,
                genre_tags=genre_tags,
                language=language,
                platform_target=platform_target,
                duration_seconds=duration_seconds,
            )
        else:
            result = self._build_template_metadata(
                artist_id=artist_id,
                artist_config=artist_config,
                song_title=song_title,
                hook_line=hook_line,
                mood_tags=mood_tags,
                genre_tags=genre_tags,
                language=language,
                platform_target=platform_target,
                duration_seconds=duration_seconds,
            )

        if cover_mode and reference_song_title:
            result = self._apply_cover_overrides(
                result=result,
                artist_id=artist_id,
                artist_config=artist_config,
                song_title=song_title,
                reference_song_title=reference_song_title,
                reference_artist_name=reference_artist_name,
                mood_tags=mood_tags,
            )

        result["seo_score"] = self._calculate_seo_score(result)
        return result

    def _build_template_metadata(
        self,
        artist_id: str,
        artist_config: dict,
        song_title: str,
        hook_line: str,
        mood_tags: list[str],
        genre_tags: list[str],
        language: str,
        platform_target: str,
        duration_seconds: int,
    ) -> dict[str, Any]:
        display_name = artist_config["display_name"]
        seo_config = artist_config.get("seo", {})
        social = artist_config.get("social_profiles", {})

        primary_mood = mood_tags[0].title() if mood_tags else "Emotional"
        emotional_keyword = self._pick_emotional_keyword(mood_tags)

        title = (
            f"{emotional_keyword} | {song_title} | {display_name} | "
            f"Hindi {primary_mood} Song {CURRENT_YEAR}"
        )
        if len(title) > 100:
            title = f"{song_title} | {display_name} | Hindi {primary_mood} Song {CURRENT_YEAR}"

        chapters = self._generate_chapters(duration_seconds)
        ai_disclosure = self._seo_rules["ai_disclosure_text"]

        subscribe_url = social.get("youtube_channel_url", "")
        spotify_url = social.get("spotify_artist_id", "")
        instagram_url = f"https://instagram.com/{social.get('instagram_handle', '').lstrip('@')}"
        tiktok_url = f"https://tiktok.com/@{social.get('tiktok_username', '')}"

        description = f"""{hook_line}

A new emotional journey from {display_name}. '{song_title}' is a cinematic {language} song that touches the deepest corners of the heart.

Stream and experience the emotion ↓

{chapters}

🔔 Subscribe: {subscribe_url}
🎵 Spotify: Coming Soon
📸 Instagram: {instagram_url}
🎵 TikTok: {tiktok_url}

{ai_disclosure}

{self._build_hashtag_block(artist_id, mood_tags)}"""

        tags = self._build_tags(artist_config, song_title, mood_tags, genre_tags)
        hashtags = self._build_hashtags(artist_id, mood_tags)

        return {
            "title": title,
            "description": description,
            "tags": tags,
            "hashtags": hashtags,
            "youtube_chapters": chapters,
            "thumbnail_text": song_title,
            "platform_target": platform_target,
            "language": language,
            "spotify_metadata": {
                "track_title": song_title,
                "artist": display_name,
                "genre": genre_tags[0] if genre_tags else "Bollywood",
                "mood_tags": mood_tags[:3],
                "language": language,
                "explicit": False,
            },
        }

    def _generate_via_gemini(self, **kwargs) -> dict[str, Any]:
        artist_config = kwargs["artist_config"]
        artist_id = kwargs["artist_id"]
        song_title = kwargs["song_title"]
        hook_line = kwargs["hook_line"]
        mood_tags = kwargs["mood_tags"]
        genre_tags = kwargs["genre_tags"]
        language = kwargs["language"]
        platform_target = kwargs["platform_target"]
        duration_seconds = kwargs["duration_seconds"]

        display_name = artist_config["display_name"]
        seo_tags_base = ", ".join(artist_config.get("seo", {}).get("core_tags", [])[:5])

        user_prompt = f"""Generate YouTube metadata for this AI music video:

ARTIST: {display_name}
SONG TITLE: {song_title}
HOOK LINE: {hook_line}
MOOD TAGS: {", ".join(mood_tags)}
GENRE TAGS: {", ".join(genre_tags)}
LANGUAGE: {language}
DURATION: {duration_seconds} seconds
PLATFORM: {platform_target}
YEAR: {CURRENT_YEAR}
CORE SEO TAGS: {seo_tags_base}

Generate JSON with this structure:
```json
{{
  "title": "YouTube-optimized title under 100 chars",
  "description": "Full YouTube description (5000 chars max) with emotional hook, lyrics teaser, timestamps placeholder, platform links placeholder, AI disclosure, and hashtags",
  "tags": ["tag1", "tag2", ...30 tags total],
  "hashtags": ["#Tag1", "#Tag2", ...20 hashtags],
  "thumbnail_text": "Short dramatic text for thumbnail overlay",
  "youtube_chapters": "Chapter timestamps as plain text"
}}
```"""

        raw = self._gemini.generate(
            system_prompt="You are a YouTube SEO expert for Hindi emotional music channels.",
            user_prompt=user_prompt,
            model="gemini-1.5-flash",
            temperature=0.7,
            max_tokens=1500,
        )

        json_match = re.search(r"```json\s*(\{.*?\})\s*```", raw, re.DOTALL)
        if json_match:
            try:
                parsed = json.loads(json_match.group(1))
                parsed.setdefault("platform_target", platform_target)
                parsed.setdefault("language", language)
                parsed.setdefault(
                    "spotify_metadata",
                    {
                        "track_title": song_title,
                        "artist": display_name,
                        "genre": genre_tags[0] if genre_tags else "Bollywood",
                        "mood_tags": mood_tags[:3],
                        "language": language,
                        "explicit": False,
                    },
                )
                return parsed
            except json.JSONDecodeError:
                pass

        return self._build_template_metadata(
            artist_id=artist_id,
            artist_config=artist_config,
            song_title=song_title,
            hook_line=hook_line,
            mood_tags=mood_tags,
            genre_tags=genre_tags,
            language=language,
            platform_target=platform_target,
            duration_seconds=duration_seconds,
        )

    def _pick_emotional_keyword(self, mood_tags: list[str]) -> str:
        keyword_map = {
            "melancholic": "Dard",
            "heartbreak": "Judai",
            "midnight": "Raat",
            "rain": "Baarish",
            "longing": "Intezaar",
            "healing": "Shifa",
            "spiritual": "Dua",
            "nostalgic": "Yaadein",
            "feminine_strength": "Himmat",
            "golden": "Roshni",
        }
        for tag in mood_tags:
            if tag in keyword_map:
                return keyword_map[tag]
        return "Dil"

    def _generate_chapters(self, duration_seconds: int) -> str:
        if duration_seconds < 60:
            return "0:00 Intro\n0:10 Song"
        verse_start = 20
        chorus_start = verse_start + 50
        verse2_start = chorus_start + 45
        chorus2_start = verse2_start + 50
        bridge_start = chorus2_start + 45
        final_chorus = bridge_start + 30
        outro_start = final_chorus + 40
        return (
            f"0:00 Intro\n"
            f"0:{verse_start:02d} Verse 1\n"
            f"1:{chorus_start - 60:02d} Chorus\n"
            f"1:{verse2_start - 60:02d} Verse 2\n"
            f"2:{chorus2_start - 120:02d} Chorus\n"
            f"2:{bridge_start - 120:02d} Bridge\n"
            f"3:{final_chorus - 180:02d} Final Chorus\n"
            f"3:{outro_start - 180:02d} Outro"
        ) if duration_seconds >= 240 else "0:00 Intro\n0:20 Verse\n1:05 Chorus\n1:50 Verse 2\n2:30 Chorus\n3:00 Outro"

    def _build_tags(
        self,
        artist_config: dict,
        song_title: str,
        mood_tags: list[str],
        genre_tags: list[str],
    ) -> list[str]:
        core_tags = artist_config.get("seo", {}).get("core_tags", [])
        display_name = artist_config["display_name"].lower()
        song_tags = [
            song_title.lower(),
            f"{song_title.lower()} {display_name}",
            f"new hindi song {CURRENT_YEAR}",
        ]
        mood_text_tags = [f"hindi {m} song" for m in mood_tags[:3]]
        genre_text_tags = [g.lower() for g in genre_tags[:3]]
        all_tags = core_tags + song_tags + mood_text_tags + genre_text_tags
        return list(dict.fromkeys(all_tags))[:30]

    def _build_hashtags(self, artist_id: str, mood_tags: list[str]) -> list[str]:
        rules = self._seo_rules["hashtag_groups"]
        core = rules.get(f"{artist_id}_core", [])
        genre_ht = rules.get("genre", [])[:4]
        mood_ht = rules.get("mood", [])[:4]
        ai_ht = rules.get("ai", [])[:3]
        reach_ht = rules.get("reach", [])[:4]
        return list(dict.fromkeys(core + genre_ht + mood_ht + ai_ht + reach_ht))[:25]

    def _build_hashtag_block(self, artist_id: str, mood_tags: list[str]) -> str:
        return " ".join(self._build_hashtags(artist_id, mood_tags))

    def _calculate_seo_score(self, metadata: dict) -> int:
        score = 0
        title = metadata.get("title", "")
        description = metadata.get("description", "")
        tags = metadata.get("tags", [])

        if 40 <= len(title) <= 100:
            score += 20
        if str(CURRENT_YEAR) in title:
            score += 5
        if len(description) > 500:
            score += 15
        if "#AIMusic" in description or "AI" in description:
            score += 10
        if len(tags) >= 20:
            score += 20
        if "0:00" in description or "chapters" in description.lower():
            score += 10
        if any(link in description for link in ["instagram", "spotify", "tiktok", "subscribe"]):
            score += 10
        if metadata.get("thumbnail_text"):
            score += 10

        return min(score, 100)

    def _apply_cover_overrides(
        self,
        result: dict,
        artist_id: str,
        artist_config: dict,
        song_title: str,
        reference_song_title: str,
        reference_artist_name: str,
        mood_tags: list[str],
    ) -> dict:
        """Patch a metadata result with cover-mode title and description rules.

        Cover titles must never name the reference song directly — only the
        emotional world is acknowledged via the inspiration_line.
        """
        display_name = artist_config["display_name"]
        primary_mood = mood_tags[0].title() if mood_tags else "Emotional"
        emotional_keyword = self._pick_emotional_keyword(mood_tags)

        cover_title = (
            f"{emotional_keyword} | {song_title} | {display_name} | "
            f"Hindi {primary_mood} Song {CURRENT_YEAR}"
        )
        if len(cover_title) > 100:
            cover_title = f"{song_title} | {display_name} | Hindi {primary_mood} Song {CURRENT_YEAR}"

        forbidden = self._seo_rules.get("cover_forbidden_title_patterns", [])
        for pattern in forbidden:
            if pattern.lower() in cover_title.lower():
                cover_title = f"{song_title} | {display_name} | Hindi {primary_mood} Song {CURRENT_YEAR}"
                break

        inspiration_template = self._seo_rules.get(
            "cover_description_inspiration_line",
            "Born from the same emotional world as '{reference_title}' — reimagined through the soul of {ai_artist}",
        )
        inspiration_line = inspiration_template.format(
            reference_title=reference_song_title,
            ai_artist=display_name,
        )

        existing_desc = result.get("description", "")
        result["title"] = cover_title
        result["description"] = f"{inspiration_line}\n\n{existing_desc}"
        result["cover_mode"] = True
        result["reference_song_title"] = reference_song_title
        result["reference_artist_name"] = reference_artist_name
        return result
