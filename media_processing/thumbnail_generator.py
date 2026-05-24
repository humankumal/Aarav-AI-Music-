"""Thumbnail generator — Pillow-based 1280×720 branded thumbnails per artist."""

import logging
import uuid
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

try:
    from PIL import Image, ImageDraw, ImageFont, ImageFilter
    PILLOW_AVAILABLE = True
except ImportError:
    PILLOW_AVAILABLE = False
    logger.warning("Pillow not installed — thumbnail generation unavailable")

CANVAS_W, CANVAS_H = 1280, 720
FONT_DIR_TPL = "agents/branding/assets/{artist_id}/fonts"


class ThumbnailGenerator:
    def __init__(self, output_dir: str | Path = "storage"):
        self._output_dir = Path(output_dir)

    def generate(
        self,
        artist_id: str,
        artist_config: dict,
        song_title: str,
        hook_line: str = "",
        mood_tags: list[str] | None = None,
        job_id: str | None = None,
    ) -> str:
        """Generate a 1280×720 JPEG thumbnail. Returns file path."""
        job_id = job_id or str(uuid.uuid4())
        out_path = self._output_dir / artist_id / "thumbnails" / f"{job_id}_thumb.jpg"
        out_path.parent.mkdir(parents=True, exist_ok=True)

        if not PILLOW_AVAILABLE:
            logger.warning("Pillow unavailable — skipping thumbnail generation")
            return ""

        visual = artist_config.get("visual_style", {})
        branding = artist_config.get("branding", {})
        palette = self._parse_palette(visual.get("primary_palette", ["#1a1a2e", "#0f3460"]))
        style = branding.get("thumbnail_text_style", "minimal_dramatic")

        fonts = self._load_fonts(artist_id, visual)

        canvas = Image.new("RGB", (CANVAS_W, CANVAS_H))
        canvas = self._build_background(canvas, palette, artist_id)
        canvas = self._add_vignette(canvas)
        canvas = self._render_title_text(canvas, song_title, hook_line, palette, fonts, style, branding)
        canvas = self._add_artist_watermark(canvas, artist_id, visual)
        canvas = self._add_decorative_lines(canvas, palette, style)

        canvas.save(str(out_path), "JPEG", quality=92, optimize=True)
        logger.info(f"Thumbnail generated → {out_path}")
        return str(out_path)

    # ── Background ────────────────────────────────────────────────────────────

    def _build_background(self, canvas: "Image.Image", palette: dict, artist_id: str) -> "Image.Image":
        draw = ImageDraw.Draw(canvas)
        top_color = palette["bg_top"]
        bot_color = palette["bg_bottom"]
        for y in range(CANVAS_H):
            t = y / CANVAS_H
            r = int(top_color[0] + (bot_color[0] - top_color[0]) * t)
            g = int(top_color[1] + (bot_color[1] - top_color[1]) * t)
            b = int(top_color[2] + (bot_color[2] - top_color[2]) * t)
            draw.line([(0, y), (CANVAS_W, y)], fill=(r, g, b))
        return canvas

    def _add_vignette(self, canvas: "Image.Image") -> "Image.Image":
        vignette = Image.new("RGBA", (CANVAS_W, CANVAS_H), (0, 0, 0, 0))
        draw = ImageDraw.Draw(vignette)
        # Four corner gradient ellipses at 35% opacity
        for cx, cy in [(0, 0), (CANVAS_W, 0), (0, CANVAS_H), (CANVAS_W, CANVAS_H)]:
            draw.ellipse(
                [cx - 500, cy - 350, cx + 500, cy + 350],
                fill=(0, 0, 0, 90),
            )
        canvas_rgba = canvas.convert("RGBA")
        canvas_rgba = Image.alpha_composite(canvas_rgba, vignette)
        return canvas_rgba.convert("RGB")

    # ── Text rendering ────────────────────────────────────────────────────────

    def _render_title_text(
        self,
        canvas: "Image.Image",
        song_title: str,
        hook_line: str,
        palette: dict,
        fonts: dict,
        style: str,
        branding: dict,
    ) -> "Image.Image":
        draw = ImageDraw.Draw(canvas)
        accent = palette["accent"]
        light = palette["text_light"]

        if style == "elegant_golden":
            # Aarohi: centered serif title, golden accent
            self._draw_centered_text(draw, song_title, fonts["title_large"], accent, CANVAS_H // 2 - 60)
            if hook_line:
                self._draw_centered_text(draw, hook_line, fonts["subtitle"], light, CANVAS_H // 2 + 40)
        else:
            # Aarav (minimal_dramatic): large dramatic title upper-center
            self._draw_centered_text(draw, song_title, fonts["title_large"], accent, CANVAS_H // 2 - 70)
            if hook_line:
                self._draw_centered_text(draw, hook_line, fonts["subtitle"], light, CANVAS_H // 2 + 50)

        return canvas

    def _draw_centered_text(
        self,
        draw: "ImageDraw.ImageDraw",
        text: str,
        font: "ImageFont.ImageFont",
        color: tuple,
        y: int,
    ) -> None:
        bbox = draw.textbbox((0, 0), text, font=font)
        text_w = bbox[2] - bbox[0]
        x = (CANVAS_W - text_w) // 2
        # Drop shadow
        draw.text((x + 2, y + 2), text, font=font, fill=(0, 0, 0, 120))
        draw.text((x, y), text, font=font, fill=color)

    def _add_decorative_lines(
        self, canvas: "Image.Image", palette: dict, style: str
    ) -> "Image.Image":
        draw = ImageDraw.Draw(canvas)
        accent = palette["accent"]
        center_y = CANVAS_H // 2
        line_y = center_y - 80 if style == "minimal_dramatic" else center_y - 90
        draw.line(
            [(CANVAS_W // 2 - 160, line_y), (CANVAS_W // 2 + 160, line_y)],
            fill=accent, width=2,
        )
        return canvas

    def _add_artist_watermark(
        self, canvas: "Image.Image", artist_id: str, visual_style: dict
    ) -> "Image.Image":
        wm_path = Path(f"agents/branding/assets/{artist_id}/watermark.png")
        if not wm_path.exists():
            return canvas
        try:
            wm = Image.open(wm_path).convert("RGBA")
            opacity = int(visual_style.get("branding", {}).get("watermark_opacity", 0.70) * 255)
            wm_with_alpha = Image.new("RGBA", wm.size)
            for px in range(wm.width):
                for py in range(wm.height):
                    r, g, b, a = wm.getpixel((px, py))
                    wm_with_alpha.putpixel((px, py), (r, g, b, int(a * opacity / 255)))
            margin = 15
            x = CANVAS_W - wm.width - margin
            y = CANVAS_H - wm.height - margin
            canvas_rgba = canvas.convert("RGBA")
            canvas_rgba.paste(wm_with_alpha, (x, y), wm_with_alpha)
            return canvas_rgba.convert("RGB")
        except Exception as e:
            logger.warning(f"Watermark composite failed: {e}")
            return canvas

    # ── Font loading ──────────────────────────────────────────────────────────

    def _load_fonts(self, artist_id: str, visual_style: dict) -> dict:
        font_dir = Path(FONT_DIR_TPL.format(artist_id=artist_id))
        fonts = {}
        sizes = {"title_large": 72, "title_medium": 52, "subtitle": 34}
        for key, size in sizes.items():
            fonts[key] = self._try_load_font(font_dir, visual_style.get("font_primary", ""), size)
        return fonts

    def _try_load_font(self, font_dir: Path, font_name: str, size: int) -> "ImageFont.ImageFont":
        # Try to load artist font file first
        for ext in [".ttf", ".otf"]:
            candidate = font_dir / f"{font_name}{ext}"
            if candidate.exists():
                try:
                    return ImageFont.truetype(str(candidate), size)
                except OSError:
                    pass
        # Search system fonts as fallback
        for search_dir in [Path("/usr/share/fonts"), Path("/usr/local/share/fonts")]:
            for f in search_dir.rglob("*.ttf"):
                try:
                    return ImageFont.truetype(str(f), size)
                except OSError:
                    continue
        return ImageFont.load_default()

    # ── Palette parsing ───────────────────────────────────────────────────────

    def _parse_palette(self, hex_palette: list[str]) -> dict:
        def h2rgb(h: str) -> tuple:
            h = h.lstrip("#")
            return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))

        colors = [h2rgb(c) for c in hex_palette]
        # Determine if background is dark (Aarav) or light (Aarohi)
        bg_lum = sum(colors[0]) / 3
        is_dark = bg_lum < 128

        return {
            "bg_top": colors[0],
            "bg_bottom": colors[1] if len(colors) > 1 else colors[0],
            "accent": colors[-1] if len(colors) > 2 else colors[0],
            "text_light": (240, 240, 240) if is_dark else (30, 30, 30),
            "is_dark": is_dark,
        }
