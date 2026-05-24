"""Lyric video generator — Pillow frames + FFmpeg assembly, no external video AI needed."""

import logging
import os
import re
import shutil
import uuid
from dataclasses import dataclass
from multiprocessing import Pool, cpu_count
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

try:
    from PIL import Image, ImageDraw, ImageFont
    PILLOW_AVAILABLE = True
except ImportError:
    PILLOW_AVAILABLE = False

# All text constrained to center 1080px so Shorts crop (center strip) is always clean
SAFE_ZONE_W = 1080
FPS = 24
FADE_FRAMES = 8  # fade in/out per lyric line
FONT_DIR_TPL = "agents/branding/assets/{artist_id}/fonts"

CANVAS_SIZES = {
    "full": (1920, 1080),
    "short": (1080, 1920),
}


@dataclass
class LyricLine:
    text: str
    section: str
    line_index: int


def _render_frame_worker(args: tuple) -> None:
    """Top-level function for multiprocessing (must be picklable)."""
    (
        frame_path, line_text, prev_text, next_text,
        canvas_w, canvas_h, bg_top, bg_bottom, accent, text_light,
        font_data, frame_i, total_frames,
    ) = args

    from PIL import Image, ImageDraw, ImageFont

    img = Image.new("RGB", (canvas_w, canvas_h))
    draw = ImageDraw.Draw(img)

    # Background gradient
    for y in range(canvas_h):
        t = y / canvas_h
        r = int(bg_top[0] + (bg_bottom[0] - bg_top[0]) * t)
        g = int(bg_top[1] + (bg_bottom[1] - bg_top[1]) * t)
        b = int(bg_top[2] + (bg_bottom[2] - bg_top[2]) * t)
        draw.line([(0, y), (canvas_w, y)], fill=(r, g, b))

    # Fade alpha
    fade_alpha = 1.0
    if frame_i < FADE_FRAMES:
        fade_alpha = frame_i / FADE_FRAMES
    elif frame_i > total_frames - FADE_FRAMES:
        fade_alpha = (total_frames - frame_i) / FADE_FRAMES

    center_y = canvas_h // 2

    def load_font(size):
        try:
            return ImageFont.truetype(font_data, size) if font_data else ImageFont.load_default()
        except Exception:
            return ImageFont.load_default()

    def draw_line_text(text, y_pos, font, color, alpha_mult):
        if not text:
            return
        alpha = int(255 * min(fade_alpha * alpha_mult, 1.0))
        r, g, b = color
        fill = (r, g, b, alpha)
        overlay = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))
        odraw = ImageDraw.Draw(overlay)
        bbox = odraw.textbbox((0, 0), text, font=font)
        tw = bbox[2] - bbox[0]
        x = max((canvas_w - tw) // 2, (canvas_w - SAFE_ZONE_W) // 2)
        odraw.text((x + 2, y_pos + 2), text, font=font, fill=(0, 0, 0, int(alpha * 0.4)))
        odraw.text((x, y_pos), text, font=font, fill=fill)
        base = img.convert("RGBA")
        merged = Image.alpha_composite(base, overlay)
        img.paste(merged.convert("RGB"))

    font_main = load_font(56)
    font_small = load_font(38)

    if prev_text:
        draw_line_text(prev_text, center_y - 110, font_small, text_light, 0.40)
    draw_line_text(line_text, center_y - 28, font_main, accent, 1.0)
    if next_text:
        draw_line_text(next_text, center_y + 80, font_small, text_light, 0.25)

    img.save(frame_path, "JPEG", quality=85)


class LyricVideoGenerator:
    def __init__(self, ffmpeg_processor=None, output_dir: str | Path = "storage"):
        self._ffmpeg = ffmpeg_processor
        self._output_dir = Path(output_dir)

    def generate(
        self,
        artist_id: str,
        artist_config: dict,
        lyrics_text: str,
        audio_path: str,
        job_id: str | None = None,
        video_type: str = "full",
        mock_mode: bool = False,
    ) -> str:
        job_id = job_id or str(uuid.uuid4())
        canvas_size = CANVAS_SIZES.get(video_type, CANVAS_SIZES["full"])
        out_path = (
            self._output_dir / artist_id / "videos" / f"{job_id}_lyric_video.mp4"
        )
        out_path.parent.mkdir(parents=True, exist_ok=True)

        if not PILLOW_AVAILABLE or mock_mode:
            return self._mock_generate(artist_id, audio_path, job_id, video_type)

        visual = artist_config.get("visual_style", {})
        palette = self._build_palette(visual.get("primary_palette", ["#1a1a2e", "#0f3460"]))
        font_path = self._resolve_font(artist_id, visual)

        lines = self._parse_lyrics_to_lines(lyrics_text)
        audio_duration = self._get_audio_duration(audio_path)
        timestamps = self._calculate_line_timestamps(lines, audio_duration)

        frames_dir = self._output_dir / artist_id / "temp" / job_id / "frames"
        frames_dir.mkdir(parents=True, exist_ok=True)

        try:
            self._render_all_frames(
                lines=lines,
                timestamps=timestamps,
                frames_dir=frames_dir,
                canvas_size=canvas_size,
                palette=palette,
                font_path=font_path,
            )
            self._frames_to_video(frames_dir, audio_path, str(out_path))
        finally:
            shutil.rmtree(str(frames_dir.parent), ignore_errors=True)

        logger.info(f"Lyric video generated → {out_path}")
        return str(out_path)

    # ── Lyrics parsing ────────────────────────────────────────────────────────

    def _parse_lyrics_to_lines(self, lyrics_text: str) -> list[LyricLine]:
        lines = []
        current_section = "INTRO"
        line_index = 0
        for raw in lyrics_text.splitlines():
            stripped = raw.strip()
            section_match = re.match(r"^\[(.+?)\]$", stripped)
            if section_match:
                current_section = section_match.group(1).upper()
                continue
            if stripped:
                lines.append(LyricLine(text=stripped, section=current_section, line_index=line_index))
                line_index += 1
        return lines

    def _calculate_line_timestamps(
        self, lines: list[LyricLine], audio_duration: float
    ) -> list[tuple[float, float]]:
        if not lines:
            return []
        # Count blank-line pauses between sections
        section_changes = sum(
            1 for i in range(1, len(lines)) if lines[i].section != lines[i - 1].section
        )
        pause_time = section_changes * 2.0
        available = audio_duration - pause_time
        per_line = available / len(lines) if lines else 3.0

        timestamps = []
        current_time = 0.0
        prev_section = lines[0].section if lines else ""
        for line in lines:
            if line.section != prev_section:
                current_time += 2.0  # section pause
                prev_section = line.section
            end_time = current_time + per_line
            timestamps.append((current_time, end_time))
            current_time = end_time
        return timestamps

    # ── Frame rendering ───────────────────────────────────────────────────────

    def _render_all_frames(
        self,
        lines: list[LyricLine],
        timestamps: list[tuple[float, float]],
        frames_dir: Path,
        canvas_size: tuple,
        palette: dict,
        font_path: str | None,
    ) -> None:
        canvas_w, canvas_h = canvas_size
        frame_args = []
        global_frame = 0

        for idx, (line, (start, end)) in enumerate(zip(lines, timestamps)):
            prev_text = lines[idx - 1].text if idx > 0 else ""
            next_text = lines[idx + 1].text if idx < len(lines) - 1 else ""
            n_frames = max(1, int((end - start) * FPS))

            # Section transition: 12 dark frames
            if idx > 0 and lines[idx].section != lines[idx - 1].section:
                for _ in range(12):
                    fp = str(frames_dir / f"frame_{global_frame:06d}.jpg")
                    frame_args.append((
                        fp, "", "", "",
                        canvas_w, canvas_h,
                        palette["bg_top"], palette["bg_bottom"],
                        palette["accent"], palette["text_light"],
                        font_path, 0, 1,
                    ))
                    global_frame += 1

            for fi in range(n_frames):
                fp = str(frames_dir / f"frame_{global_frame:06d}.jpg")
                frame_args.append((
                    fp, line.text, prev_text, next_text,
                    canvas_w, canvas_h,
                    palette["bg_top"], palette["bg_bottom"],
                    palette["accent"], palette["text_light"],
                    font_path, fi, n_frames,
                ))
                global_frame += 1

        workers = max(1, cpu_count() - 1)
        logger.info(f"Rendering {len(frame_args)} frames with {workers} workers…")
        with Pool(processes=workers) as pool:
            pool.map(_render_frame_worker, frame_args)

    def _frames_to_video(self, frames_dir: Path, audio_path: str, output_path: str) -> None:
        if not self._ffmpeg:
            raise RuntimeError("FFmpegProcessor required for video assembly")
        cmd = [
            self._ffmpeg._ffmpeg,
            "-framerate", str(FPS),
            "-i", str(frames_dir / "frame_%06d.jpg"),
            "-i", audio_path,
            "-c:v", "libx264", "-preset", "slow", "-crf", "18",
            "-c:a", "aac", "-b:a", "192k",
            "-shortest",
            "-movflags", "+faststart",
            "-y", output_path,
        ]
        self._ffmpeg._run(cmd, "lyric video assembly")

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _build_palette(self, hex_palette: list[str]) -> dict:
        def h2rgb(h: str) -> tuple:
            h = h.lstrip("#")
            return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))

        colors = [h2rgb(c) for c in hex_palette]
        bg_lum = sum(colors[0]) / 3
        is_dark = bg_lum < 128
        return {
            "bg_top": colors[0],
            "bg_bottom": colors[1] if len(colors) > 1 else colors[0],
            "accent": colors[-1] if len(colors) > 2 else colors[0],
            "text_light": (230, 230, 230) if is_dark else (30, 30, 30),
        }

    def _resolve_font(self, artist_id: str, visual_style: dict) -> str | None:
        font_dir = Path(FONT_DIR_TPL.format(artist_id=artist_id))
        font_name = visual_style.get("font_primary", "")
        for ext in [".ttf", ".otf"]:
            candidate = font_dir / f"{font_name}{ext}"
            if candidate.exists():
                return str(candidate)
        for search_dir in [Path("/usr/share/fonts"), Path("/usr/local/share/fonts")]:
            for f in search_dir.rglob("*.ttf"):
                return str(f)  # first available system font
        return None

    def _get_audio_duration(self, audio_path: str) -> float:
        if self._ffmpeg and Path(audio_path).exists():
            return self._ffmpeg.get_duration(audio_path)
        return 210.0

    def _mock_generate(
        self, artist_id: str, audio_path: str, job_id: str, video_type: str
    ) -> str:
        """Generate a minimal valid MP4 (5 frames) without full rendering."""
        if not PILLOW_AVAILABLE:
            return ""

        canvas_size = CANVAS_SIZES.get(video_type, CANVAS_SIZES["full"])
        out_path = self._output_dir / artist_id / "videos" / f"{job_id}_lyric_video.mp4"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        frames_dir = self._output_dir / artist_id / "temp" / job_id / "frames"
        frames_dir.mkdir(parents=True, exist_ok=True)

        try:
            for i in range(5):
                img = Image.new("RGB", canvas_size, color=(26, 26, 46))
                draw = ImageDraw.Draw(img)
                draw.text((50, canvas_size[1] // 2), f"[MOCK LYRIC VIDEO]", fill=(233, 69, 96))
                img.save(str(frames_dir / f"frame_{i:06d}.jpg"), "JPEG", quality=85)

            if self._ffmpeg:
                cmd = [
                    self._ffmpeg._ffmpeg,
                    "-framerate", "1",
                    "-i", str(frames_dir / "frame_%06d.jpg"),
                    "-i", audio_path,
                    "-c:v", "libx264", "-preset", "ultrafast",
                    "-c:a", "aac", "-b:a", "128k",
                    "-shortest",
                    "-y", str(out_path),
                ]
                try:
                    self._ffmpeg._run(cmd, "mock video")
                except Exception as e:
                    logger.warning(f"Mock video assembly failed: {e}")
                    return ""
        finally:
            shutil.rmtree(str(frames_dir.parent), ignore_errors=True)

        return str(out_path)
