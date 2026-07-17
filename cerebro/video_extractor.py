"""Extractor de frames desde videos de Instagram/TikTok.

Usa yt-dlp para descargar videos y moviepy para extraer frames clave.
"""

from __future__ import annotations

import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

FRAMES_DIR = Path(__file__).parent / "data" / "frames"


@dataclass
class VideoInfo:
    """Información de un video descargado."""
    url: str
    video_id: str
    titulo: str = ""
    autor: str = ""
    duracion: float = 0.0
    plataforma: str = ""
    local_path: Path | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ExtractedFrame:
    """Un frame extraído de un video."""
    frame_number: int
    timestamp: float  # segundos
    path: Path
    width: int = 0
    height: int = 0
    quality_score: float = 0.0  # 0-1, qué tan "buena" es la imagen


class VideoExtractor:
    """Extrae frames clave de videos de redes sociales."""

    def __init__(self, output_dir: Path | str | None = None, max_frames: int = 10):
        self.output_dir = Path(output_dir) if output_dir else FRAMES_DIR
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.max_frames = max_frames

    def descargar_video(self, url: str) -> VideoInfo:
        """Descarga un video desde Instagram/TikTok usando yt-dlp."""
        video_id = self._extraer_video_id(url)
        plataforma = self._detectar_plataforma(url)

        tmp_dir = tempfile.mkdtemp(prefix="cerebro_")
        output_path = Path(tmp_dir) / f"{video_id}.%(ext)s"

        cmd = [
            "yt-dlp",
            "--no-playlist",
            "-f", "best[height<=1080]",
            "--output", str(output_path),
            "--write-info-json",
            url,
        ]

        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=120
            )
            if result.returncode != 0:
                raise RuntimeError(f"yt-dlp error: {result.stderr}")

            # Buscar el archivo descargado
            for f in Path(tmp_dir).iterdir():
                if video_id in f.name and f.suffix in (".mp4", ".webm", ".mkv", ".jpg"):
                    info = VideoInfo(
                        url=url,
                        video_id=video_id,
                        plataforma=plataforma,
                        local_path=f,
                    )
                    # Intentar leer info adicional
                    info_file = Path(tmp_dir) / f"{video_id}.info.json"
                    if info_file.exists():
                        import json
                        meta = json.loads(info_file.read_text())
                        info.titulo = meta.get("title", "")
                        info.autor = meta.get("uploader", "")
                        info.duracion = meta.get("duration", 0)
                    return info

            raise RuntimeError(f"No se encontro el video descargado para {video_id}")

        except FileNotFoundError:
            raise RuntimeError(
                "yt-dlp no instalado. Ejecutar: pip install yt-dlp"
            )

    def extraer_frames(
        self, video_info: VideoInfo, n_frames: int | None = None
    ) -> list[ExtractedFrame]:
        """Extrae frames clave de un video descargado."""
        if not video_info.local_path or not video_info.local_path.exists():
            raise FileNotFoundError(f"Video no encontrado: {video_info.local_path}")

        n = n_frames or self.max_frames
        video_dir = self.output_dir / video_info.video_id
        video_dir.mkdir(parents=True, exist_ok=True)

        frames = []

        try:
            from moviepy.editor import VideoFileClip

            clip = VideoFileClip(str(video_info.local_path))
            duracion = clip.duration

            if duracion <= 0:
                clip.close()
                return []

            # Calcular timestamps distribuidos均匀mente
            if n >= duracion:
                timestamps = [i for i in range(int(duracion))]
            else:
                step = duracion / n
                timestamps = [i * step for i in range(n)]

            for i, ts in enumerate(timestamps):
                frame_path = video_dir / f"frame_{i:03d}_{int(ts)}s.jpg"

                try:
                    frame = clip.get_frame(ts)
                    self._guardar_frame(frame, frame_path)

                    extracted = ExtractedFrame(
                        frame_number=i,
                        timestamp=ts,
                        path=frame_path,
                        width=clip.size[0] if clip.size else 0,
                        height=clip.size[1] if clip.size else 0,
                        quality_score=self._calcular_calidad(frame_path),
                    )
                    frames.append(extracted)
                except Exception:
                    continue

            clip.close()

        except ImportError:
            raise RuntimeError(
                "moviepy no instalado. Ejecutar: pip install moviepy"
            )

        # Ordenar por calidad y devolver los mejores
        frames.sort(key=lambda f: f.quality_score, reverse=True)
        return frames[:n]

    def extraer_de_url(
        self, url: str, n_frames: int | None = None
    ) -> tuple[VideoInfo, list[ExtractedFrame]]:
        """Flujo completo: descargar video + extraer frames."""
        info = self.descargar_video(url)
        frames = self.extraer_frames(info, n_frames)
        return info, frames

    def _extraer_video_id(self, url: str) -> str:
        """Extrae el ID del video desde la URL."""
        # Instagram: /reel/XXXXX o /p/XXXXX
        if "instagram.com" in url:
            parts = url.rstrip("/").split("/")
            for i, part in enumerate(parts):
                if part in ("reel", "p", "tv") and i + 1 < len(parts):
                    return f"ig_{parts[i + 1]}"
            return f"ig_{hash(url) % 100000}"

        # TikTok: /video/XXXXX
        if "tiktok.com" in url:
            parts = url.rstrip("/").split("/")
            for i, part in enumerate(parts):
                if part == "video" and i + 1 < len(parts):
                    return f"tt_{parts[i + 1]}"
            return f"tt_{hash(url) % 100000}"

        return f"vid_{hash(url) % 100000}"

    def _detectar_plataforma(self, url: str) -> str:
        if "instagram.com" in url:
            return "instagram"
        if "tiktok.com" in url:
            return "tiktok"
        return "desconocida"

    def _guardar_frame(self, frame: Any, path: Path) -> None:
        """Guarda un frame numpy array como JPEG."""
        from PIL import Image
        import numpy as np

        img = Image.fromarray(frame.astype(np.uint8))
        img.save(str(path), "JPEG", quality=90)

    def _calcular_calidad(self, path: Path) -> float:
        """Calcula un score de calidad simple basado en la imagen."""
        try:
            from PIL import Image
            img = Image.open(path)
            w, h = img.size

            # Score basado en resolución
            resolution_score = min(1.0, (w * h) / (1920 * 1080))

            # Score basado en nitidez (aproximado con varianza)
            gray = img.convert("L")
            pixels = list(gray.getdata())
            mean = sum(pixels) / len(pixels)
            variance = sum((p - mean) ** 2 for p in pixels) / len(pixels)
            sharpness_score = min(1.0, variance / 3000)

            return (resolution_score * 0.6 + sharpness_score * 0.4)

        except Exception:
            return 0.5

    def limpiar_frames(self, video_id: str | None = None) -> int:
        """Limpia frames extraídos."""
        count = 0
        if video_id:
            target = self.output_dir / video_id
            if target.exists():
                for f in target.iterdir():
                    f.unlink()
                    count += 1
                target.rmdir()
        else:
            for d in self.output_dir.iterdir():
                if d.is_dir():
                    for f in d.iterdir():
                        f.unlink()
                        count += 1
                    d.rmdir()
        return count
