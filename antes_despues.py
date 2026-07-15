"""
Modulo antes/despues para contenido inmobiliario.

Tres modos:
  - real:  tenes foto del antes Y del despues. Solo empaqueta el carrusel.
  - ia:    solo tenes foto del antes. Genera prompt SDXL + instrucciones para img2img.
  - mixto: tenes foto del antes y queres que la IA sugiera como podria quedar.

Uso:
    from realestate_studio import RealestateStudio
    from antes_despues import AntesDespues

    studio = RealestateStudio()
    ad = AntesDespues(studio)

    # Modo IA: solo foto del antes
    ad_resultado = ad.generar(
        foto_antes_path="inmuebles/lotes/chacra-canuelas-5ha/inputs/lote_baldio.jpg",
        estilo_casa="casa de campo tradicional con galería",
        hectareas=5,
        municipio="Cañuelas",
        proyecto="chacra-canuelas-5ha",
        modo="ia",
    )

    # Modo real: ambas fotos
    ad_resultado = ad.generar(
        foto_antes_path="antes.jpg",
        foto_despues_path="despues.jpg",
        cliente="Familia Pérez",
        municipio="Escobar",
        proyecto="casa-perez-escobar",
        modo="real",
    )

    ad.guardar(ad_resultado)
"""

from __future__ import annotations

import json
import shutil
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from realestate_studio import RealestateStudio

ROOT = Path(__file__).resolve().parent


