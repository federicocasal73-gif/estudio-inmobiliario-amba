"""
Generador de imagenes: interfaz abstracta + stub + cliente Fooocus real.

Arquitectura:
  - ImageGenerator: interfaz abstracta
  - StubImageGenerator: NO genera imagenes, devuelve instrucciones
  - FooocusImageGenerator: usa gradio-client para conectar con Fooocus
  - get_generator(): factory que devuelve el generador apropiado

Setup del cliente real:
  pip install gradio-client

  1. Arrancar Fooocus:
     cd Fooocus
     python launch.py --preset default

  2. Verificar que este corriendo:
     curl http://127.0.0.1:7865/

  3. En este codigo, get_generator() detecta automaticamente y devuelve
     FooocusImageGenerator en lugar de StubImageGenerator.

Uso:
    from image_generator import get_generator

    gen = get_generator()
    resultado = gen.generar(
        prompt="5 hectares pampas farm...",
        aspect_ratio="1152*896",
        styles=["Fooocus V2", "Fooocus Enhance"],
        output_path=Path("imagen.jpg"),
    )
    print(resultado.output_path)  # path a la imagen generada
"""

from __future__ import annotations

import json
import shutil
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
DEFAULT_OUTPUT_DIR = ROOT / "inmuebles" / "_generados_ia"


@dataclass
class ImageResult:
    prompt: str
    negative_prompt: str = ""
    aspect_ratio: str = "1152*896"
    styles: list[str] = field(default_factory=list)
    output_path: str | None = None
    fooocus_url: str | None = None
    fooocus_disponible: bool = False
    stub: bool = True
    mensaje: str = ""
    fecha: str = field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class ImageGenerator(ABC):
    """Interfaz abstracta para generadores de imagen."""

    @abstractmethod
    def generar(
        self,
        prompt: str,
        negative_prompt: str = "",
        aspect_ratio: str = "1152*896",
        styles: list[str] | None = None,
        output_path: Path | None = None,
        **kwargs: Any,
    ) -> ImageResult:
        """Genera una imagen y devuelve el resultado."""


class StubImageGenerator(ImageGenerator):
    """Stub que NO genera imagenes. Devuelve el prompt listo para copiar."""

    def __init__(
        self, fooocus_url: str = "http://127.0.0.1:7865", output_dir: Path = DEFAULT_OUTPUT_DIR
    ):
        self.fooocus_url = fooocus_url
        self.output_dir = output_dir
        self.fooocus_disponible = self._check_fooocus()

    def _check_fooocus(self) -> bool:
        try:
            import urllib.request

            req = urllib.request.Request(f"{self.fooocus_url}/", method="GET")
            with urllib.request.urlopen(req, timeout=3):
                return True
        except Exception:
            return False

    def generar(
        self,
        prompt: str,
        negative_prompt: str = "",
        aspect_ratio: str = "1152*896",
        styles: list[str] | None = None,
        output_path: Path | None = None,
        **kwargs: Any,
    ) -> ImageResult:
        styles = styles or ["Fooocus V2", "Fooocus Enhance"]
        output_path = output_path or self._output_path_sugerido(prompt)

        if self.fooocus_disponible:
            mensaje = (
                "Fooocus esta corriendo pero StubImageGenerator no envia imagenes. "
                "Usar FooocusImageGenerator o cambiar get_generator() para activarlo."
            )
        else:
            mensaje = (
                f"Fooocus no detectado en {self.fooocus_url}. Imagen NO generada.\n"
                "Pasos para producir la imagen:\n"
                "  1) Arrancar Fooocus: cd Fooocus && python launch.py\n"
                "  2) Pegar el prompt en el textbox del UI web\n"
                "  3) Configurar aspect_ratio y styles\n"
                "  4) Generate\n"
                "  5) Descargar y guardar en: " + str(output_path) + "\n"
                "Alternativa: usar el prompt en Midjourney, DALL-E o Flux."
            )

        self._guardar_prompt_json(output_path, prompt, negative_prompt, aspect_ratio, styles)

        return ImageResult(
            prompt=prompt,
            negative_prompt=negative_prompt,
            aspect_ratio=aspect_ratio,
            styles=styles,
            output_path=str(output_path),
            fooocus_url=self.fooocus_url,
            fooocus_disponible=self.fooocus_disponible,
            stub=True,
            mensaje=mensaje,
            metadata={"kwargs": kwargs},
        )

    def _output_path_sugerido(self, prompt: str) -> Path:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        palabras = prompt.split()[:5]
        slug = "_".join(palabras).lower()
        slug = "".join(c for c in slug if c.isalnum() or c == "_")[:50]
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        return self.output_dir / f"{slug}_{ts}.jpg"

    def _guardar_prompt_json(
        self,
        output_path: Path,
        prompt: str,
        negative_prompt: str,
        aspect_ratio: str,
        styles: list[str],
    ) -> None:
        json_path = output_path.with_suffix(".prompt.json")
        json_path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "prompt": prompt,
            "negative_prompt": negative_prompt,
            "aspect_ratio": aspect_ratio,
            "styles": styles,
            "imagen_esperada": str(output_path),
            "fecha": datetime.now().isoformat(timespec="seconds"),
        }
        json_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


