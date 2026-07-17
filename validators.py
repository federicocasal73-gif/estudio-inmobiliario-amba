"""
Validaciones centralizadas para el estudio inmobiliario AMBA.

Cubre los limites y reglas de Instagram + restricciones del estudio:
  - caption: max 2200 chars (limite de IG)
  - hashtags: max 30 por post (limite de IG)
  - municipio: debe estar en la lista AMBA soportada o warn
  - hectareas: > 0
  - carrusel: 2-10 imagenes
  - imagenes: tamano maximo 8 MB

Uso:
    from validators import validate_post, validate_carrusel

    resultado = validate_post(caption="...", hashtags=[...])
    if not resultado.ok:
        print(resultado.errores)
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent

IG_CAPTION_MAX_CHARS = 2200
IG_HASHTAGS_MAX = 30
IG_CARRUSEL_MIN = 2
IG_CARRUSEL_MAX = 10
IG_IMAGE_MAX_MB = 8

MUNICIPIOS_AMBA = {
    # Norte
    "Pilar",
    "Escobar",
    "Campana",
    "Zarate",
    "Capilla del Señor",
    "Exaltacion de la Cruz",
    "San Fernando",
    "Tigre",
    "Jose C. Paz",
    "Malvinas Argentinas",
    # Oeste
    "Moreno",
    "Merlo",
    "Ituzaingo",
    "General Rodriguez",
    "Lujan",
    "Mercedes",
    "Suipacha",
    "Navarro",
    # Sur
    "Canuelas",
    "San Vicente",
    "Brandsen",
    "Lobos",
    "Roque Perez",
    "General Paz",
    "Chascomus",
    "Monte",
    # Sudoeste
    "General Alvear",
    "25 de Mayo",
    "9 de Julio",
    "Saladillo",
}


@dataclass
class ResultadoValidacion:
    ok: bool
    errores: list[str] = field(default_factory=list)
    advertencias: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "errores": self.errores,
            "advertencias": self.advertencias,
            "metadata": self.metadata,
        }

    def agregar_error(self, msg: str) -> None:
        self.errores.append(msg)
        self.ok = False

    def agregar_warning(self, msg: str) -> None:
        self.advertencias.append(msg)


# ---------------- Helpers ----------------


def _slug_municipio(municipio: str) -> str:
    """Quita acentos y espacios (igual que CaptionFactory._slug_municipio)."""
    texto = unicodedata.normalize("NFD", municipio)
    texto = "".join(c for c in texto if unicodedata.category(c) != "Mn")
    return texto.lower().replace(" ", "")


def _normalizar_municipio(municipio: str) -> str:
    """Capitaliza y limpia acentos para comparar con lista AMBA."""
    if not municipio:
        return ""
    slug = _slug_municipio(municipio)
    # Reemplazar la primera letra de cada palabra en mayusculas
    partes = slug.split()
    return " ".join(p.capitalize() for p in partes)


# ---------------- Validaciones ----------------


def validate_caption(caption: str) -> ResultadoValidacion:
    """Valida que el caption cumpla los limites de IG."""
    res = ResultadoValidacion(ok=True)
    if caption is None:
        res.agregar_error("caption no puede ser None")
        return res
    if not isinstance(caption, str):
        res.agregar_error(f"caption debe ser string, recibido {type(caption).__name__}")
        return res
    n = len(caption)
    res.metadata["longitud"] = n
    if n == 0:
        res.agregar_error("caption vacio")
    elif n > IG_CAPTION_MAX_CHARS:
        res.agregar_error(f"caption demasiado largo: {n} chars (maximo {IG_CAPTION_MAX_CHARS})")
    elif n > IG_CAPTION_MAX_CHARS * 0.9:
        res.agregar_warning(f"caption cerca del limite: {n} chars (maximo {IG_CAPTION_MAX_CHARS})")
    return res


def validate_hashtags(
    hashtags: list[str] | None,
    blacklist: list[str] | None = None,
    must_include: list[str] | None = None,
) -> ResultadoValidacion:
    """Valida cantidad, formato, blacklist y must_include de hashtags."""
    res = ResultadoValidacion(ok=True)
    if hashtags is None:
        res.agregar_warning("hashtags vacio, recomendado agregar al menos 5")
        return res
    if not isinstance(hashtags, list):
        res.agregar_error(f"hashtags debe ser list, recibido {type(hashtags).__name__}")
        return res

    n = len(hashtags)
    res.metadata["cantidad"] = n
    if n == 0:
        res.agregar_warning("hashtags vacio")
    elif n > IG_HASHTAGS_MAX:
        res.agregar_error(f"demasiados hashtags: {n} (maximo {IG_HASHTAGS_MAX})")

    pattern = re.compile(r"^#[A-Za-z0-9_]+$")
    invalidos = [h for h in hashtags if not pattern.match(h)]
    if invalidos:
        res.agregar_error(
            f"hashtags con formato invalido: {invalidos[:5]}"
            + ("..." if len(invalidos) > 5 else "")
        )

    if blacklist:
        bl_set = {_slug_municipio(b) for b in blacklist}
        conflictivos = [h for h in hashtags if _slug_municipio(h.lstrip("#")) in bl_set]
        if conflictivos:
            res.agregar_error(f"hashtags en blacklist: {conflictivos}")

    if must_include:
        {_slug_municipio(m) for m in must_include}
        tags_set = {_slug_municipio(h.lstrip("#")) for h in hashtags}
        faltan = [m for m in must_include if _slug_municipio(m) not in tags_set]
        if faltan:
            res.agregar_warning(f"hashtags must_include faltantes: {faltan}")

    return res


def validate_municipio(municipio: str, estricto: bool = False) -> ResultadoValidacion:
    """Valida que el municipio este en la lista AMBA.

    estricto=False: solo warning si no esta
    estricto=True: error si no esta
    """
    res = ResultadoValidacion(ok=True)
    if not municipio:
        res.agregar_error("municipio vacio")
        return res
    normalizado = _normalizar_municipio(municipio)
    if normalizado in MUNICIPIOS_AMBA:
        res.metadata["municipio"] = normalizado
        res.metadata["en_lista"] = True
    else:
        res.metadata["municipio"] = normalizado
        res.metadata["en_lista"] = False
        msg = f"municipio '{normalizado}' no esta en la lista AMBA"
        if estricto:
            res.agregar_error(msg)
        else:
            res.agregar_warning(msg)
    return res


def validate_hectareas(hectareas: float | int) -> ResultadoValidacion:
    """Valida que las hectareas sean positivas y razonables."""
    res = ResultadoValidacion(ok=True)
    try:
        valor = float(hectareas)
    except (TypeError, ValueError):
        res.agregar_error(f"hectareas debe ser numerico, recibido {hectareas}")
        return res
    if valor <= 0:
        res.agregar_error(f"hectareas debe ser > 0, recibido {valor}")
    elif valor > 1000:
        res.agregar_warning(f"hectareas muy grande: {valor} (mas de 1000 ha es inusual para AMBA)")
    res.metadata["hectareas"] = valor
    return res


def validate_carrusel(rutas_imagenes: list[str | Path]) -> ResultadoValidacion:
    """Valida cantidad y existencia de imagenes para un carrusel."""
    res = ResultadoValidacion(ok=True)
    if not isinstance(rutas_imagenes, list):
        res.agregar_error("rutas_imagenes debe ser list")
        return res
    n = len(rutas_imagenes)
    res.metadata["cantidad"] = n
    if n < IG_CARRUSEL_MIN:
        res.agregar_error(f"carrusel demasiado corto: {n} imagenes (minimo {IG_CARRUSEL_MIN})")
    elif n > IG_CARRUSEL_MAX:
        res.agregar_error(f"carrusel demasiado largo: {n} imagenes (maximo {IG_CARRUSEL_MAX})")

    for ruta in rutas_imagenes:
        p = Path(ruta)
        if not p.exists():
            res.agregar_error(f"imagen no existe: {ruta}")
            continue
        size_mb = p.stat().st_size / (1024 * 1024)
        if size_mb > IG_IMAGE_MAX_MB:
            res.agregar_error(
                f"imagen demasiado pesada: {ruta} ({size_mb:.1f} MB, max {IG_IMAGE_MAX_MB})"
            )

    return res


def validate_imagen(ruta: str | Path) -> ResultadoValidacion:
    """Valida una imagen individual."""
    res = ResultadoValidacion(ok=True)
    p = Path(ruta)
    if not p.exists():
        res.agregar_error(f"imagen no existe: {ruta}")
        return res
    size_mb = p.stat().st_size / (1024 * 1024)
    res.metadata["size_mb"] = round(size_mb, 2)
    if size_mb > IG_IMAGE_MAX_MB:
        res.agregar_error(f"imagen demasiado pesada: {size_mb:.1f} MB (max {IG_IMAGE_MAX_MB})")
    ext = p.suffix.lower()
    if ext not in (".jpg", ".jpeg", ".png"):
        res.agregar_warning(f"extension {ext} puede no ser soportada por IG (preferir .jpg o .png)")
    return res


def validate_post(
    caption: str,
    hashtags: list[str] | None = None,
    municipio: str | None = None,
    hectareas: float | int | None = None,
    hashtags_blacklist: list[str] | None = None,
    hashtags_must_include: list[str] | None = None,
    estricto_municipio: bool = False,
) -> ResultadoValidacion:
    """Validacion completa de un post (caption + hashtags + contexto)."""
    res = ResultadoValidacion(ok=True)

    cap = validate_caption(caption)
    if not cap.ok:
        res.errores.extend(cap.errores)
        res.ok = False
    res.advertencias.extend(cap.advertencias)
    res.metadata["caption"] = cap.metadata

    if hashtags is not None or hashtags_must_include:
        tags = validate_hashtags(
            hashtags, blacklist=hashtags_blacklist, must_include=hashtags_must_include
        )
        if not tags.ok:
            res.errores.extend(tags.errores)
            res.ok = False
        res.advertencias.extend(tags.advertencias)
        res.metadata["hashtags"] = tags.metadata

    if municipio is not None:
        mun = validate_municipio(municipio, estricto=estricto_municipio)
        if not mun.ok:
            res.errores.extend(mun.errores)
            res.ok = False
        res.advertencias.extend(mun.advertencias)
        res.metadata["municipio"] = mun.metadata

    if hectareas is not None:
        ha = validate_hectareas(hectareas)
        if not ha.ok:
            res.errores.extend(ha.errores)
            res.ok = False
        res.advertencias.extend(ha.advertencias)
        res.metadata["hectareas"] = ha.metadata

    return res


def safe_post(post: dict[str, Any], **kwargs) -> dict[str, Any]:
    """Valida un post del CaptionFactory y agrega metadata de validacion.

    Devuelve el mismo dict con campo extra "_validacion".
    """
    validacion = validate_post(
        caption=post.get("caption_completo", ""), hashtags=post.get("hashtags"), **kwargs
    )
    post["_validacion"] = validacion.to_dict()
    return post


def demo() -> None:
    print("=" * 60)
    print("VALIDATORS - Demo")
    print("=" * 60)
    print()

    print("--- caption normal ---")
    r = validate_caption("Hola mundo 🌾" * 100)
    print(f"  ok={r.ok}, errores={r.errores}, warnings={r.advertencias}")
    print()

    print("--- caption vacio ---")
    r = validate_caption("")
    print(f"  ok={r.ok}, errores={r.errores}")
    print()

    print("--- hashtags validos ---")
    r = validate_hashtags(["#lotes", "#chacras", "#campo"])
    print(f"  ok={r.ok}, metadata={r.metadata}")
    print()

    print("--- hashtags con formato invalido ---")
    r = validate_hashtags(["#lotes", "lotes sin #", "#con espacio"])
    print(f"  ok={r.ok}, errores={r.errores}")
    print()

    print("--- hashtags con blacklist ---")
    r = validate_hashtags(["#lotes", "#chacras"], blacklist=["chacras"])
    print(f"  ok={r.ok}, errores={r.errores}")
    print()

    print("--- municipio valido ---")
    r = validate_municipio("Cañuelas")
    print(f"  ok={r.ok}, metadata={r.metadata}")
    print()

    print("--- municipio no AMBA ---")
    r = validate_municipio("Mar del Plata")
    print(f"  ok={r.ok}, warnings={r.advertencias}")
    print()

    print("--- municipio estricto no AMBA ---")
    r = validate_municipio("Mar del Plata", estricto=True)
    print(f"  ok={r.ok}, errores={r.errores}")
    print()

    print("--- hectareas ---")
    for ha in [5, 0, -1, 5000]:
        r = validate_hectareas(ha)
        nivel = "OK" if r.ok and not r.advertencias else "WARN" if r.ok else "ERROR"
        print(f"  {ha}: {nivel} ({r.errores or r.advertencias or 'ok'})")
    print()

    print("--- validate_post completo ---")
    r = validate_post(
        caption="Hermosa chacra en Cañuelas 🌾" * 50,
        hashtags=["#lotes", "#chacras", "#campo"],
        municipio="Cañuelas",
        hectareas=5,
    )
    print(f"  ok={r.ok}")
    print(f"  errores={r.errores}")
    print(f"  warnings={r.advertencias}")


if __name__ == "__main__":
    demo()
