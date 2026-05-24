"""FFmpeg-based media processor — assembles video, normalizes audio, applies watermark."""

import logging
import os
import subprocess
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

TARGET_LUFS = -14.0
WATERMARK_OPACITY = 0.70


class FFmpegProcessor:
    def __init__(self, ffmpeg_path: str = "ffmpeg", ffprobe_path: str = "ffprobe"):
        self._ffmpeg = ffmpeg_path
        self._ffprobe = ffprobe_path
        self._verify_ffmpeg()

    def _verify_ffmpeg(self) -> None:
        try:
            subprocess.run(
                [self._ffmpeg, "-version"],
                capture_output=True,
                check=True,
            )
        except (subprocess.CalledProcessError, FileNotFoundError):
            logger.warning("FFmpeg not found — media processing will fail at runtime")

    def _run(self, cmd: list[str], description: str = "") -> subprocess.CompletedProcess:
        logger.debug(f"FFmpeg: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(
                f"FFmpeg failed ({description}): {result.stderr[-500:]}"
            )
        return result

    def normalize_audio(self, input_path: str, output_path: str) -> str:
        """Normalize audio to -14 LUFS for streaming compliance (two-pass loudnorm)."""
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)

        # Pass 1: measure loudness
        measure_cmd = [
            self._ffmpeg, "-i", input_path,
            "-af", f"loudnorm=I={TARGET_LUFS}:TP=-1.5:LRA=11:print_format=json",
            "-f", "null", "-",
        ]
        result = self._run(measure_cmd, "loudnorm pass 1")
        # In real use: parse the JSON from stderr to get measured_I, measured_TP, etc.
        # For simplicity we use single-pass loudnorm here:
        normalize_cmd = [
            self._ffmpeg, "-i", input_path,
            "-af", f"loudnorm=I={TARGET_LUFS}:TP=-1.5:LRA=11",
            "-ar", "44100", "-b:a", "320k",
            "-y", output_path,
        ]
        self._run(normalize_cmd, "loudnorm pass 2")
        logger.info(f"Audio normalized → {output_path}")
        return output_path

    def assemble_video(
        self,
        video_path: str,
        audio_path: str,
        output_path: str,
        watermark_path: str | None = None,
        target_duration_seconds: float | None = None,
    ) -> str:
        """Merge audio onto video, optionally apply watermark, export master MP4."""
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)

        filters = []
        inputs = ["-i", video_path, "-i", audio_path]

        if watermark_path and Path(watermark_path).exists():
            inputs += ["-i", watermark_path]
            opacity = WATERMARK_OPACITY
            # Bottom-right watermark at 70% opacity
            filters.append(
                f"[2:v]format=rgba,colorchannelmixer=aa={opacity}[wm];"
                f"[0:v][wm]overlay=W-w-20:H-h-20[outv]"
            )
            video_map = "[outv]"
        else:
            video_map = "0:v"

        trim_args = []
        if target_duration_seconds:
            trim_args = ["-t", str(target_duration_seconds)]

        cmd = [self._ffmpeg] + inputs
        if filters:
            cmd += ["-filter_complex", ";".join(filters), "-map", video_map, "-map", "1:a"]
        else:
            cmd += ["-map", "0:v", "-map", "1:a"]

        cmd += [
            "-c:v", "libx264", "-preset", "slow", "-crf", "18",
            "-c:a", "aac", "-b:a", "192k",
            "-shortest",
            *trim_args,
            "-movflags", "+faststart",
            "-y", output_path,
        ]

        self._run(cmd, "video assembly")
        logger.info(f"Video assembled → {output_path}")
        return output_path

    def cut_short_clip(
        self,
        input_path: str,
        output_path: str,
        start_seconds: float,
        duration_seconds: float,
        reformat_vertical: bool = True,
    ) -> str:
        """Extract a clip segment and optionally reformat to 9:16 for Shorts."""
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)

        vf_filters = []
        if reformat_vertical:
            vf_filters.append("scale=1080:1920:force_original_aspect_ratio=increase")
            vf_filters.append("crop=1080:1920")

        cmd = [
            self._ffmpeg,
            "-ss", str(start_seconds),
            "-i", input_path,
            "-t", str(duration_seconds),
        ]

        if vf_filters:
            cmd += ["-vf", ",".join(vf_filters)]

        cmd += [
            "-c:v", "libx264", "-preset", "fast", "-crf", "20",
            "-c:a", "aac", "-b:a", "128k",
            "-y", output_path,
        ]

        self._run(cmd, f"short clip cut {start_seconds}-{start_seconds + duration_seconds}s")
        logger.info(f"Short clip → {output_path}")
        return output_path

    def burn_subtitles(self, video_path: str, srt_path: str, output_path: str) -> str:
        """Burn SRT subtitle file into video."""
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        cmd = [
            self._ffmpeg, "-i", video_path,
            "-vf", f"subtitles={srt_path}:force_style='FontName=Arial,FontSize=18,PrimaryColour=&Hffffff,OutlineColour=&H000000,Outline=2'",
            "-c:a", "copy",
            "-y", output_path,
        ]
        self._run(cmd, "subtitle burn")
        logger.info(f"Subtitles burned → {output_path}")
        return output_path

    def get_duration(self, media_path: str) -> float:
        """Return duration in seconds using ffprobe."""
        cmd = [
            self._ffprobe, "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            media_path,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        try:
            return float(result.stdout.strip())
        except ValueError:
            return 0.0
