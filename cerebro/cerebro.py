"""Orquestador principal del Cerebro de Prompts.

Flujo completo: URL → video → frames → análisis → prompts → BD.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from cerebro.prompt_database import PromptDatabase, PromptEntry
from cerebro.video_extractor import VideoExtractor, VideoInfo, ExtractedFrame
from cerebro.frame_analyzer import FrameAnalyzer, AnalisisFrame


@dataclass
class ProcesamientoResultado:
    """Resultado de procesar un video."""
    video_info: VideoInfo | None = None
    frames_extraidos: int = 0
    frames_analizados: int = 0
    prompts_generados: int = 0
    prompts_guardados: int = 0
    errores: list[str] = field(default_factory=list)
    detalles: list[dict[str, Any]] = field(default_factory=list)


class Cerebro:
    """Orquestador principal del sistema de prompts."""

    def __init__(
        self,
        db_path: Path | str | None = None,
        api_provider: str = "openai",
        api_key: str | None = None,
        max_frames: int = 10,
    ):
        self.db = PromptDatabase(db_path)
        self.extractor = VideoExtractor(max_frames=max_frames)
        self.analyzer = FrameAnalyzer(api_provider=api_provider, api_key=api_key)

    def procesar_video(
        self,
        url: str,
        n_frames: int | None = None,
        auto_aprobar: bool = False,
        tags: list[str] | None = None,
    ) -> ProcesamientoResultado:
        """Procesa un video completo: descarga → frames → análisis → prompts."""
        resultado = ProcesamientoResultado()

        # 1. Descargar video y extraer frames
        try:
            print(f"Descargando video: {url}")
            video_info, frames = self.extractor.extraer_de_url(url, n_frames)
            resultado.video_info = video_info
            resultado.frames_extraidos = len(frames)
            print(f"  Extraídos {len(frames)} frames del video {video_info.video_id}")
        except Exception as e:
            resultado.errores.append(f"Error descargando video: {e}")
            return resultado

        # 2. Analizar frames
        try:
            frame_paths = [f.path for f in frames]
            video_meta = {
                "video_id": video_info.video_id,
                "plataforma": video_info.plataforma,
                "titulo": video_info.titulo,
                "autor": video_info.autor,
                "fuente": url,
            }

            print(f"Analizando {len(frame_paths)} frames con IA...")
            analisis_list = self.analyzer.analizar_lote(frame_paths, video_meta)
            resultado.frames_analizados = len(analisis_list)
        except Exception as e:
            resultado.errores.append(f"Error analizando frames: {e}")
            return resultado

        # 3. Guardar prompts en la BD
        for i, (analisis, frame) in enumerate(zip(analisis_list, frames)):
            try:
                metadata = {
                    "categoria": analisis.categoria,
                    "estilo": analisis.estilo,
                    "momento_dia": analisis.momento_dia,
                    "ubicacion": analisis.ubicacion,
                    "elementos": analisis.elementos,
                    "colores_dominate": analisis.colores_dominate,
                    "fuente": url,
                    "video_id": video_info.video_id,
                    "frame_numero": frame.frame_number,
                    "frame_timestamp": frame.timestamp,
                    "frame_quality": frame.quality_score,
                    "plataforma": video_info.plataforma,
                }

                entry = self.db.agregar(
                    prompt=analisis.prompt_generado,
                    negative_prompt=analisis.negative_prompt,
                    aspect_ratio=analisis.aspect_ratio,
                    styles=analisis.styles,
                    metadata=metadata,
                    tags=tags or [],
                )

                if auto_aprobar:
                    self.db.actualizar(
                        entry.id,
                        aprobado=True,
                        rating=3,
                    )

                resultado.prompts_guardados += 1
                resultado.detalles.append({
                    "frame": frame.frame_number,
                    "prompt": analisis.prompt_generado[:80],
                    "categoria": analisis.categoria,
                    "confianza": analisis.confianza,
                })

                print(
                    f"  Frame {frame.frame_number}: [{analisis.categoria}] "
                    f"{analisis.prompt_generado[:60]}..."
                )

            except Exception as e:
                resultado.errores.append(f"Error guardando frame {i}: {e}")

        resultado.prompts_generados = len(analisis_list)
        print(f"\nProcesamiento completo: {resultado.prompts_guardados} prompts guardados")
        return resultado

    def procesar_lote(
        self,
        urls: list[str],
        n_frames: int | None = None,
        auto_aprobar: bool = False,
    ) -> list[ProcesamientoResultado]:
        """Procesa múltiples videos."""
        resultados = []
        for i, url in enumerate(urls, 1):
            print(f"\n--- Video {i}/{len(urls)} ---")
            resultado = self.procesar_video(url, n_frames, auto_aprobar)
            resultados.append(resultado)
        return resultados

    def obtener_prompt(
        self,
        categoria: str | None = None,
        estilo: str | None = None,
        momento_dia: str | None = None,
        min_rating: int = 1,
    ) -> PromptEntry | None:
        """Obtiene un prompt aleatorio que cumpla los criterios."""
        prompts = self.db.buscar(
            categoria=categoria,
            estilo=estilo,
            momento_dia=momento_dia,
            aprobado=True,
            min_rating=min_rating,
            limit=10,
        )
        if not prompts:
            return None
        import random
        return random.choice(prompts)

    def obtener_prompts(
        self,
        categoria: str | None = None,
        estilo: str | None = None,
        n: int = 5,
        min_rating: int = 1,
    ) -> list[PromptEntry]:
        """Obtiene N prompts que cumplan los criterios."""
        return self.db.buscar(
            categoria=categoria,
            estilo=estilo,
            aprobado=True,
            min_rating=min_rating,
            limit=n,
        )

    def estadisticas(self) -> dict[str, Any]:
        """Devuelve estadísticas del cerebro."""
        return self.db.estadisticas()
