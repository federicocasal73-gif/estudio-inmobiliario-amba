"""
Modulo de mejora de fotos para contenido inmobiliario.

Funciona en 2 niveles:
  - Local (sin Fooocus): usa solo Pillow. Ajustes basicos de brillo,
    contraste, color, sharpness, upscale Lanczos, filtros "magazine".
  - Con Fooocus: delega en el modulo extras/ de Fooocus para RealESRGAN,
    GFPGAN, inpainting, etc.

Modos disponibles:
  - "natural":     ajustes suaves, preserva realismo
  - "magazine":    look inmobiliario de revista (warm, contraste medio)
  - "instagram":   listo para subir (resize 1080x1350 4:5, sharpen)
  - "golden_hour": simula golden hour pampeano (warm, sombras abiertas)
  - "pampa":       look del campo (cielo mas azul, verde mas verde)

Uso:
    from mejora_fotos import MejoraFotos

    mejora = MejoraFotos()
    resultado = mejora.mejorar(
        foto_path="inmuebles/obras/casa-perez/inputs/semana-03.jpg",
        modo="magazine",
        intensidad="media",
        upscale=2,
    )
    print(resultado.ruta_salida)
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

try:
    from PIL import Image, ImageEnhance, ImageFilter, ImageOps, ImageStat

    HAS_PILLOW = True
except ImportError:
    HAS_PILLOW = False

ROOT = Path(__file__).resolve().parent


@dataclass
class ResultadoMejora:
    foto_origen: str
    foto_destino: str
    modo: str
    intensidad: str
    upscale: int
    transformaciones: list[str] = field(default_factory=list)
    metadata_origen: dict[str, Any] = field(default_factory=dict)
    metadata_destino: dict[str, Any] = field(default_factory=dict)
    fooocus_usado: bool = False
    fecha_procesado: str = field(
        default_factory=lambda: datetime.now().isoformat(timespec="seconds")
    )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class MejoraFotos:
    """Mejora fotos usando Pillow. Hooks para delegar a Fooocus si esta activo."""

    MODOS = ["natural", "magazine", "instagram", "golden_hour", "pampa"]
    INTENSIDADES = ["baja", "media", "alta"]

    PARAMETROS_POR_MODO = {
        "natural": {
            "brillo": 1.05,
            "contraste": 1.10,
            "saturacion": 1.05,
            "sharpness": 1.20,
            "warmth": 1.00,
        },
        "magazine": {
            "brillo": 1.08,
            "contraste": 1.25,
            "saturacion": 1.15,
            "sharpness": 1.40,
            "warmth": 1.15,
        },
        "instagram": {
            "brillo": 1.10,
            "contraste": 1.20,
            "saturacion": 1.20,
            "sharpness": 1.50,
            "warmth": 1.10,
        },
        "golden_hour": {
            "brillo": 1.05,
            "contraste": 1.15,
            "saturacion": 1.25,
            "sharpness": 1.30,
            "warmth": 1.40,
        },
        "pampa": {
            "brillo": 1.05,
            "contraste": 1.30,
            "saturacion": 1.35,
            "sharpness": 1.40,
            "warmth": 1.05,
        },
    }

    MULTIPLICADOR_INTENSIDAD = {
        "baja": 0.5,
        "media": 1.0,
        "alta": 1.5,
    }

    def __init__(self, fooocus_url: str | None = None):
        self.fooocus_url = fooocus_url
        self.fooocus_disponible = self._check_fooocus()

    def _check_fooocus(self) -> bool:
        if not self.fooocus_url:
            return False
        try:
            import urllib.request

            req = urllib.request.Request(f"{self.fooocus_url}/", method="GET")
            with urllib.request.urlopen(req, timeout=3):
                return True
        except Exception:
            return False

    # ---------------- API principal ----------------

    def mejorar(
        self,
        foto_path: str | Path,
        modo: str = "magazine",
        intensidad: str = "media",
        upscale: int = 1,
        ruta_salida: str | Path | None = None,
        tamaño_ig: tuple[int, int] | None = None,
    ) -> ResultadoMejora:
        if not HAS_PILLOW:
            raise RuntimeError("Pillow no instalado. pip install pillow")

        if modo not in self.MODOS:
            raise ValueError(f"modo invalido: {modo}. Use {self.MODOS}")
        if intensidad not in self.INTENSIDADES:
            raise ValueError(f"intensidad invalida: {intensidad}. Use {self.INTENSIDADES}")

        foto_path = Path(foto_path)
        if not foto_path.exists():
            raise FileNotFoundError(f"No existe: {foto_path}")

        resultado = ResultadoMejora(
            foto_origen=str(foto_path.resolve()),
            foto_destino="",
            modo=modo,
            intensidad=intensidad,
            upscale=upscale,
        )
        resultado.metadata_origen = self._metadata_imagen(foto_path)

        img = Image.open(foto_path)
        resultado.metadata_origen.update(
            {
                "modo": img.mode,
                "size": img.size,
                "formato": img.format,
            }
        )

        transformaciones: list[str] = []

        # 1) Convertir a RGB si es necesario (algunos TIFF, PNG con alfa, etc.)
        if img.mode != "RGB":
            img = img.convert("RGB")
            transformaciones.append(f"convert_to_rgb (desde {img.mode})")

        # 2) Auto-exposure si la foto esta sub/sobreexpuesta
        if self._necesita_auto_exposure(img):
            img = self._auto_exposure(img, intensidad)
            transformaciones.append("auto_exposure")

        # 3) Aplicar Look del modo
        params = self._parametros_efectivos(modo, intensidad)
        img = self._aplicar_look(img, params)
        transformaciones.append(
            f"look:{modo} brillo={params['brillo']:.2f} contraste={params['contraste']:.2f} "
            f"saturacion={params['saturacion']:.2f} sharpness={params['sharpness']:.2f} "
            f"warmth={params['warmth']:.2f}"
        )

        # 4) Sharpen final (UnsharpMask mas agresivo)
        img = img.filter(ImageFilter.UnsharpMask(radius=2, percent=150, threshold=3))
        transformaciones.append("unsharp_mask_final")

        # 5) Upscale si se pidio
        if upscale > 1:
            img = self._upscale(img, upscale)
            transformaciones.append(f"upscale_x{upscale}")

        # 6) Resize a tamano IG si se pidio
        if tamaño_ig:
            img = self._resize_instagram(img, tamaño_ig)
            transformaciones.append(f"resize_instagram_{tamaño_ig[0]}x{tamaño_ig[1]}")

        # 7) Guardar
        if ruta_salida is None:
            carpeta = foto_path.parent / "mejoras"
            carpeta.mkdir(exist_ok=True)
            sufijo = f"_{modo}_x{upscale}"
            ruta_salida = carpeta / f"{foto_path.stem}{sufijo}.jpg"
        else:
            ruta_salida = Path(ruta_salida)
            ruta_salida.parent.mkdir(parents=True, exist_ok=True)

        img.save(ruta_salida, "JPEG", quality=92, optimize=True)
        resultado.metadata_destino = self._metadata_imagen(ruta_salida)
        resultado.metadata_destino.update(
            {
                "modo": img.mode,
                "size": img.size,
                "formato": "JPEG",
            }
        )
        resultado.foto_destino = str(ruta_salida.resolve())
        resultado.transformaciones = transformaciones
        return resultado

    def batch(
        self,
        carpeta_origen: str | Path,
        carpeta_destino: str | Path,
        modo: str = "magazine",
        intensidad: str = "media",
        upscale: int = 1,
        extensiones: tuple[str, ...] = (".jpg", ".jpeg", ".png", ".tif", ".tiff"),
    ) -> list[ResultadoMejora]:
        carpeta_origen = Path(carpeta_origen)
        carpeta_destino = Path(carpeta_destino)
        carpeta_destino.mkdir(parents=True, exist_ok=True)

        fotos = sorted(
            [p for p in carpeta_origen.iterdir() if p.is_file() and p.suffix.lower() in extensiones]
        )
        resultados: list[ResultadoMejora] = []
        for foto in fotos:
            try:
                ruta_salida = carpeta_destino / f"{foto.stem}_{modo}_x{upscale}.jpg"
                resultado = self.mejorar(
                    foto_path=foto,
                    modo=modo,
                    intensidad=intensidad,
                    upscale=upscale,
                    ruta_salida=ruta_salida,
                )
                resultados.append(resultado)
            except Exception as e:
                resultados.append(
                    ResultadoMejora(
                        foto_origen=str(foto),
                        foto_destino="",
                        modo=modo,
                        intensidad=intensidad,
                        upscale=upscale,
                        transformaciones=[f"ERROR: {e}"],
                    )
                )
        return resultados

    # ---------------- Hooks para Fooocus (futuro) ----------------

    def mejorar_con_fooocus(
        self,
        foto_path: str | Path,
        operacion: str = "upscale_2x",
        ruta_salida: str | Path | None = None,
    ) -> ResultadoMejora:
        """Hook para cuando Fooocus este activo.

        operacion: 'upscale_2x' | 'upscale_4x' | 'face_enhance' | 'inpaint'
        """
        if not self.fooocus_disponible:
            raise RuntimeError(
                "Fooocus no esta activo. Levantar con python launch.py primero. "
                f"URL configurada: {self.fooocus_url}"
            )

        # Por ahora delega al metodo local hasta que integremos la API de Fooocus
        escala = {"upscale_2x": 2, "upscale_4x": 4}.get(operacion, 2)
        resultado = self.mejorar(
            foto_path, modo="magazine", intensidad="media", upscale=escala, ruta_salida=ruta_salida
        )
        resultado.fooocus_usado = False  # hasta integrar API
        resultado.transformaciones.append("fooocus_delegated_to_local_pending_api_integration")
        return resultado

    # ---------------- Utilidades internas ----------------

    def _metadata_imagen(self, path: Path) -> dict[str, Any]:
        return {
            "archivo": path.name,
            "tamaño_bytes": path.stat().st_size,
        }

    @staticmethod
    def _necesita_auto_exposure(img: Image.Image) -> bool:
        """Detecta si la imagen esta sub/sobreexpuesta."""
        stat = ImageStat.Stat(img.convert("L"))
        media = stat.mean[0]
        # < 80 subexpuesta, > 200 sobreexpuesta
        return media < 80 or media > 200

    @staticmethod
    def _auto_exposure(img: Image.Image, intensidad: str) -> Image.Image:
        factor = {"baja": 0.5, "media": 0.8, "alta": 1.0}[intensidad]
        stat = ImageStat.Stat(img.convert("L"))
        media = stat.mean[0]
        target = 128
        ratio = target / max(media, 1)
        ratio = 1 + (ratio - 1) * factor
        enhancer = ImageEnhance.Brightness(img)
        return enhancer.enhance(ratio)

    def _parametros_efectivos(self, modo: str, intensidad: str) -> dict[str, float]:
        params = self.PARAMETROS_POR_MODO[modo].copy()
        mult = self.MULTIPLICADOR_INTENSIDAD[intensidad]
        # Los parametros ya estan normalizados en torno a 1.0
        # Multiplicamos la desviacion (param - 1) por mult
        for key in params:
            params[key] = 1.0 + (params[key] - 1.0) * mult
        return params

    @staticmethod
    def _aplicar_look(img: Image.Image, params: dict[str, float]) -> Image.Image:
        img = ImageEnhance.Brightness(img).enhance(params["brillo"])
        img = ImageEnhance.Contrast(img).enhance(params["contraste"])
        img = ImageEnhance.Color(img).enhance(params["saturacion"])
        img = ImageEnhance.Sharpness(img).enhance(params["sharpness"])
        # Warmth: mezclamos con una capa roja
        if params["warmth"] != 1.0:
            img = MejoraFotos._aplicar_warmth(img, params["warmth"])
        return img

    @staticmethod
    def _aplicar_warmth(img: Image.Image, factor: float) -> Image.Image:
        """Calienta la imagen. factor > 1 = mas calido, < 1 = mas frio."""
        r, g, b = img.split()
        if factor > 1.0:
            r = r.point(lambda p: min(255, int(p * factor)))
            b = b.point(lambda p: int(p * (2 - factor)))
        else:
            factor_inv = 2 - factor  # invertir para enfriar
            b = b.point(lambda p: min(255, int(p * factor_inv)))
            r = r.point(lambda p: int(p * (2 - factor_inv)))
        return Image.merge("RGB", (r, g, b))

    @staticmethod
    def _upscale(img: Image.Image, factor: int) -> Image.Image:
        new_size = (img.width * factor, img.height * factor)
        return img.resize(new_size, Image.Resampling.LANCZOS)

    @staticmethod
    def _resize_instagram(img: Image.Image, target: tuple[int, int]) -> Image.Image:
        return img.resize(target, Image.Resampling.LANCZOS)


def demo() -> None:
    """Demo: crea una imagen de prueba y la mejora."""
    mejora = MejoraFotos()

    # Crear imagen de prueba para que el demo funcione sin inputs reales
    test_dir = ROOT / "inmuebles" / "_test_mejora"
    test_dir.mkdir(parents=True, exist_ok=True)
    test_foto = test_dir / "lote_original.jpg"

    if not test_foto.exists():
        img = Image.new("RGB", (800, 600), color=(180, 165, 130))
        for x in range(0, 800, 40):
            for y in range(0, 600, 40):
                img.paste((120, 100, 70), (x, y, x + 20, y + 20))
        img.save(test_foto, "JPEG")
        print(f"Imagen de prueba creada: {test_foto}")

    print("\n--- Mejora con modo 'magazine' ---")
    resultado = mejora.mejorar(
        foto_path=test_foto,
        modo="magazine",
        intensidad="media",
        upscale=1,
    )
    print(f"Origen:  {resultado.foto_origen}")
    print(f"Destino: {resultado.foto_destino}")
    print(f"Size origen:  {resultado.metadata_origen['size']}")
    print(f"Size destino: {resultado.metadata_destino['size']}")
    print("Transformaciones:")
    for t in resultado.transformaciones:
        print(f"  - {t}")

    print("\n--- Batch (1 sola imagen) ---")
    resultados_batch = mejora.batch(
        carpeta_origen=test_dir,
        carpeta_destino=test_dir / "mejoras_batch",
        modo="golden_hour",
        intensidad="alta",
        upscale=2,
    )
    for r in resultados_batch:
        print(f"  {r.foto_origen} -> {r.foto_destino} ({len(r.transformaciones)} pasos)")


if __name__ == "__main__":
    demo()
