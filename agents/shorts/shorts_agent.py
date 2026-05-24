"""Shorts Agent — viral short-form clip timestamps, captions, and 9:16 video cuts."""

import re
import uuid
from pathlib import Path
from typing import Any

from agents.base_agent import BaseAgent

MAX_SHORT_DURATION = 59  # YouTube Shorts hard cap


class ShortsAgent(BaseAgent):
    def __init__(self, ffmpeg_processor=None, mock_mode: bool = False):
        super().__init__("ShortsAgent")
        self._ffmpeg = ffmpeg_processor
        self._mock_mode = mock_mode

    def _execute(
        self,
        artist_id: str,
        artist_config: dict,
        context: dict[str, Any],
        job_id: str,
    ) -> dict[str, Any]:
        lyrics_output = context.get("lyrics_output", {})
        audio_path = context.get("audio_path", "")
        video_path = context.get("video_path", "")
        audio_duration = context.get("audio_duration", 210.0)
        shorts_count = min(context.get("shorts_count", 3), 5)
        burn_captions = context.get("burn_captions", False)

        lyrics_text = lyrics_output.get("lyrics_text", "")
        hook_line = lyrics_output.get("hook_line", "")
        mood_tags = lyrics_output.get("mood_tags", [])
        suggested_titles = lyrics_output.get("suggested_titles", ["Untitled"])
        song_title = suggested_titles[0] if suggested_titles else "Untitled"
        display_name = artist_config["display_name"]

        windows = self._select_clip_windows(lyrics_text, audio_duration, hook_line, shorts_count)

        clips = []
        for i, window in enumerate(windows):
            clip_job_id = f"{job_id}_short_{i}"
            out_dir = Path("storage") / artist_id / "shorts"
            out_dir.mkdir(parents=True, exist_ok=True)

            video_out = str(out_dir / f"{clip_job_id}.mp4")
            srt_out = str(out_dir / f"{clip_job_id}.srt")

            if not self._mock_mode and self._ffmpeg and Path(video_path).exists():
                try:
                    self._ffmpeg.cut_short_clip(
                        input_path=video_path,
                        output_path=video_out,
                        start_seconds=window["start_seconds"],
                        duration_seconds=window["duration_seconds"],
                        reformat_vertical=True,
                    )
                except Exception as e:
                    self.logger.warning(f"Short clip {i} cut failed: {e}")
                    video_out = ""
            else:
                video_out = ""

            srt_lines = self._extract_lines_for_window(
                lyrics_text, window["start_seconds"], audio_duration
            )
            if srt_lines:
                self._write_srt(srt_lines, window["start_seconds"], window["duration_seconds"], Path(srt_out))
            else:
                srt_out = ""

            title = self._build_shorts_title(song_title, window["label"], display_name)
            caption = self._build_caption(hook_line, window["label"], mood_tags, artist_id, artist_config)
            hashtags = self._build_hashtags(artist_id, artist_config, mood_tags)

            clips.append({
                "clip_index": i,
                "start_seconds": window["start_seconds"],
                "duration_seconds": window["duration_seconds"],
                "label": window["label"],
                "video_path": video_out,
                "srt_path": srt_out,
                "caption_text": caption,
                "youtube_title": title,
                "hashtags": hashtags,
            })
            self.logger.info(f"Short {i} prepared: {window['label']} @ {window['start_seconds']:.0f}s")

        return {
            "clips": clips,
            "total_clips": len(clips),
            "song_title": song_title,
            "artist_id": artist_id,
        }

    # ── Clip window selection ─────────────────────────────────────────────────

    def _select_clip_windows(
        self,
        lyrics_text: str,
        audio_duration: float,
        hook_line: str,
        shorts_count: int,
    ) -> list[dict]:
        section_times = self._detect_section_times(lyrics_text, audio_duration)
        windows = []

        # Clip 0: Hook/Chorus — highest retention value
        chorus_start = section_times.get("CHORUS", section_times.get("chorus", audio_duration * 0.35))
        hook_start = max(0.0, chorus_start - 5.0)
        windows.append({
            "label": "chorus_hook",
            "start_seconds": hook_start,
            "duration_seconds": min(45.0, audio_duration - hook_start, MAX_SHORT_DURATION),
        })

        if shorts_count >= 2:
            # Clip 1: Intro teaser — first 30s
            windows.append({
                "label": "intro_teaser",
                "start_seconds": 0.0,
                "duration_seconds": min(30.0, audio_duration, MAX_SHORT_DURATION),
            })

        if shorts_count >= 3:
            # Clip 2: Bridge/emotional peak
            bridge_start = section_times.get("BRIDGE", section_times.get("bridge", audio_duration * 0.70))
            bridge_start = max(0.0, bridge_start - 3.0)
            windows.append({
                "label": "bridge_climax",
                "start_seconds": bridge_start,
                "duration_seconds": min(40.0, audio_duration - bridge_start, MAX_SHORT_DURATION),
            })

        if shorts_count >= 4 and audio_duration > 120:
            # Clip 3: Second chorus
            chorus2_start = min(chorus_start + 60.0, audio_duration - 45.0)
            windows.append({
                "label": "chorus_2",
                "start_seconds": max(0.0, chorus2_start),
                "duration_seconds": min(45.0, audio_duration - chorus2_start, MAX_SHORT_DURATION),
            })

        if shorts_count >= 5 and audio_duration > 150:
            # Clip 4: Outro emotion
            outro_start = max(0.0, audio_duration - 45.0)
            windows.append({
                "label": "outro_emotion",
                "start_seconds": outro_start,
                "duration_seconds": min(44.0, audio_duration - outro_start, MAX_SHORT_DURATION),
            })

        return windows[:shorts_count]

    def _detect_section_times(
        self, lyrics_text: str, audio_duration: float
    ) -> dict[str, float]:
        """Approximate section start times by proportional distribution."""
        sections = []
        for line in lyrics_text.splitlines():
            m = re.match(r"^\[(.+?)\]$", line.strip())
            if m:
                sections.append(m.group(1).upper())

        if not sections:
            return {}

        # Proportionally space unique sections across song duration
        unique_sections = list(dict.fromkeys(sections))
        n = len(unique_sections)
        return {s: (i / n) * audio_duration for i, s in enumerate(unique_sections)}

    # ── SRT generation ────────────────────────────────────────────────────────

    def _extract_lines_for_window(
        self, lyrics_text: str, start_sec: float, audio_duration: float
    ) -> list[str]:
        all_lines = [
            l.strip() for l in lyrics_text.splitlines()
            if l.strip() and not re.match(r"^\[.+\]$", l.strip())
        ]
        if not all_lines:
            return []
        # Take lines from approximate position
        ratio = start_sec / max(audio_duration, 1)
        start_idx = int(ratio * len(all_lines))
        return all_lines[start_idx:start_idx + 8]

    def _write_srt(
        self,
        lines: list[str],
        start_offset: float,
        duration: float,
        output_path: Path,
    ) -> None:
        if not lines:
            return
        per_line = duration / len(lines)
        entries = []
        for i, line in enumerate(lines):
            t_start = start_offset + i * per_line
            t_end = t_start + per_line - 0.1
            entries.append(
                f"{i + 1}\n"
                f"{self._fmt_srt_time(t_start)} --> {self._fmt_srt_time(t_end)}\n"
                f"{line}\n"
            )
        output_path.write_text("\n".join(entries), encoding="utf-8")

    @staticmethod
    def _fmt_srt_time(seconds: float) -> str:
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = int(seconds % 60)
        ms = int((seconds - int(seconds)) * 1000)
        return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

    # ── Metadata helpers ──────────────────────────────────────────────────────

    def _build_shorts_title(self, song_title: str, label: str, display_name: str) -> str:
        label_map = {
            "chorus_hook": "Best Part",
            "intro_teaser": "Opening",
            "bridge_climax": "Emotional Peak",
            "chorus_2": "Chorus",
            "outro_emotion": "Ending",
        }
        label_display = label_map.get(label, label.replace("_", " ").title())
        title = f"{song_title} | {label_display} | {display_name} | #Shorts"
        return title[:100]

    def _build_caption(
        self,
        hook_line: str,
        label: str,
        mood_tags: list[str],
        artist_id: str,
        artist_config: dict,
    ) -> str:
        hooks = {
            "chorus_hook": f"🎵 {hook_line}\n\nThis one hits different at night... 💔",
            "intro_teaser": f"Starting with feelings you can't explain...\n\n🎵 {hook_line}",
            "bridge_climax": f"The part that breaks you every time 💔\n\n🎵 {hook_line}",
            "chorus_2": f"That chorus that lives rent-free in your head 🌧️\n\n🎵 {hook_line}",
            "outro_emotion": f"The ending that stays with you... 🌙\n\n🎵 {hook_line}",
        }
        base = hooks.get(label, f"🎵 {hook_line}")
        return base

    def _build_hashtags(
        self, artist_id: str, artist_config: dict, mood_tags: list[str]
    ) -> str:
        core_tags = artist_config.get("seo", {}).get("core_tags", [])
        artist_tag = f"#{artist_config['display_name'].replace(' ', '')}"
        mood_ht = [f"#{t.title()}" for t in mood_tags[:3]]
        base = [artist_tag, "#Shorts", "#HindiShorts", "#AIMusicShorts", "#EmotionalShorts"]
        base += mood_ht
        base += [f"#{t.replace(' ', '').title()}" for t in core_tags[:3]]
        return " ".join(list(dict.fromkeys(base))[:20])
