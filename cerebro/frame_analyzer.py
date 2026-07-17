"""Analizador de frames con modelos de visión IA.

Analiza imágenes de frames extraídos y genera prompts SDXL optimizados.
Soporta GPT-4V, Claude Vision, y fallback local con BLIP-2.
"""

from __future__ import annotations

import base64
import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from cerebro.prompt_database import (
    CATEGORIAS,
    ESTILOS,
    MOMENTOS_DIA,
    DEFAULT_NEGATIVE,
    DEFAULT_STYLES,
)


@dataclass
class AnalisisFrame:
    """Resultado del análisis de un frame."""
    prompt_generado: str = ""
    negative_prompt: str = DEFAULT_NEGATIVE
    aspect_ratio: str = "896*1152"
    styles: list[str] = field(default_factory=lambda: DEFAULT_STYLES.copy())
    categoria: str = "otro"
    estilo: str = "otro"
    momento_dia: str = ""
    ubicacion: str = ""
    elementos: list[str] = field(default_factory=list)
    colores_dominate: list[str] = field(default_factory=list)
    descripcion: str = ""
    confianza: float = 0.0  # 0-1
    metadata_extra: dict[str, Any] = field(default_factory=dict)


class FrameAnalyzer:
    """Analiza frames y genera prompts SDXL."""

    def __init__(self, api_provider: str = "openai", api_key: str | None = None):
        """
        api_provider: 'openai', 'anthropic', o 'local'
        api_key: API key del proveedor (o env var)
        """
        self.api_provider = api_provider
        self.api_key = api_key or self._get_api_key()

    def _get_api_key(self) -> str | None:
        if self.api_provider == "openai":
            return os.environ.get("OPENAI_API_KEY")
        if self.api_provider == "anthropic":
            return os.environ.get("ANTHROPIC_API_KEY")
        return None

    def analizar_frame(self, frame_path: Path | str) -> AnalisisFrame:
        """Analiza un frame y devuelve un AnalisisFrame con prompt generado."""
        frame_path = Path(frame_path)
        if not frame_path.exists():
            raise FileNotFoundError(f"Frame no encontrado: {frame_path}")

        if self.api_provider == "openai" and self.api_key:
            return self._analizar_con_openai(frame_path)
        elif self.api_provider == "anthropic" and self.api_key:
            return self._analizar_con_anthropic(frame_path)
        else:
            return self._analizar_local(frame_path)

    def _analizar_con_openai(self, frame_path: Path) -> AnalisisFrame:
        """Analiza usando GPT-4V."""
        import urllib.request

        image_b64 = base64.b64encode(frame_path.read_bytes()).decode()

        prompt_sistema = """Sos un experto en fotografía inmobiliaria y generación de prompts para Stable Diffusion.
Analizá esta imagen de una propiedad inmobiliaria y devolvé un JSON con:

1. prompt: Prompt SDXL optimizado (en inglés, descriptivo, 50-100 palabras). Incluí:
   - Tipo de escena (terreno, lote, construcción, casa)
   - Elementos visuales clave
   - Estilo fotográfico
   - Iluminación y momento del día
   - Calidad (8k, professional photography, etc.)

2. negative_prompt: Qué excluir (en inglés)

3. categoria: Una de: terreno, lote, desarrollo, construccion, casa_terminada, servicio, vista_aerea, render, otro

4. estilo: Uno de: campestre, moderno, rustico, premium, minimalista, industrial, colonial, otro

5. momento_dia: amanecer, manana, mediodia, tarde, atardecer, noche, blue_hour, golden_hour

6. ubicacion: Ubicación probable (si se puede inferir)

7. elementos: Lista de elementos visuales principales

8. colores_dominate: Lista de 3-5 colores principales

9. aspect_ratio: Uno de: 896*1152 (post), 768*1344 (story), 1024*1024 (square), 1152*896 (landscape)

10. descripcion: Descripción en español de lo que se ve

Respondé SOLO con el JSON, sin texto adicional."""

        payload = {
            "model": "gpt-4o",
            "messages": [
                {"role": "system", "content": prompt_sistema},
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "Analizá esta imagen y generá el prompt SDXL optimizado."
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{image_b64}",
                                "detail": "high",
                            },
                        },
                    ],
                },
            ],
            "max_tokens": 1000,
            "temperature": 0.3,
        }

        data = json.dumps(payload).encode()
        req = urllib.request.Request(
            "https://api.openai.com/v1/chat/completions",
            data=data,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
        )

        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                result = json.loads(resp.read().decode())
                content = result["choices"][0]["message"]["content"]
                # Limpiar posibles markdown code blocks
                content = content.strip()
                if content.startswith("```"):
                    content = content.split("\n", 1)[1]
                if content.endswith("```"):
                    content = content.rsplit("```", 1)[0]
                content = content.strip()

                parsed = json.loads(content)
                return AnalisisFrame(
                    prompt_generado=parsed.get("prompt", ""),
                    negative_prompt=parsed.get("negative_prompt", DEFAULT_NEGATIVE),
                    aspect_ratio=parsed.get("aspect_ratio", "896*1152"),
                    categoria=parsed.get("categoria", "otro"),
                    estilo=parsed.get("estilo", "otro"),
                    momento_dia=parsed.get("momento_dia", ""),
                    ubicacion=parsed.get("ubicacion", ""),
                    elementos=parsed.get("elementos", []),
                    colores_dominate=parsed.get("colores_dominate", []),
                    descripcion=parsed.get("descripcion", ""),
                    confianza=0.9,
                    metadata_extra={"api": "openai", "model": "gpt-4o"},
                )
        except Exception as e:
            print(f"Error con OpenAI: {e}")
            return self._analizar_local(frame_path)

    def _analizar_con_anthropic(self, frame_path: Path) -> AnalisisFrame:
        """Analiza usando Claude Vision."""
        import urllib.request

        image_b64 = base64.b64encode(frame_path.read_bytes()).decode()

        prompt_sistema = """Eres un experto en fotografía inmobiliaria y generación de prompts para Stable Diffusion.
Analiza esta imagen de una propiedad inmobiliaria y devuelve un JSON con:
prompt, negative_prompt, categoria, estilo, momento_dia, ubicacion, elementos, colores_dominate, aspect_ratio, descripcion.
Usa los mismos valores que para OpenAI (ver sistema de archivos).
Responde SOLO con el JSON."""

        payload = {
            "model": "claude-sonnet-4-20250514",
            "max_tokens": 1000,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/jpeg",
                                "data": image_b64,
                            },
                        },
                        {"type": "text", "text": prompt_sistema},
                    ],
                }
            ],
        }

        data = json.dumps(payload).encode()
        req = urllib.request.Request(
            "https://api.anthropic.com/v1/messages",
            data=data,
            headers={
                "Content-Type": "application/json",
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01",
            },
        )

        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                result = json.loads(resp.read().decode())
                content = result["content"][0]["text"]
                content = content.strip()
                if content.startswith("```"):
                    content = content.split("\n", 1)[1]
                if content.endswith("```"):
                    content = content.rsplit("```", 1)[0]

                parsed = json.loads(content.strip())
                return AnalisisFrame(
                    prompt_generado=parsed.get("prompt", ""),
                    negative_prompt=parsed.get("negative_prompt", DEFAULT_NEGATIVE),
                    aspect_ratio=parsed.get("aspect_ratio", "896*1152"),
                    categoria=parsed.get("categoria", "otro"),
                    estilo=parsed.get("estilo", "otro"),
                    momento_dia=parsed.get("momento_dia", ""),
                    ubicacion=parsed.get("ubicacion", ""),
                    elementos=parsed.get("elementos", []),
                    colores_dominate=parsed.get("colores_dominate", []),
                    descripcion=parsed.get("descripcion", ""),
                    confianza=0.85,
                    metadata_extra={"api": "anthropic", "model": "claude-sonnet-4-20250514"},
                )
        except Exception as e:
            print(f"Error con Anthropic: {e}")
            return self._analizar_local(frame_path)

    def _analizar_local(self, frame_path: Path) -> AnalisisFrame:
        """Análisis básico sin API (fallback)."""
        from PIL import Image

        img = Image.open(frame_path)
        w, h = img.size

        # Detectar aspect ratio dominante
        if w > h:
            aspect = "1152*896"
        elif h > w:
            aspect = "896*1152"
        else:
            aspect = "1024*1024"

        # Analizar brillo para momento del día aprox
        gray = img.convert("L")
        pixels = list(gray.getdata())
        avg_brightness = sum(pixels) / len(pixels)

        if avg_brightness < 80:
            momento = "noche"
        elif avg_brightness < 120:
            momento = "atardecer"
        elif avg_brightness < 180:
            momento = "manana"
        else:
            momento = "mediodia"

        # Prompt genérico basado en análisis básico
        prompt = (
            f"real estate photography, professional quality, "
            f"Argentine property, Buenos Aires province, "
            f"{momento} lighting, sharp focus, 8k, "
            f"ultra realistic photography"
        )

        return AnalisisFrame(
            prompt_generado=prompt,
            negative_prompt=DEFAULT_NEGATIVE,
            aspect_ratio=aspect,
            styles=DEFAULT_STYLES.copy(),
            categoria="otro",
            estilo="otro",
            momento_dia=momento,
            ubicacion="Buenos Aires",
            elementos=["propiedad", "terreno"],
            colores_dominate=[],
            descripcion="Análisis básico sin API de visión",
            confianza=0.3,
            metadata_extra={"api": "local", "model": "basic_analysis"},
        )

    def analizar_lote(
        self, frames_paths: list[Path], video_metadata: dict[str, Any] | None = None
    ) -> list[AnalisisFrame]:
        """Analiza múltiples frames de un video."""
        resultados = []
        for path in frames_paths:
            try:
                resultado = self.analizar_frame(path)
                if video_metadata:
                    resultado.metadata_extra.update(video_metadata)
                resultados.append(resultado)
            except Exception as e:
                print(f"Error analizando {path}: {e}")
                continue
        return resultados