class FooocusImageGenerator(ImageGenerator):
    """Cliente real para Fooocus usando gradio-client.

    Conecta con un servidor Fooocus que este corriendo y envia los prompts
    a la cola de generacion. Devuelve paths a las imagenes generadas.

    IMPORTANTE: el nombre del endpoint API varia segun la version de Fooocus.
    Esta clase lo detecta automaticamente la primera vez y lo guarda en cache.
    """

    _ENDPOINT_CANDIDATES = [
        "generate_image",
        "generate",
        "txt2img",
        "infer",
        "predict",
    ]

    def __init__(
        self,
        fooocus_url: str = "http://127.0.0.1:7865",
        output_dir: Path = DEFAULT_OUTPUT_DIR,
        poll_interval: int = 5,
        max_wait: int = 900,
    ):
        self.fooocus_url = fooocus_url
        self.output_dir = output_dir
        self.poll_interval = poll_interval
        self.max_wait = max_wait
        self._cliente = None
        self._endpoint: str | None = None
        self._api_info: Any = None

    def _get_client(self):
        if self._cliente is not None:
            return self._cliente
        try:
            from gradio_client import Client
        except ImportError as e:
            raise RuntimeError(
                "gradio-client no instalado. Ejecutar: pip install gradio-client"
            ) from e
        self._cliente = Client(self.fooocus_url)
        return self._cliente

    def _detectar_endpoint(self) -> str:
        """Detecta el nombre del endpoint de generacion en Fooocus."""
        if self._endpoint:
            return self._endpoint
        cliente = self._get_client()
        try:
            info = cliente.view_api(return_format="dict")
        except Exception as e:
            raise RuntimeError(f"No se pudo inspeccionar API de Fooocus: {e}") from e

        self._api_info = info
        nombres = list(info.get("named_endpoints", {}).keys()) + list(
            info.get("unnamed_endpoints", {}).keys()
        )

        for candidato in self._ENDPOINT_CANDIDATES:
            for nombre in nombres:
                if candidato.lower() in nombre.lower():
                    self._endpoint = nombre
                    return nombre

        raise RuntimeError(
            f"No se encontro un endpoint de generacion en Fooocus. Endpoints disponibles: {nombres}"
        )

    def _parsear_aspect(self, aspect_ratio: str) -> tuple[int, int]:
        """Convierte '1152*896' a (1152, 896)."""
        try:
            w, h = aspect_ratio.replace("x", "*").split("*")
            return int(w), int(h)
        except (ValueError, AttributeError):
            return 1152, 896

    def generar(
        self,
        prompt: str,
        negative_prompt: str = "",
        aspect_ratio: str = "1152*896",
        styles: list[str] | None = None,
        output_path: Path | None = None,
        steps: int = 30,
        cfg_scale: float = 4.0,
        seed: int = -1,
        **kwargs: Any,
    ) -> ImageResult:
        """Envia prompt a Fooocus y descarga la imagen resultante."""
        styles = styles or ["Fooocus V2", "Fooocus Enhance"]
        output_path = output_path or self._output_path_sugerido(prompt)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        cliente = self._get_client()
        endpoint = self._detectar_endpoint()

        try:
            width, height = self._parsear_aspect(aspect_ratio)
            kwargs_gradio = {
                "prompt": prompt,
                "negative_prompt": negative_prompt,
                "styles": styles,
                "performance_selection": "Speed",
                "aspect_ratios_selection": aspect_ratio.replace("*", "x"),
                "width": width,
                "height": height,
                "image_number": 1,
                "seed": seed,
                "sharpness": 2.0,
                "guidance_scale": cfg_scale,
                "steps": steps,
            }
            kwargs_gradio = {k: v for k, v in kwargs_gradio.items() if v is not None}

            job = cliente.predict(**kwargs_gradio, api_name=endpoint)
        except Exception as e:
            raise RuntimeError(f"Error enviando a Fooocus (endpoint={endpoint}): {e}") from e

        try:
            resultado = self._esperar_y_descargar(job, output_path)
        except Exception as e:
            raise RuntimeError(f"Error descargando resultado: {e}") from e

        return ImageResult(
            prompt=prompt,
            negative_prompt=negative_prompt,
            aspect_ratio=aspect_ratio,
            styles=styles,
            output_path=str(output_path),
            fooocus_url=self.fooocus_url,
            fooocus_disponible=True,
            stub=False,
            mensaje=f"Imagen generada por Fooocus en {output_path}",
            metadata={"endpoint": endpoint, "steps": steps, "cfg_scale": cfg_scale, "seed": seed},
        )

    def _esperar_y_descargar(self, job, output_path: Path) -> Path:
        """Espera el resultado del job y guarda la imagen en output_path."""
        resultado = job.result() if hasattr(job, "result") else job

        if isinstance(resultado, (list, tuple)) and resultado:
            path_or_url = resultado[0]
        else:
            path_or_url = resultado

        if path_or_url is None:
            raise RuntimeError("Fooocus devolvio resultado vacio")

        src = Path(str(path_or_url))
        if src.exists() and src.is_file():
            shutil.move(str(src), str(output_path))
            return output_path
        if isinstance(path_or_url, str) and path_or_url.startswith(("http://", "https://")):
            import urllib.request

            with urllib.request.urlopen(path_or_url, timeout=30) as resp:
                output_path.write_bytes(resp.read())
            return output_path

        raise RuntimeError(f"No se pudo obtener la imagen desde: {path_or_url}")

    def _output_path_sugerido(self, prompt: str) -> Path:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        palabras = prompt.split()[:5]
        slug = "_".join(palabras).lower()
        slug = "".join(c for c in slug if c.isalnum() or c == "_")[:50]
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        return self.output_dir / f"{slug}_{ts}.jpg"


