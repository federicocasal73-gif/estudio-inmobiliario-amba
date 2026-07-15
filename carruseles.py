"""
Modulo de carruseles automaticos para Instagram.
Genera slides con prompts visuales, texto overlay (como metadata) y un
caption narrativo que conecta toda la secuencia.

Cada Slide puede ser:
  - foto: prompt SDXL para generar la imagen con IA
  - placeholder_foto: marcador que vos reemplazás con foto real
  - dato: slide informativo (típicamente con texto overlay)

Uso desde opencode:
    from realestate_studio import RealestateStudio
    from carruseles import CarruselFactory
    studio = RealestateStudio()
    factory = CarruselFactory(studio)
    carrusel = factory.lote_premium("5 ha en Cañuelas", municipio="Cañuelas",
                                   hectareas=5, precio_usd="USD 60.000")
    factory.guardar(carrusel, proyecto="chacra-canuelas-5ha", nombre="lote_premium")
"""

from __future__ import annotations

import json
import random
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from realestate_studio import RealestateStudio

ROOT = Path(__file__).resolve().parent
LOTES_DIR = ROOT / "inmuebles" / "lotes"
OBRAS_DIR = ROOT / "inmuebles" / "obras"
SERVICIOS_DIR = ROOT / "inmuebles" / "servicios"
POSTS_DIR = ROOT / "inmuebles" / "posts"

ASPECT_INSTAGRAM_POST = "896*1152"


@dataclass
class Slide:
    numero: int
    tipo: str  # "portada" | "foto" | "dato" | "beneficio" | "cta" | "placeholder_foto"
    descripcion: str  # descripcion humana del slide
    prompt: str = ""  # prompt SDXL (vacio si es placeholder)
    texto_overlay: str = ""  # texto que va encima de la imagen
    aspect_ratio: str = ASPECT_INSTAGRAM_POST
    styles: list[str] = field(default_factory=lambda: ["Fooocus V2", "Fooocus Enhance"])
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Carrusel:
    tema: str
    tipo: str  # "lote_premium" | "country_etapa" | "obra_avance" | "servicios" | "antes_despues"
    municipio: str
    tono: str
    slides: list[Slide]
    caption_narrativo: str
    hashtags: list[str]
    fecha_creacion: str = field(
        default_factory=lambda: datetime.now().isoformat(timespec="seconds")
    )
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def n_slides(self) -> int:
        return len(self.slides)

    @property
    def caption_completo(self) -> str:
        return self.caption_narrativo + "\n\n" + " ".join(self.hashtags)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["n_slides"] = self.n_slides
        d["caption_completo"] = self.caption_completo
        return d


class CaptionNarrativo:
    """Une los slides en un texto continuo con ganchos entre ellos."""

    GANCHOS = [
        "Deslizá →",
        "Mirá esto →",
        "Seguimos →",
        "Ahora esto →",
        "Lo que viene →",
        "Y esto es lo que más nos gusta →",
        "Pero esperá, hay más →",
        "Ahora sí, lo importante →",
    ]

    CIERRES = [
        "Link en bio para más info.",
        "Escribinos al DM, te contamos.",
        "Apartá tu lugar hoy.",
        "Agenda una visita este finde.",
        "Te esperamos.",
        "Compartí este post con alguien que lo necesite.",
    ]

    @classmethod
    def unir(
        cls,
        tema: str,
        municipio: str,
        slides: list[Slide],
        tono: str = "emotivo",
        gancho_inicial: str | None = None,
    ) -> str:
        gancho = gancho_inicial or random.choice(cls.GANCHOS)
        lineas: list[str] = []

        if tono == "emotivo":
            lineas.append(f"🌾 {tema}")
            lineas.append("")
            lineas.append(f"Una historia en {len(slides)} imágenes. {gancho}")
            lineas.append("")
        elif tono == "inversion":
            lineas.append(f"📈 {tema}")
            lineas.append("")
            lineas.append(f"Los números cuentan mejor cuando los ves. {gancho}")
            lineas.append("")
        elif tono == "premium":
            lineas.append(f"✨ {tema}")
            lineas.append("")
            lineas.append(f"Las cosas que importan, en {len(slides)} slides. {gancho}")
            lineas.append("")
        else:
            lineas.append(f"{tema}")
            lineas.append("")
            lineas.append(f"{gancho}")
            lineas.append("")

        for i, slide in enumerate(slides):
            if slide.texto_overlay:
                lineas.append(f"Slide {i + 1}: {slide.texto_overlay}")
            else:
                lineas.append(f"Slide {i + 1}: {slide.descripcion}")
            if i < len(slides) - 1:
                lineas.append("")
                lineas.append(random.choice(cls.GANCHOS))
                lineas.append("")

        lineas.append("")
        lineas.append(f"📍 {municipio}, Buenos Aires")
        lineas.append("")
        lineas.append(random.choice(cls.CIERRES))

        return "\n".join(lineas)