@dataclass
class AntesDespues:
    nombre_obra: str
    municipio: str
    proyecto: str | None
    modo: str  # "real" | "ia" | "mixto"
    estilo_casa: str
    hectareas: float | int
    foto_antes_path: str
    foto_despues_path: str | None = None
    cliente: str | None = None
    fecha_inicio: str | None = None
    fecha_entrega: str | None = None
    tiempo_construccion_meses: int | None = None

    # Generados
    prompt_despues: str = ""
    instrucciones_img2img: list[str] = field(default_factory=list)
    carrusel: dict[str, Any] = field(default_factory=dict)
    caption_narrativo: str = ""
    hashtags: list[str] = field(default_factory=list)
    caption_completo: str = ""

    metadata: dict[str, Any] = field(default_factory=dict)
    fecha_creacion: str = field(
        default_factory=lambda: datetime.now().isoformat(timespec="seconds")
    )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class AntesDespuesFactory:
    """Generador de contenido antes/despues para Instagram."""

    ESTILOS_CASA = {
        "campo_tradicional": "casa de campo tradicional argentina con galería",
        "moderno_minimalista": "casa moderna minimalista con grandes ventanales",
        "steel_frame": "casa steel frame contemporánea",
        "colonial": "casa colonial con tejas y paredes blancas",
        "industrial_loft": "casa estilo industrial loft con estructura metálica vista",
        "toscana": "casa estilo toscano con piedra y tejados",
    }

    def __init__(self, studio: RealestateStudio):
        self.studio = studio

    # ---------------- API principal ----------------

    def generar(
        self,
        foto_antes_path: str,
        estilo_casa: str = "casa de campo tradicional con galería",
        hectareas: float | int = 1,
        municipio: str = "Cañuelas",
        proyecto: str | None = None,
        nombre_obra: str | None = None,
        foto_despues_path: str | None = None,
        cliente: str | None = None,
        fecha_inicio: str | None = None,
        fecha_entrega: str | None = None,
        tiempo_construccion_meses: int | None = None,
        modo: str | None = None,
    ) -> AntesDespues:
        if modo is None:
            modo = "real" if foto_despues_path else "ia"

        if modo not in ("real", "ia", "mixto"):
            raise ValueError(f"modo invalido: {modo}. Use 'real', 'ia' o 'mixto'.")

        ad = AntesDespues(
            nombre_obra=nombre_obra or proyecto or "Sin nombre",
            municipio=municipio,
            proyecto=proyecto,
            modo=modo,
            estilo_casa=estilo_casa,
            hectareas=hectareas,
            foto_antes_path=str(Path(foto_antes_path).resolve()),
            foto_despues_path=str(Path(foto_despues_path).resolve()) if foto_despues_path else None,
            cliente=cliente,
            fecha_inicio=fecha_inicio,
            fecha_entrega=fecha_entrega,
            tiempo_construccion_meses=tiempo_construccion_meses,
        )

        if modo == "ia":
            ad.prompt_despues = self._prompt_despues_sd(estilo_casa, hectareas, municipio)
            ad.instrucciones_img2img = self._instrucciones_img2img(foto_antes_path)

        ad.caption_narrativo = self._caption(ad)
        ad.hashtags = self.studio.post.hashtags(["casas", "construccion", "general"], municipio)
        ad.caption_completo = ad.caption_narrativo + "\n\n" + " ".join(ad.hashtags)

        ad.carrusel = self._carrusel_antes_despues(ad)
        ad.metadata = {
            "modo": modo,
            "tiene_foto_despues_real": bool(foto_despues_path),
            "requiere_generar_despues": modo in ("ia", "mixto"),
        }

        return ad

    # ---------------- Generadores ----------------

    def _prompt_despues_sd(self, estilo_casa: str, hectareas: float | int, municipio: str) -> str:
        """Prompt SDXL para generar el 'después' (sin foto de referencia)."""
        req = self.studio.construccion.render_proyecto(
            estilo=estilo_casa, hectareas=hectareas, municipio=municipio
        )
        return req.prompt

    @staticmethod
    def _instrucciones_img2img(foto_antes_path: str) -> list[str]:
        return [
            f"1. Subir foto del antes a Midjourney/DALL-E/Flux: {foto_antes_path}",
            "2. Usar modo img2img / image variation / image edit",
            "3. Prompt recomendado (variante del que genera el estudio):",
            "   'architectural rendering of a country house on this lot, "
            "traditional Argentine style, golden hour, photorealistic, "
            "preserve the same camera angle and horizon'",
            "4. Strength 0.45-0.60 para que mantenga la composición del lote",
            "5. Iterar 3-4 veces, elegir el que mejor conserve la tranquera / "
            "alambrados / horizonte",
            "6. (Opcional) Pasar el resultado por el módulo de mejora de fotos "
            "para sharpening y color grading",
        ]

    def _carrusel_antes_despues(self, ad: AntesDespues) -> dict[str, Any]:
        """Empaqueta el carrusel de 3-5 slides segun modo."""
        from carruseles import Slide

        slides: list[Slide] = []
        n = 1

        # Slide 1: Portada
        slides.append(
            Slide(
                numero=n,
                tipo="portada",
                descripcion=f"Portada: {ad.nombre_obra}",
                prompt="",
                texto_overlay=self._overlay_portada(ad),
                metadata={"requiere_foto_real": False, "tipo": "portada"},
            )
        )
        n += 1

        # Slide 2: Antes (placeholder con path)
        placeholder_antes = ad.foto_antes_path
        slides.append(
            Slide(
                numero=n,
                tipo="placeholder_foto",
                descripcion="Foto del antes: lote baldío / obra temprana",
                prompt="",
                texto_overlay="Esto era antes",
                metadata={
                    "requiere_foto_real": True,
                    "placeholder_foto_path": placeholder_antes,
                },
            )
        )
        n += 1

        # Slide 3: Despues (real o placeholder)
        if ad.modo == "real" and ad.foto_despues_path:
            slides.append(
                Slide(
                    numero=n,
                    tipo="placeholder_foto",
                    descripcion="Foto del después: casa terminada",
                    prompt="",
                    texto_overlay="Y esto es hoy",
                    metadata={
                        "requiere_foto_real": True,
                        "placeholder_foto_path": ad.foto_despues_path,
                    },
                )
            )
        else:
            # Modo IA: prompt SDXL para generar el después
            slides.append(
                Slide(
                    numero=n,
                    tipo="beneficio",
                    descripcion="Render del proyecto terminado (prompt para img2img)",
                    prompt=ad.prompt_despues,
                    texto_overlay="Y esto es lo que viene",
                    metadata={
                        "requiere_foto_real": False,
                        "tipo_prompt": "render_despues",
                        "workflow": "img2img con foto del antes",
                    },
                )
            )
        n += 1

        # Slide 4 (opcional): Tiempo / datos
        if ad.tiempo_construccion_meses or ad.fecha_inicio:
            tiempo = (
                f"{ad.tiempo_construccion_meses} meses de obra"
                if ad.tiempo_construccion_meses
                else f"De {ad.fecha_inicio} a {ad.fecha_entrega or 'hoy'}"
            )
            slides.append(
                Slide(
                    numero=n,
                    tipo="dato",
                    descripcion="Tiempo y proceso",
                    prompt="",
                    texto_overlay=f"⏱ {tiempo}",
                    metadata={
                        "requiere_foto_real": False,
                        "tipo": "dato",
                        "fecha_inicio": ad.fecha_inicio,
                        "fecha_entrega": ad.fecha_entrega,
                        "meses": ad.tiempo_construccion_meses,
                    },
                )
            )
            n += 1

        # Slide CTA
        slides.append(
            Slide(
                numero=n,
                tipo="cta",
                descripcion="Slide final: contacto",
                prompt="",
                texto_overlay="¿Arrancamos tu proyecto?\nDM o link en bio",
                metadata={"requiere_foto_real": False, "tipo": "cta"},
            )
        )

        # Renumerar
        for i, s in enumerate(slides):
            s.numero = i + 1

        return {
            "tema": f"Antes/Después: {ad.nombre_obra}",
            "tipo": "antes_despues",
            "municipio": ad.municipio,
            "tono": "emotivo",
            "slides": [s.to_dict() for s in slides],
            "n_slides": len(slides),
        }

    def _caption(self, ad: AntesDespues) -> str:
        cliente = ad.cliente or "esta familia"
        hectareas = ad.hectareas

        if ad.modo == "real":
            tiempo = ""
            if ad.tiempo_construccion_meses:
                tiempo = f"\n\n⏱ {ad.tiempo_construccion_meses} meses desde el primer replanteo hasta la entrega de llaves."
            elif ad.fecha_inicio and ad.fecha_entrega:
                tiempo = f"\n\n⏱ De {ad.fecha_inicio} a {ad.fecha_entrega}."

            return (
                f"🌾 Antes era esto.\n\n"
                f"Un lote baldío de {hectareas} ha en {ad.municipio}.\n"
                f"Hoy es la casa de {cliente}.{tiempo}\n\n"
                f"Diseño, movimiento de suelo, obra, terminaciones, llaves. "
                f"Un solo equipo. De la tranquera a la primera foto familiar.\n\n"
                f"¿Arrancamos el tuyo?\n\n"
                f"📍 {ad.municipio}, Buenos Aires"
            )

        # Modo IA o mixto: caption de preventa / proyecto
        return (
            f"🌱 Antes era un lote baldío en {ad.municipio}.\n\n"
            f"Después puede ser lo que vos quieras construir.\n\n"
            f"Te acompañamos de punta a punta: diseño, movimiento de suelo, "
            f"obra gruesa, terminaciones, llave en mano. {hectareas} ha en una "
            f"zona que va a explotar.\n\n"
            f"Deslizá para ver el proyecto conceptual ↓\n\n"
            f"📍 {ad.municipio}, Buenos Aires"
        )

    @staticmethod
    def _overlay_portada(ad: AntesDespues) -> str:
        cliente = ad.cliente or "este proyecto"
        return f"{cliente}\nAntes · Después"

    # ---------------- Persistencia ----------------

    def guardar(self, ad: AntesDespues) -> Path:
        if ad.proyecto:
            carpeta = ROOT / "inmuebles" / "obras" / ad.proyecto / "antes_despues"
        else:
            carpeta = ROOT / "inmuebles" / "obras" / "_generados"
        carpeta.mkdir(parents=True, exist_ok=True)

        # JSON principal
        json_path = carpeta / "antes_despues.json"
        json_path.write_text(
            json.dumps(ad.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8"
        )

        # Markdown
        md_path = carpeta / "antes_despues.md"
        md_path.write_text(self._a_markdown(ad), encoding="utf-8")

        # Caption IG
        ig_path = carpeta / "caption_instagram.txt"
        ig_path.write_text(ad.caption_completo, encoding="utf-8")

        # Slides
        slides_dir = carpeta / "slides"
        slides_dir.mkdir(exist_ok=True)
        for slide in ad.carrusel.get("slides", []):
            slide_path = slides_dir / f"slide_{slide['numero']:02d}_{slide['tipo']}.json"
            slide_path.write_text(json.dumps(slide, indent=2, ensure_ascii=False), encoding="utf-8")

        # Si la foto del antes existe, copiarla a inputs para referencia
        src = Path(ad.foto_antes_path)
        if src.exists() and src.is_file():
            inputs_dir = carpeta / "inputs"
            inputs_dir.mkdir(exist_ok=True)
            dst = inputs_dir / src.name
            if not dst.exists():
                shutil.copy2(src, dst)

        return carpeta

    @staticmethod
    def _a_markdown(ad: AntesDespues) -> str:
        lineas = [
            f"# Antes / Después: {ad.nombre_obra}",
            "",
            f"**Modo:** {ad.modo}  ",
            f"**Municipio:** {ad.municipio}  ",
            f"**Cliente:** {ad.cliente or '(sin asignar)'}  ",
            f"**Estilo de casa:** {ad.estilo_casa}  ",
            f"**Hectareas:** {ad.hectareas}  ",
            "",
            "## Inputs",
            "",
            f"- **Foto del antes:** `{ad.foto_antes_path}`",
        ]
        if ad.foto_despues_path:
            lineas.append(f"- **Foto del después:** `{ad.foto_despues_path}`")
        if ad.tiempo_construccion_meses:
            lineas.append(f"- **Tiempo de construcción:** {ad.tiempo_construccion_meses} meses")
        if ad.fecha_inicio:
            lineas.append(f"- **Fecha inicio:** {ad.fecha_inicio}")
        if ad.fecha_entrega:
            lineas.append(f"- **Fecha entrega:** {ad.fecha_entrega}")

        if ad.modo in ("ia", "mixto"):
            lineas.extend(
                [
                    "",
                    "## Prompt para generar el después (SDXL)",
                    "",
                    "```",
                    ad.prompt_despues,
                    "```",
                    "",
                    "## Instrucciones para img2img",
                    "",
                ]
            )
            for paso in ad.instrucciones_img2img:
                lineas.append(f"- {paso}")

        lineas.extend(
            [
                "",
                "## Carrusel",
                "",
                f"Total slides: **{ad.carrusel.get('n_slides', 0)}**",
                "",
                "| # | Tipo | Descripción | Texto overlay | Foto real requerida |",
                "|---|------|-------------|---------------|--------------------|",
            ]
        )
        for s in ad.carrusel.get("slides", []):
            req = "✅" if s["metadata"].get("requiere_foto_real") else "—"
            placeholder = s["metadata"].get("placeholder_foto_path", "")
            txt = s["texto_overlay"].replace("\n", " / ")
            lineas.append(
                f"| {s['numero']} | {s['tipo']} | {s['descripcion']} "
                f"| `{txt}` | {req} {placeholder} |"
            )

        lineas.extend(
            [
                "",
                "## Caption completo",
                "",
                "```",
                ad.caption_completo,
                "```",
            ]
        )

        return "\n".join(lineas)


def demo() -> None:
    """Demo: simula un antes/despues en modo IA sin foto real."""
    from realestate_studio import RealestateStudio

    studio = RealestateStudio()
    factory = AntesDespuesFactory(studio)

    # Modo IA (no requiere foto existente, solo genera el workflow)
    ad = factory.generar(
        foto_antes_path="inmuebles/lotes/chacra-canuelas-5ha/inputs/lote_baldio.jpg",
        estilo_casa="casa de campo tradicional con galería",
        hectareas=5,
        municipio="Cañuelas",
        proyecto="chacra-canuelas-5ha",
        cliente="Familia Pérez",
        tiempo_construccion_meses=8,
        modo="ia",
    )

    print("=" * 60)
    print(f"ANTES/DESPUES: {ad.nombre_obra}")
    print("=" * 60)
    print(f"Modo: {ad.modo}")
    print(f"Slides: {ad.carrusel['n_slides']}")
    print()
    print("--- Caption ---")
    print(ad.caption_narrativo)
    print()
    print("--- Workflow ---")
    for paso in ad.instrucciones_img2img[:3]:
        print(f"  {paso}")

    carpeta = factory.guardar(ad)
    print(f"\nGuardado en: {carpeta.relative_to(ROOT)}")


if __name__ == "__main__":
    demo()