def get_generator(prefer_real: bool = True) -> ImageGenerator:
    """Factory: devuelve FooocusImageGenerator si esta disponible y gradio-client
    esta instalado; si no devuelve StubImageGenerator.
    """
    try:
        import gradio_client  # noqa: F401
    except ImportError:
        return StubImageGenerator()

    stub = StubImageGenerator()
    if prefer_real and stub.fooocus_disponible:
        try:
            return FooocusImageGenerator(stub.fooocus_url)
        except Exception:
            return stub
    return stub


def demo() -> None:
    gen = get_generator()
    print("=" * 60)
    print("IMAGE GENERATOR - Demo")
    print("=" * 60)
    print(f"Clase: {type(gen).__name__}")
    print(f"Fooocus URL: {gen.fooocus_url}")
    print(f"Fooocus disponible: {gen.fooocus_disponible}")
    print()

    resultado = gen.generar(
        prompt="5 hectares pampas farm, golden hour, real estate photography",
        negative_prompt="blurry, low quality",
        aspect_ratio="1152*896",
        styles=["Fooocus V2", "Fooocus Enhance"],
        output_path=Path("/tmp/test_generated.jpg"),
    )

    print("--- Resultado ---")
    print(f"Stub: {resultado.stub}")
    print(f"Output esperado: {resultado.output_path}")
    if resultado.exito if hasattr(resultado, "exito") else True:
        print(f"Imagen: {resultado.output_path}")
    print("Mensaje (primeras lineas):")
    for linea in resultado.mensaje.split("\n")[:6]:
        print(f"  {linea}")

    print()
    print("--- Factory get_generator() ---")
    g = get_generator()
    print(f"Tipo: {type(g).__name__}")
    print(f"Real disponible: {not isinstance(g, StubImageGenerator)}")


if __name__ == "__main__":
    demo()