class CarruselFactory:
    """Factory de los 4 tipos principales de carrusel."""

    def __init__(self, studio: RealestateStudio):
        self.studio = studio

    # ---------------- 1) LOTE PREMIUM ----------------

    def lote_premium(
        self,
        tema: str,
        municipio: str,
        hectareas: float | int,
        precio_usd: str | None = None,
        distancia_caba: str | None = None,
        tono: str = "emotivo",
        n_slides: int = 6,
    ) -> Carrusel:
        if n_slides < 4:
            n_slides = 4

        slides: list[Slide] = []

        # Slide 1: Portada
        req_portada = self.studio.lotes.chacra_pampeana(
            hectareas=hectareas, municipio=municipio, momento="atardecer"
        )
        slides.append(
            Slide(
                numero=1,
                tipo="portada",
                descripcion=f"Portada: chacra {hectareas} ha en {municipio} al atardecer",
                prompt=req_portada.prompt,
                aspect_ratio=req_portada.aspect_ratio,
                styles=req_portada.styles,
                texto_overlay=self._overlay_portada(hectareas, municipio, precio_usd),
                metadata={
                    "tipo_prompt": "chacra_pampeana",
                    "hectareas": hectareas,
                    "municipio": municipio,
                },
            )
        )

        # Slide 2: Vista aerea
        req_aerea = self.studio.lotes.vista_aerea_loteo(
            n_lotes=int(hectareas * 4) if isinstance(hectareas, (int, float)) else 20,
            municipio=municipio,
        )
        slides.append(
            Slide(
                numero=2,
                tipo="foto",
                descripcion="Vista aerea con drone del loteo",
                prompt=req_aerea.prompt,
                aspect_ratio=req_aerea.aspect_ratio,
                styles=req_aerea.styles,
                texto_overlay="Vista aérea · 360° de horizonte pampeano",
                metadata={"tipo_prompt": "vista_aerea_loteo", "municipio": municipio},
            )
        )

        # Slide 3: Tranquera
        req_tranquera = self.studio.lotes.tranquera_argentina(municipio=municipio)
        slides.append(
            Slide(
                numero=3,
                tipo="foto",
                descripcion="Detalle de tranquera de madera",
                prompt=req_tranquera.prompt,
                aspect_ratio=req_tranquera.aspect_ratio,
                styles=req_tranquera.styles,
                texto_overlay="Tu próxima tranquera · ingreso sobre calle mejorada",
                metadata={"tipo_prompt": "tranquera", "municipio": municipio},
            )
        )

        # Slide 4: Molino
        req_molino = self.studio.lotes.molino_tanque_australiano(municipio=municipio)
        slides.append(
            Slide(
                numero=4,
                tipo="foto",
                descripcion="Molino y tanque australiano funcionando",
                prompt=req_molino.prompt,
                aspect_ratio=req_molino.aspect_ratio,
                styles=req_molino.styles,
                texto_overlay="Agua propia · molino + tanque australiano",
                metadata={"tipo_prompt": "molino", "municipio": municipio},
            )
        )

        # Slide 5: Render del proyecto (si hay slide extra)
        if n_slides >= 6:
            req_render = self.studio.construccion.render_proyecto(
                estilo="casa de campo tradicional con galería",
                hectareas=hectareas,
                municipio=municipio,
            )
            slides.append(
                Slide(
                    numero=5,
                    tipo="beneficio",
                    descripcion="Render de casa posible sobre el lote",
                    prompt=req_render.prompt,
                    aspect_ratio=req_render.aspect_ratio,
                    styles=req_render.styles,
                    texto_overlay="Tu casa acá · te la diseñamos llave en mano",
                    metadata={"tipo_prompt": "render_proyecto", "municipio": municipio},
                )
            )

        # Slide final: CTA con datos
        slides.append(
            Slide(
                numero=len(slides) + 1,
                tipo="cta",
                descripcion="Slide final con datos de contacto",
                prompt="",
                aspect_ratio=ASPECT_INSTAGRAM_POST,
                styles=[],
                texto_overlay=self._overlay_cta(precio_usd, distancia_caba),
                metadata={"requiere_foto_real": False, "tipo": "cta"},
            )
        )

        caption = CaptionNarrativo.unir(tema, municipio, slides, tono)
        hashtags = self.studio.post.hashtags(["general", "campo", "inversion"], municipio)

        return Carrusel(
            tema=tema,
            tipo="lote_premium",
            municipio=municipio,
            tono=tono,
            slides=slides,
            caption_narrativo=caption,
            hashtags=hashtags,
            metadata={
                "hectareas": hectareas,
                "precio_usd": precio_usd,
                "distancia_caba": distancia_caba,
                "n_slides": len(slides),
            },
        )

    # ---------------- 2) COUNTRY ETAPA ----------------

    def country_etapa(
        self,
        nombre_country: str,
        municipio: str,
        etapa: str = "2",
        n_lotes: int = 12,
        precio_desde: str = "USD 85.000",
        amenities: str = "Club house, pileta, canchas de tenis, golf",
        distancia_caba: str = "45 km",
        tono: str = "premium",
        n_slides: int = 5,
    ) -> Carrusel:
        if n_slides < 3:
            n_slides = 3

        slides: list[Slide] = []

        # Slide 1: Portada (siempre)
        req = self.studio.lotes.country_premium(nombre=nombre_country, amenities=amenities)
        slides.append(
            Slide(
                numero=1,
                tipo="portada",
                descripcion=f"Portada: entrada de {nombre_country}",
                prompt=req.prompt,
                aspect_ratio=req.aspect_ratio,
                styles=req.styles,
                texto_overlay=f"{nombre_country}\nEtapa {etapa} disponible",
                metadata={"nombre_country": nombre_country, "etapa": etapa},
            )
        )

        # Slides intermedios segun n_slides:
        #   3 slides: portada + obra + cta
        #   4 slides: portada + masterplan + obra + cta
        #   5 slides: portada + masterplan + amenity + obra + cta
        #   6 slides: portada + masterplan + amenity + obra + render + cta
        #   7 slides: + dato
        intermedios: list[Slide] = []

        if n_slides >= 4:
            intermedios.append(
                Slide(
                    numero=len(slides) + len(intermedios) + 1,
                    tipo="foto",
                    descripcion="Masterplan del country con lotes marcados",
                    prompt=(
                        f"architectural masterplan visualization of {nombre_country} gated community "
                        f"in {municipio}, Buenos Aires province, {n_lotes} marked lots, "
                        f"roads, green spaces, club house, professional architectural rendering"
                    ),
                    aspect_ratio="1152*896",
                    styles=["Fooocus V2", "Fooocus Enhance", "misc-architectural"],
                    texto_overlay=f"{n_lotes} lotes · desde {precio_desde}",
                    metadata={"tipo_prompt": "masterplan"},
                )
            )

        if n_slides >= 5:
            intermedios.append(
                Slide(
                    numero=len(slides) + len(intermedios) + 1,
                    tipo="beneficio",
                    descripcion="Amenities del country",
                    prompt=(
                        f"luxury club house and amenities at {nombre_country} country, "
                        f"{amenities}, swimming pool, tennis courts, modern architecture, "
                        f"{municipio} Buenos Aires, blue hour photography"
                    ),
                    aspect_ratio="1152*896",
                    styles=["Fooocus V2", "Fooocus Enhance", "ads-luxury"],
                    texto_overlay=f"Amenities · {amenities}",
                    metadata={"amenities": amenities},
                )
            )

        if n_slides >= 3:
            req_obra = self.studio.lotes.loteo_en_desarrollo(
                etapa=f"Etapa {etapa}", municipio=municipio
            )
            intermedios.append(
                Slide(
                    numero=len(slides) + len(intermedios) + 1,
                    tipo="foto",
                    descripcion="Obra de movimiento de suelo en etapa actual",
                    prompt=req_obra.prompt,
                    aspect_ratio=req_obra.aspect_ratio,
                    styles=req_obra.styles,
                    texto_overlay=f"Etapa {etapa} · obra en curso",
                    metadata={"tipo_prompt": "loteo_en_desarrollo"},
                )
            )

        if n_slides >= 6:
            intermedios.append(
                Slide(
                    numero=len(slides) + len(intermedios) + 1,
                    tipo="beneficio",
                    descripcion="Render de lote con casa modelo",
                    prompt=(
                        f"architectural rendering of a modern country house at {nombre_country}, "
                        f"{municipio} Buenos Aires, manicured lawn, sunset, photorealistic"
                    ),
                    aspect_ratio="1152*896",
                    styles=["Fooocus V2", "Fooocus Enhance", "misc-architectural"],
                    texto_overlay="Casa modelo · te la entregamos llave en mano",
                    metadata={"tipo_prompt": "render_casa_country"},
                )
            )

        if n_slides >= 7:
            intermedios.append(
                Slide(
                    numero=len(slides) + len(intermedios) + 1,
                    tipo="dato",
                    descripcion="Dato clave del country",
                    prompt="",
                    aspect_ratio=ASPECT_INSTAGRAM_POST,
                    styles=[],
                    texto_overlay=f"Desde {precio_desde}\nA {distancia_caba} de CABA",
                    metadata={"requiere_foto_real": False, "tipo": "dato"},
                )
            )

        slides.extend(intermedios)

        # Renumerar
        for i, s in enumerate(slides):
            s.numero = i + 1

        # Slide CTA final
        slides.append(
            Slide(
                numero=len(slides) + 1,
                tipo="cta",
                descripcion="Slide final con datos para reservar",
                prompt="",
                aspect_ratio=ASPECT_INSTAGRAM_POST,
                styles=[],
                texto_overlay=self._overlay_cta_country(precio_desde, distancia_caba, n_lotes),
                metadata={"requiere_foto_real": False, "tipo": "cta"},
            )
        )

        # Renumerar tras agregar CTA
        for i, s in enumerate(slides):
            s.numero = i + 1

        caption = CaptionNarrativo.unir(
            f"{nombre_country} · Etapa {etapa}", municipio, slides, tono
        )
        hashtags = self.studio.post.hashtags(["country", "inversion"], municipio)

        return Carrusel(
            tema=f"{nombre_country} · Etapa {etapa}",
            tipo="country_etapa",
            municipio=municipio,
            tono=tono,
            slides=slides,
            caption_narrativo=caption,
            hashtags=hashtags,
            metadata={
                "nombre_country": nombre_country,
                "etapa": etapa,
                "n_lotes": n_lotes,
                "precio_desde": precio_desde,
                "n_slides": len(slides),
            },
        )

    # ---------------- 3) OBRA AVANCE ----------------

    def obra_avance(
        self,
        nombre_obra: str,
        municipio: str,
        semana: int,
        etapa: str,
        foto_antes_path: str | None = None,
        estilo_render: str = "casa de campo tradicional",
        hectareas: float | int = 1,
        tono: str = "practico",
        n_slides: int = 4,
    ) -> Carrusel:
        if n_slides < 3:
            n_slides = 3

        slides: list[Slide] = []

        # Slide 1: Portada
        req_obra = self.studio.construccion.obra_gruesa(etapa=etapa, municipio=municipio)
        slides.append(
            Slide(
                numero=1,
                tipo="portada",
                descripcion=f"Portada: obra {nombre_obra} semana {semana}",
                prompt=req_obra.prompt,
                aspect_ratio=req_obra.aspect_ratio,
                styles=req_obra.styles,
                texto_overlay=f"{nombre_obra}\nSemana {semana} · {etapa}",
                metadata={"nombre_obra": nombre_obra, "semana": semana, "etapa": etapa},
            )
        )

        # Slide 2: Foto real del avance (placeholder)
        if foto_antes_path:
            placeholder_path = str(Path(foto_antes_path).resolve())
            placeholder_desc = f"Foto real: {Path(foto_antes_path).name}"
            prompt_value = ""
        else:
            placeholder_path = f"inmuebles/obras/{nombre_obra.lower().replace(' ', '-')}/inputs/semana-{semana:02d}.jpg"
            placeholder_desc = f"Placeholder: foto real del avance de semana {semana}"
            prompt_value = ""

        slides.append(
            Slide(
                numero=2,
                tipo="placeholder_foto",
                descripcion=placeholder_desc,
                prompt=prompt_value,
                aspect_ratio=ASPECT_INSTAGRAM_POST,
                styles=[],
                texto_overlay=f"Semana {semana} · así viene avanzando",
                metadata={
                    "placeholder_foto_path": placeholder_path,
                    "requiere_foto_real": True,
                    "semana": semana,
                },
            )
        )

        # Slide 3: Render de cómo va a quedar
        if n_slides >= 4:
            req_render = self.studio.construccion.render_proyecto(
                estilo=estilo_render, hectareas=hectareas, municipio=municipio
            )
            slides.append(
                Slide(
                    numero=3,
                    tipo="beneficio",
                    descripcion=f"Render objetivo: {estilo_render}",
                    prompt=req_render.prompt,
                    aspect_ratio=req_render.aspect_ratio,
                    styles=req_render.styles,
                    texto_overlay=f"Hacia dónde vamos · {estilo_render}",
                    metadata={"tipo_prompt": "render_proyecto", "estilo": estilo_render},
                )
            )
            slide_cta_idx = 4
        else:
            slide_cta_idx = 3

        # Slide CTA
        slides.append(
            Slide(
                numero=slide_cta_idx,
                tipo="cta",
                descripcion="Próximos pasos + contacto",
                prompt="",
                aspect_ratio=ASPECT_INSTAGRAM_POST,
                styles=[],
                texto_overlay=f"Próxima semana: {self._proxima_etapa(etapa)}\n\nTe contamos más por DM",
                metadata={"requiere_foto_real": False, "tipo": "cta", "etapa_actual": etapa},
            )
        )

        caption = CaptionNarrativo.unir(
            f"Obra {nombre_obra} · Semana {semana}", municipio, slides, tono
        )
        hashtags = self.studio.post.hashtags(["construccion", "casas"], municipio)

        return Carrusel(
            tema=f"Obra {nombre_obra} · Semana {semana}",
            tipo="obra_avance",
            municipio=municipio,
            tono=tono,
            slides=slides,
            caption_narrativo=caption,
            hashtags=hashtags,
            metadata={
                "nombre_obra": nombre_obra,
                "semana": semana,
                "etapa": etapa,
                "hectareas": hectareas,
                "n_slides": len(slides),
            },
        )

    # ---------------- 4) SERVICIOS ----------------

    def servicios(
        self,
        empresa: str = "Construcciones Rurales",
        municipio: str = "Cañuelas",
        servicios: list[str] | None = None,
        tonos_por_slide: list[str] | None = None,
        tono: str = "premium",
        n_slides: int = 6,
    ) -> Carrusel:
        if servicios is None:
            servicios = [
                "Diseño arquitectónico",
                "Movimiento de suelo y topografía",
                "Obra gruesa y estructura",
                "Construcción en seco · Steel Frame",
                "Terminaciones e instalaciones",
                "Llave en mano",
            ]
        else:
            n_slides = len(servicios) + 2  # portada + servicios + cta

        if tonos_por_slide is None:
            tonos_por_slide = ["premium"] * len(servicios)

        slides: list[Slide] = []

        # Slide 1: Portada
        prompt_portada = (
            f"modern construction company logo wall, {empresa}, "
            f"construction equipment background, professional photography, "
            f"Buenos Aires Argentina, blue hour, corporate branding"
        )
        slides.append(
            Slide(
                numero=1,
                tipo="portada",
                descripcion=f"Portada: ¿Qué hace {empresa}?",
                prompt=prompt_portada,
                aspect_ratio=ASPECT_INSTAGRAM_POST,
                styles=["Fooocus V2", "Fooocus Enhance", "ads-real estate"],
                texto_overlay=f"¿Qué hace {empresa}?\nDel plano a la llave",
                metadata={"empresa": empresa},
            )
        )

        # Slides de servicios (1 por servicio)
        prompts_servicios = {
            "Diseño arquitectónico": (
                "architect working on blueprints at desk, modern studio, "
                "renders on screen, professional photography"
            ),
            "Movimiento de suelo y topografía": (
                "heavy machinery doing earthworks, bulldozer, retroexcavadora, "
                "professional construction photography, dust, golden hour"
            ),
            "Obra gruesa y estructura": (
                "residential concrete structure construction, brick walls rising, "
                "rebar, scaffolding, professional construction photography"
            ),
            "Construcción en seco · Steel Frame": (
                "steel frame house under construction, metal structure, panels, "
                "modern construction method, professional photography"
            ),
            "Terminaciones e instalaciones": (
                "luxury interior finishing work, drywall, painting, "
                "high-end details, professional photography"
            ),
            "Llave en mano": (
                "beautiful finished country house with family at entrance, "
                "keys handoff moment, sunset, professional photography"
            ),
        }

        for i, servicio in enumerate(servicios):
            prompt = prompts_servicios.get(
                servicio, f"professional photography of {servicio}, construction industry"
            )
            slides.append(
                Slide(
                    numero=len(slides) + 1,
                    tipo="beneficio",
                    descripcion=f"Servicio {i + 1}: {servicio}",
                    prompt=prompt,
                    aspect_ratio=ASPECT_INSTAGRAM_POST,
                    styles=["Fooocus V2", "Fooocus Enhance", "ads-real estate"],
                    texto_overlay=f"{i + 1}. {servicio}",
                    metadata={"servicio": servicio, "orden": i + 1},
                )
            )

        # Slide CTA final
        slides.append(
            Slide(
                numero=len(slides) + 1,
                tipo="cta",
                descripcion="Slide final: cómo empezar tu proyecto",
                prompt="",
                aspect_ratio=ASPECT_INSTAGRAM_POST,
                styles=[],
                texto_overlay=f"¿Arrancamos?\n\nEscribinos al DM o link en bio.\n\n📍 {municipio}, Buenos Aires",
                metadata={"requiere_foto_real": False, "tipo": "cta"},
            )
        )

        caption = CaptionNarrativo.unir(f"{empresa} · qué hacemos", municipio, slides, tono)
        hashtags = self.studio.post.hashtags(["construccion", "casas", "general"], municipio)
        hashtags = [h for h in hashtags if h != "#casas"] + ["#casasllaveenmano"]

        return Carrusel(
            tema=f"{empresa} · Servicios",
            tipo="servicios",
            municipio=municipio,
            tono=tono,
            slides=slides,
            caption_narrativo=caption,
            hashtags=hashtags,
            metadata={"empresa": empresa, "servicios": servicios, "n_slides": len(slides)},
        )

    # ---------------- Mejora de fotos en slides (gap #10) ----------------

    def aplicar_mejora_a_slide(
        self,
        carrusel: Carrusel,
        n_slide: int,
        modo: str = "magazine",
        intensidad: str = "media",
        upscale: int = 1,
    ) -> dict[str, Any]:
        """Aplica mejora de foto a la imagen del slide n_slide.

        Retorna info de la mejora aplicada o error si no hay imagen.
        """
        from mejora_fotos import MejoraFotos

        if n_slide < 1 or n_slide > len(carrusel.slides):
            raise ValueError(f"n_slide fuera de rango: {n_slide} (1..{len(carrusel.slides)})")

        slide = carrusel.slides[n_slide - 1]
        if slide.tipo != "placeholder_foto":
            return {
                "exito": False,
                "n_slide": n_slide,
                "tipo_slide": slide.tipo,
                "mensaje": "El slide no es placeholder_foto, no requiere imagen real",
            }

        placeholder_path = slide.metadata.get("placeholder_foto_path", "")
        if not placeholder_path:
            return {
                "exito": False,
                "n_slide": n_slide,
                "tipo_slide": slide.tipo,
                "mensaje": "No hay placeholder_foto_path configurado",
            }

        path = Path(placeholder_path)
        if not path.is_absolute():
            path = (ROOT / placeholder_path).resolve()

        if not path.exists():
            return {
                "exito": False,
                "n_slide": n_slide,
                "path_buscado": str(path),
                "mensaje": f"Imagen no encontrada: {path}",
            }

        mejora = MejoraFotos()
        resultado = mejora.mejorar(
            foto_path=path,
            modo=modo,
            intensidad=intensidad,
            upscale=upscale,
        )

        return {
            "exito": True,
            "n_slide": n_slide,
            "tipo_slide": slide.tipo,
            "path_original": str(path),
            "path_mejorada": resultado.foto_destino,
            "modo": modo,
            "intensidad": intensidad,
            "upscale": upscale,
            "transformaciones": resultado.transformaciones,
        }

    def aplicar_mejora_a_todos_los_placeholders(
        self,
        carrusel: Carrusel,
        modo: str = "magazine",
        intensidad: str = "media",
        upscale: int = 1,
    ) -> list[dict[str, Any]]:
        """Aplica mejora a todos los slides de tipo placeholder_foto."""
        placeholders = [s for s in carrusel.slides if s.tipo == "placeholder_foto"]
        resultados = []
        for slide in placeholders:
            r = self.aplicar_mejora_a_slide(carrusel, slide.numero, modo, intensidad, upscale)
            resultados.append(r)
        return resultados

    # ---------------- Story + Reel (gap #17) ----------------

    def story(
        self,
        tema: str,
        municipio: str,
        imagen_prompts: list[str] | None = None,
        duracion_por_slide: int = 5,
        tono: str = "emotivo",
    ) -> Carrusel:
        """Story de Instagram (9:16, formato vertical).

        imagen_prompts: lista de prompts para cada slide (opcional)
        duracion_por_slide: segundos (5 default)
        """
        from realestate_studio import ASPECT_INSTAGRAM_STORY

        if imagen_prompts is None:
            imagen_prompts = [
                self.studio.lotes.chacra_pampeana(hectareas=5, municipio=municipio).prompt,
                self.studio.lotes.amanecer_pampa(municipio=municipio).prompt,
                self.studio.lotes.tranquera_argentina(municipio=municipio).prompt,
            ]

        slides: list[Slide] = []
        for i, prompt in enumerate(imagen_prompts, 1):
            slides.append(
                Slide(
                    numero=i,
                    tipo="foto",
                    descripcion=f"Story {i}/{len(imagen_prompts)}",
                    prompt=prompt,
                    aspect_ratio=ASPECT_INSTAGRAM_STORY,
                    styles=["Fooocus V2", "Fooocus Enhance"],
                    texto_overlay=tema if i == 1 else "",
                    metadata={"duracion_segundos": duracion_por_slide, "formato": "story"},
                )
            )

        caption = (
            f"📲 Story: {tema}\n\n"
            f"Te mostramos en {len(imagen_prompts)} imagenes. "
            f"Volve a verla las veces que quieras antes de que se borre en 24 hs.\n\n"
            f"📍 {municipio}, Buenos Aires"
        )
        hashtags = self.studio.post.hashtags(["general", "inversion"], municipio)
        return Carrusel(
            tema=f"Story: {tema}",
            tipo="story",
            municipio=municipio,
            tono=tono,
            slides=slides,
            caption_narrativo=caption,
            hashtags=hashtags,
            metadata={
                "formato": "story",
                "aspect_ratio": ASPECT_INSTAGRAM_STORY,
                "n_slides": len(slides),
            },
        )

    def reel(
        self,
        tema: str,
        municipio: str,
        prompt_principal: str | None = None,
        duracion_segundos: int = 30,
        tono: str = "emotivo",
    ) -> Carrusel:
        """Reel de Instagram (1 slide, 9:16, caption corto).

        prompt_principal: prompt para la imagen principal del reel
        duracion_segundos: duracion del video (15-90)
        """
        from realestate_studio import ASPECT_INSTAGRAM_STORY

        if prompt_principal is None:
            prompt_principal = self.studio.lotes.chacra_pampeana(
                hectareas=5, municipio=municipio
            ).prompt

        # Caption corto tipo hook para reel
        caption_corto = self.studio.post.post_reel_hook(tema=tema, tono=tono)["caption"]

        slides: list[Slide] = [
            Slide(
                numero=1,
                tipo="portada",
                descripcion=f"Reel: {tema}",
                prompt=prompt_principal,
                aspect_ratio=ASPECT_INSTAGRAM_STORY,
                styles=["Fooocus V2", "Fooocus Enhance", "ads-luxury"],
                texto_overlay=tema,
                metadata={"duracion_segundos": duracion_segundos, "formato": "reel"},
            )
        ]
        hashtags = self.studio.post.hashtags(["general", "inversion"], municipio)
        return Carrusel(
            tema=f"Reel: {tema}",
            tipo="reel",
            municipio=municipio,
            tono=tono,
            slides=slides,
            caption_narrativo=caption_corto,
            hashtags=hashtags,
            metadata={
                "formato": "reel",
                "aspect_ratio": ASPECT_INSTAGRAM_STORY,
                "duracion_segundos": duracion_segundos,
                "n_slides": 1,
            },
        )

    # ---------------- Carruseles especificos de construccion ----------------

    def etapas_construccion(
        self, metros_cuadrados: int = 120, municipio: str = "Cañuelas", n_slides: int = 10
    ) -> Carrusel:
        """Carrusel mostrando las 8-10 etapas de una obra completa."""
        if n_slides < 8:
            n_slides = 8

        etapas = [
            ("replanteo_obra", "Etapa 1: Replanteo", "Marcamos ejes y limites en {municipio}"),
            ("excavacion_fundaciones", "Etapa 2: Excavacion", "Zanjas para fundaciones"),
            ("fundaciones_hormigon", "Etapa 3: Fundaciones", "Hormigon visto con armadura"),
            ("estructura_hormigon", "Etapa 4: Estructura", "Columnas y vigas H°A°"),
            ("mamposteria_ladrillo", "Etapa 5: Mamposteria", "Paredes de ladrillo"),
            ("cubierta_techo", "Etapa 6: Cubierta", "Techo y aislacion"),
            ("revoque_grueso", "Etapa 7: Revoques", "Grueso y fino"),
            ("colocacion_aberturas", "Etapa 8: Aberturas", "Ventanas DVH"),
            ("colocacion_pisos", "Etapa 9: Pisos", "Porcelanato o vinilico"),
            ("pintura_interior", "Etapa 10: Pintura", "Interior y exterior"),
        ]
        etapas_usar = etapas[:n_slides]

        slides: list[Slide] = []
        for i, (tipo_prompt, titulo, desc) in enumerate(etapas_usar, 1):
            req = getattr(self.studio.construccion, tipo_prompt)(municipio=municipio)
            slides.append(
                Slide(
                    numero=i,
                    tipo="foto",
                    descripcion=f"{titulo} - {desc}",
                    prompt=req.prompt,
                    aspect_ratio=req.aspect_ratio,
                    styles=req.styles,
                    texto_overlay=titulo,
                    metadata={"tipo_prompt": tipo_prompt, "etapa": i},
                )
            )

        caption = (
            f"🔨 Como se construye una casa en {n_slides} pasos\n\n"
            f"Te mostramos el proceso completo de una casa de {metros_cuadrados} m² "
            f"en {municipio}, desde el replanteo hasta la entrega de llaves.\n\n"
            f"⏱ Plazo total: 8-12 meses dependiendo del sistema constructivo.\n"
            f"💬 Te interesa saber mas? Pedinos el desglose por etapa."
        )
        hashtags = self.studio.post.hashtags(
            ["construccion", "ingenieria", "arquitectura"], municipio
        )
        return Carrusel(
            tema=f"Etapas de construcción en {municipio}",
            tipo="etapas_construccion",
            municipio=municipio,
            tono="educativo",
            slides=slides,
            caption_narrativo=caption,
            hashtags=hashtags,
            metadata={
                "formato": "carrusel_etapas",
                "n_etapas": n_slides,
                "metros_cuadrados": metros_cuadrados,
            },
        )

    def steel_frame_completo(
        self, municipio: str = "Cañuelas", metros_cuadrados: int = 120, n_slides: int = 6
    ) -> Carrusel:
        """Carrusel completo del sistema steel frame."""
        if n_slides < 5:
            n_slides = 5

        items = [
            ("anteproyecto_arquitectonico", "1. Diseño", "Planos y renders"),
            ("steel_frame_estructura", "2. Estructura", "Perfiles de acero galvanizado"),
            ("steel_frame_cerramiento", "3. Cerramiento", "Placas cementicias"),
            ("colocacion_aberturas", "4. Instalaciones", "Electricidad, sanitaria, gas"),
            ("revoque_grueso", "5. Terminaciones", "Revoques y pintura"),
            ("casa_terminada_frente", "6. Casa terminada", "Lista para habitar"),
        ]
        items_usar = items[:n_slides]

        slides: list[Slide] = []
        for i, (tipo_prompt, titulo, desc) in enumerate(items_usar, 1):
            req = getattr(self.studio.construccion, tipo_prompt)(municipio=municipio)
            slides.append(
                Slide(
                    numero=i,
                    tipo="foto",
                    descripcion=f"{titulo} - {desc}",
                    prompt=req.prompt,
                    aspect_ratio=req.aspect_ratio,
                    styles=req.styles,
                    texto_overlay=titulo,
                    metadata={"tipo_prompt": tipo_prompt, "etapa": i},
                )
            )

        caption = (
            f"⚙️ Steel Frame: el sistema constructivo del futuro\n\n"
            f"Casa de {metros_cuadrados} m² en {municipio}, Buenos Aires.\n\n"
            f"✓ Plazo: 30% mas rapido que tradicional\n"
            f"✓ Peso: 60% mas liviano\n"
            f"✓ Aislacion termica y acustica superior\n"
            f"✓ Resistente a sismos\n"
            f"✓ Construccion en seco = menos humedad\n\n"
            f"Te interesa construir en steel frame? Escribinos."
        )
        hashtags = self.studio.post.hashtags(["construccion", "casas", "ingenieria"], municipio)
        return Carrusel(
            tema=f"Steel Frame en {municipio}",
            tipo="steel_frame",
            municipio=municipio,
            tono="educativo",
            slides=slides,
            caption_narrativo=caption,
            hashtags=hashtags,
            metadata={
                "sistema": "steel_frame",
                "metros_cuadrados": metros_cuadrados,
                "n_slides": n_slides,
            },
        )

    def llave_en_mano_completo(
        self,
        municipio: str = "Cañuelas",
        metros_cuadrados: int = 130,
        precio_desde: str = "USD 95.000",
        n_slides: int = 8,
    ) -> Carrusel:
        """Carrusel explicando que incluye 'llave en mano'."""
        if n_slides < 7:
            n_slides = 7

        items = [
            ("render_exterior_casa", "1. Diseño 3D", "Ves tu casa antes de construirla"),
            ("estudio_de_suelo", "2. Estudio de suelo", "Garantizamos que tu casa no se hunde"),
            ("permisos_tramites", "3. Permisos", "Gestion municipal completa"),
            ("movimiento_suelo", "4. Movimiento de suelo", "Maquinaria pesada propia"),
            ("casa_terminada_frente", "5. Obra", "Tradicional o steel frame"),
            ("diseno_interior_acabados", "6. Diseño de interiores", "Asesoria de deco incluida"),
            ("entrega_llaves", "7. Entrega", "Te damos las llaves"),
            ("garantia_postventa", "8. Postventa", "10 años garantia estructura"),
        ]
        items_usar = items[:n_slides]

        slides: list[Slide] = []
        for i, (tipo_prompt, titulo, desc) in enumerate(items_usar, 1):
            try:
                req = getattr(self.studio.construccion, tipo_prompt)(municipio=municipio)
            except AttributeError:
                # Si no existe el metodo, usar otro generico
                req = self.studio.lotes.chacra_pampeana(
                    hectareas=metros_cuadrados / 10000, municipio=municipio
                )
            slides.append(
                Slide(
                    numero=i,
                    tipo="foto",
                    descripcion=f"{titulo} - {desc}",
                    prompt=req.prompt,
                    aspect_ratio=req.aspect_ratio,
                    styles=req.styles,
                    texto_overlay=titulo,
                    metadata={"tipo_prompt": tipo_prompt, "etapa": i},
                )
            )

        caption = (
            f"🔑 Llave en mano: que incluye?\n\n"
            f"Casa de {metros_cuadrados} m² en {municipio}, Buenos Aires.\n"
            f"Desde {precio_desde}.\n\n"
            f"NOSOTROS nos ocupamos de TODO:\n"
            f"✓ Diseño arquitectonico\n"
            f"✓ Tramites municipales\n"
            f"✓ Movimiento de suelo y fundaciones\n"
            f"✓ Obra gruesa y terminaciones\n"
            f"✓ Instalaciones completas\n"
            f"✓ Diseño de interiores\n"
            f"✓ Entrega llave en mano\n"
            f"✓ Garantia postventa\n\n"
            f"Un solo equipo. Un solo presupuesto. Una sola llamada."
        )
        hashtags = self.studio.post.hashtags(["construccion", "casas", "general"], municipio)
        return Carrusel(
            tema=f"Llave en mano en {municipio}",
            tipo="llave_en_mano",
            municipio=municipio,
            tono="premium",
            slides=slides,
            caption_narrativo=caption,
            hashtags=hashtags,
            metadata={
                "modalidad": "llave_en_mano",
                "precio_desde": precio_desde,
                "metros_cuadrados": metros_cuadrados,
                "n_slides": n_slides,
            },
        )

    def terminaciones_detalle(self, municipio: str = "Cañuelas", n_slides: int = 6) -> Carrusel:
        """Carrusel de terminaciones (los detalles que importan)."""
        if n_slides < 5:
            n_slides = 5

        items = [
            ("revoque_grueso", "1. Revoques", "Base solida para todo lo que viene"),
            ("colocacion_aberturas", "2. Aberturas DVH", "Doble vidrio hermetico"),
            ("colocacion_pisos", "3. Pisos", "Porcelanato o madera"),
            ("pintura_interior", "4. Pintura", "Latex interior + exterior"),
            ("fachada_moderna_minimalista", "5. Fachada", "Detalle final exterior"),
            ("render_interior_casa", "6. Interior", "Ambientes terminados"),
        ]
        items_usar = items[:n_slides]

        slides: list[Slide] = []
        for i, (tipo_prompt, titulo, desc) in enumerate(items_usar, 1):
            try:
                req = getattr(self.studio.construccion, tipo_prompt)(municipio=municipio)
            except AttributeError:
                req = self.studio.lotes.chacra_pampeana(hectareas=1, municipio=municipio)
            slides.append(
                Slide(
                    numero=i,
                    tipo="foto",
                    descripcion=f"{titulo} - {desc}",
                    prompt=req.prompt,
                    aspect_ratio=req.aspect_ratio,
                    styles=req.styles,
                    texto_overlay=titulo,
                    metadata={"tipo_prompt": tipo_prompt, "etapa": i},
                )
            )

        caption = (
            f"✨ Las terminaciones son la diferencia\n\n"
            f"Una casa puede tener la mejor estructura del mundo, pero si las "
            f"terminaciones son malas, se ve mal.\n\n"
            f"Te mostramos los 6 detalles que importan:\n"
            f"• Revoques nivelados\n"
            f"• Aberturas DVH (doble vidrio)\n"
            f"• Pisos de calidad\n"
            f"• Pintura profesional\n"
            f"• Fachada con proteccion hidrofuga\n"
            f"• Interiores con iluminacion adecuada\n\n"
            f"En {municipio} trabajamos con materiales premium en cada detalle."
        )
        hashtags = self.studio.post.hashtags(
            ["construccion", "casas", "diseno_interior"], municipio
        )
        return Carrusel(
            tema=f"Terminaciones que importan ({municipio})",
            tipo="terminaciones",
            municipio=municipio,
            tono="aspiracional",
            slides=slides,
            caption_narrativo=caption,
            hashtags=hashtags,
            metadata={"formato": "carrusel_terminaciones", "n_slides": n_slides},
        )

    def obra_completa(
        self,
        nombre_obra: str,
        municipio: str = "Cañuelas",
        metros_cuadrados: int = 130,
        estilo: str = "minimalista moderno",
        n_slides: int = 8,
    ) -> Carrusel:
        """Carrusel 'obra completa' con before/after + etapas clave."""
        if n_slides < 6:
            n_slides = 6

        items = [
            ("loteo_en_desarrollo", "0. Antes", "Lote baldío"),
            ("replanteo_obra", "1. Replanteo", "Marcamos los ejes"),
            ("fundaciones_hormigon", "2. Fundaciones", "Hormigon + armadura"),
            ("estructura_hormigon", "3. Estructura", "Columnas y vigas"),
            ("casa_terminada_frente", "4. Casa terminada", f"{estilo} {metros_cuadrados} m²"),
            ("entrega_llaves", "5. Entrega", "Llave en mano"),
            ("fachada_moderna_minimalista", "6. Detalle", f"{estilo}"),
            ("render_interior_casa", "7. Interior", "Ambientes terminados"),
        ]
        items_usar = items[:n_slides]

        slides: list[Slide] = []
        for i, (tipo_prompt, titulo, desc) in enumerate(items_usar, 1):
            try:
                req = getattr(self.studio.construccion, tipo_prompt)(municipio=municipio)
            except AttributeError:
                req = self.studio.lotes.loteo_en_desarrollo(etapa="Etapa 1", municipio=municipio)
            slides.append(
                Slide(
                    numero=i,
                    tipo="foto",
                    descripcion=f"{titulo} - {desc}",
                    prompt=req.prompt,
                    aspect_ratio=req.aspect_ratio,
                    styles=req.styles,
                    texto_overlay=titulo,
                    metadata={"tipo_prompt": tipo_prompt, "etapa": i, "nombre_obra": nombre_obra},
                )
            )

        caption = (
            f"🏡 Obra {nombre_obra} - proceso completo\n\n"
            f"En {municipio}, Buenos Aires. Casa {estilo} de {metros_cuadrados} m².\n\n"
            f"Del lote baldío a la entrega de llaves. "
            f"{n_slides} pasos clave que te mostramos hoy.\n\n"
            f"¿Tenés un proyecto similar? Arranquemos con un render."
        )
        hashtags = self.studio.post.hashtags(["construccion", "casas", "arquitectura"], municipio)
        return Carrusel(
            tema=f"Obra {nombre_obra}",
            tipo="obra_completa",
            municipio=municipio,
            tono="emotivo",
            slides=slides,
            caption_narrativo=caption,
            hashtags=hashtags,
            metadata={
                "nombre_obra": nombre_obra,
                "estilo": estilo,
                "metros_cuadrados": metros_cuadrados,
                "n_slides": n_slides,
            },
        )

    # ---------------- Persistencia ----------------

    def guardar(
        self, carrusel: Carrusel, nombre: str, proyecto: str | None = None, vertical: str = "lotes"
    ) -> Path:
        if proyecto and vertical in ("lotes", "obras"):
            carpeta = ROOT / "inmuebles" / vertical / proyecto / "carruseles" / nombre
        else:
            carpeta = ROOT / "inmuebles" / vertical / "carruseles" / nombre
        carpeta.mkdir(parents=True, exist_ok=True)

        # JSON completo
        json_path = carpeta / "carrusel.json"
        json_path.write_text(
            json.dumps(carrusel.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8"
        )

        # Slides individuales como prompts
        slides_dir = carpeta / "slides"
        slides_dir.mkdir(exist_ok=True)
        for slide in carrusel.slides:
            slide_path = slides_dir / f"slide_{slide.numero:02d}_{slide.tipo}.json"
            slide_data = slide.to_dict()
            slide_path.write_text(
                json.dumps(slide_data, indent=2, ensure_ascii=False), encoding="utf-8"
            )

        # Markdown imprimible
        md_path = carpeta / "carrusel.md"
        md_path.write_text(self._a_markdown(carrusel), encoding="utf-8")

        # Caption plano para Instagram
        ig_path = carpeta / "caption_instagram.txt"
        ig_path.write_text(carrusel.caption_completo, encoding="utf-8")

        return carpeta

    @staticmethod
    def _a_markdown(carrusel: Carrusel) -> str:
        lineas: list[str] = [
            f"# {carrusel.tema}",
            "",
            f"**Tipo:** {carrusel.tipo}  ",
            f"**Municipio:** {carrusel.municipio}  ",
            f"**Tono:** {carrusel.tono}  ",
            f"**Slides:** {carrusel.n_slides}  ",
            f"**Fecha:** {carrusel.fecha_creacion}  ",
            "",
            "## Slides",
            "",
        ]
        for slide in carrusel.slides:
            lineas.append(f"### Slide {slide.numero} · {slide.tipo}")
            lineas.append(f"_{slide.descripcion}_")
            if slide.texto_overlay:
                lineas.append("")
                lineas.append(f"**Texto overlay:** `{slide.texto_overlay}`")
            if slide.prompt:
                lineas.append("")
                lineas.append("**Prompt SDXL:**")
                lineas.append("```")
                lineas.append(slide.prompt)
                lineas.append("```")
            if slide.metadata.get("placeholder_foto_path"):
                lineas.append("")
                lineas.append(f"**Foto requerida:** `{slide.metadata['placeholder_foto_path']}`")
            lineas.append("")

        lineas.append("## Caption narrativo")
        lineas.append("")
        lineas.append("```")
        lineas.append(carrusel.caption_narrativo)
        lineas.append("```")
        lineas.append("")
        lineas.append("## Hashtags")
        lineas.append("")
        lineas.append(" ".join(carrusel.hashtags))
        lineas.append("")
        lineas.append("## Caption completo para IG")
        lineas.append("")
        lineas.append("```")
        lineas.append(carrusel.caption_completo)
        lineas.append("```")
        return "\n".join(lineas)

    # ---------------- Helpers ----------------

    @staticmethod
    def _overlay_portada(hectareas, municipio, precio_usd) -> str:
        partes = [f"{hectareas} ha"]
        partes.append(municipio)
        if precio_usd:
            partes.append(precio_usd)
        return " · ".join(partes)

    @staticmethod
    def _overlay_cta(precio_usd, distancia_caba) -> str:
        partes = ["¿Lo vemos?"]
        if precio_usd:
            partes.append(precio_usd)
        if distancia_caba:
            partes.append(f"A {distancia_caba} de CABA")
        partes.append("DM o link en bio")
        return "\n".join(partes)

    @staticmethod
    def _overlay_cta_country(precio_desde, distancia_caba, n_lotes) -> str:
        partes = ["Últimas unidades"]
        partes.append(f"Desde {precio_desde}")
        partes.append(f"A {distancia_caba} de CABA")
        partes.append(f"Solo {n_lotes} lotes · apartá con señal")
        return "\n".join(partes)

    @staticmethod
    def _proxima_etapa(etapa_actual: str) -> str:
        orden = [
            "replanteo y movimiento de suelo",
            "fundaciones",
            "estructura y columnas",
            "mampostería",
            "losas y techos",
            "instalaciones",
            "revoques y terminaciones",
            "aberturas",
            "pisos y revestimientos",
            "pintura",
            "entrega de llaves",
        ]
        actual = etapa_actual.lower()
        for i, etapa in enumerate(orden):
            if etapa in actual or actual in etapa:
                if i + 1 < len(orden):
                    return orden[i + 1]
        return "avance de obra"


def demo() -> None:
    """Demostración rápida de los 4 tipos de carrusel."""
    from realestate_studio import RealestateStudio

    studio = RealestateStudio()
    factory = CarruselFactory(studio)

    print("=" * 60)
    print("CARRUSELES - Demo")
    print("=" * 60)

    # 1) Lote premium
    c1 = factory.lote_premium(
        tema="5 ha en Cañuelas, a 65 km de CABA",
        municipio="Cañuelas",
        hectareas=5,
        precio_usd="USD 60.000",
        distancia_caba="65 km",
        tono="emotivo",
        n_slides=6,
    )
    print(f"\n[1] lote_premium: {c1.n_slides} slides")
    print(f"    Caption ({len(c1.caption_narrativo)} chars):")
    print(c1.caption_narrativo[:200] + "...")

    # 2) Country etapa
    c2 = factory.country_etapa(
        nombre_country="El Casco", municipio="Pilar", etapa="2", n_lotes=12, n_slides=5
    )
    print(f"\n[2] country_etapa: {c2.n_slides} slides")

    # 3) Obra avance
    c3 = factory.obra_avance(
        nombre_obra="Casa Pérez", municipio="Escobar", semana=3, etapa="mampostería", n_slides=4
    )
    print(f"\n[3] obra_avance: {c3.n_slides} slides")
    placeholder = [s for s in c3.slides if s.tipo == "placeholder_foto"]
    if placeholder:
        print(f"    Placeholder foto: {placeholder[0].metadata['placeholder_foto_path']}")

    # 4) Servicios
    c4 = factory.servicios(empresa="Construcciones Rurales", municipio="Cañuelas", n_slides=6)
    print(f"\n[4] servicios: {c4.n_slides} slides")

    # Persistir el primero
    ruta = factory.guardar(c1, "lote_premium_cañuelas", proyecto="chacra-canuelas-5ha")
    print(f"\nGuardado en: {ruta.relative_to(ROOT)}")


if __name__ == "__main__":
    demo()
