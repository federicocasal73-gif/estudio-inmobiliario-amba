"""
Realestate Studio AMBA - orquestador de contenido inmobiliario para Instagram.

Especializado en lotes, chacras, campos, countries y servicios de construccion
en la Zona Metropolitana de Buenos Aires (Argentina).

Funciona con Fooocus local (cuando esta corriendo) o de forma independiente
como generador de prompts SDXL y copy rioplatense, valido para cualquier
generador de imagen (Midjourney, DALL-E, Flux, Leonardo).

Uso desde opencode:
    from realestate_studio import RealestateStudio
    studio = RealestateStudio()
    print(studio.lotes.chacra_pampeana(hectareas=5, municipio="Ca\u00f1uelas").prompt)
    print(studio.post.lote_venta(tema="5 ha en Ca\u00f1uelas", municipio="Ca\u00f1uelas",
                                  hectareas="5 hectareas", distancia_caba="65 km")["caption_completo"])
"""

from __future__ import annotations

import json
import os
import random
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
INMUEBLES_DIR = ROOT / "inmuebles"
LOTES_DIR = INMUEBLES_DIR / "lotes"
OBRAS_DIR = INMUEBLES_DIR / "obras"
SERVICIOS_DIR = INMUEBLES_DIR / "servicios"
INPUTS_DIR = INMUEBLES_DIR / "inputs"
OUTPUTS_DIR = INMUEBLES_DIR / "outputs"
POSTS_DIR = INMUEBLES_DIR / "posts"
PROMPTS_DB = ROOT / "prompts_inmobiliarios.json"
CAPTIONS_DB = ROOT / "captions_instagram.json"

FOOOCUS_DEFAULT_URL = os.environ.get("FOOOCUS_URL", "http://127.0.0.1:7865")
FOOOCUS_TIMEOUT = int(os.environ.get("FOOOCUS_TIMEOUT", "600"))

ASPECT_INSTAGRAM_POST = "896*1152"
ASPECT_INSTAGRAM_STORY = "768*1344"
ASPECT_INSTAGRAM_SQUARE = "1024*1024"
ASPECT_INSTAGRAM_LANDSCAPE = "1152*896"
ASPECT_INSTAGRAM_PORTRAIT = "1152*896"

# Aspectos por tipo de contenido rural
ASPECT_CHACRA = ASPECT_INSTAGRAM_LANDSCAPE
ASPECT_COUNTRY = ASPECT_INSTAGRAM_LANDSCAPE
ASPECT_VISTA_AEREA = ASPECT_INSTAGRAM_LANDSCAPE
ASPECT_REEL = ASPECT_INSTAGRAM_POST


@dataclass
class GenerationRequest:
    prompt: str
    negative_prompt: str = ""
    aspect_ratio: str = ASPECT_INSTAGRAM_POST
    styles: list[str] = field(default_factory=lambda: ["Fooocus V2", "Fooocus Enhance"])
    performance: str = "Speed"
    steps: int = 30
    cfg_scale: float = 4.0
    seed: int = -1
    imagen_salida: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {k: v for k, v in asdict(self).items() if v is not None}


class FooocusClient:
    """Cliente HTTP ligero para invocar Fooocus cuando esta corriendo."""

    def __init__(self, base_url: str = FOOOCUS_DEFAULT_URL, timeout: int = FOOOCUS_TIMEOUT):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def disponible(self) -> bool:
        try:
            req = urllib.request.Request(f"{self.base_url}/", method="GET")
            with urllib.request.urlopen(req, timeout=5):
                return True
        except (urllib.error.URLError, urllib.error.HTTPError, OSError):
            return False

    def payload_text_to_image(
        self,
        prompt: str,
        negativo: str = "",
        aspect: str = ASPECT_INSTAGRAM_POST,
        styles: list[str] | None = None,
        performance: str = "Speed",
        steps: int = 30,
    ) -> dict[str, Any]:
        """Payload listo para enviar a la cola de Gradio cuando Fooocus este activo."""
        return {
            "prompt": prompt,
            "negative_prompt": negativo,
            "aspect_ratio": aspect,
            "styles": styles or ["Fooocus V2", "Fooocus Enhance"],
            "performance_selection": performance,
            "steps": steps,
            "cfg_scale": 4.0,
            "sampler": "dpmpp_2m_sde_gpu",
            "scheduler": "karras",
            "sharpness": 2.0,
            "image_number": 1,
            "seed": random.randint(0, 2**31 - 1),
        }

    def guardar_payload(self, payload: dict[str, Any], nombre: str) -> Path:
        OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
        ruta = OUTPUTS_DIR / f"{nombre}.json"
        ruta.write_text(json.dumps(payload, indent=2, ensure_ascii=False))
        return ruta


class VerticalLotes:
    """Generador de prompts para venta de lotes, chacras, campos y countries en AMBA."""

    ESTILOS_FOTOS = ["Fooocus V2", "Fooocus Enhance", "ads-real estate"]
    ESTILOS_CINEMATIC = ["Fooocus V2", "Fooocus Enhance", "photo-cinematic"]
    ESTILOS_AEREAS = ["Fooocus V2", "Fooocus Enhance", "photo-cinematic"]

    def __init__(self, prompts_db: dict[str, Any]):
        self.db = prompts_db
        self.plantillas = prompts_db.get("plantillas_base", {})
        self.negativos = prompts_db.get("negativos_default", "")

    def _req(
        self,
        prompt: str,
        aspect: str,
        estilos: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> GenerationRequest:
        return GenerationRequest(
            prompt=prompt,
            negative_prompt=self.negativos,
            aspect_ratio=aspect,
            styles=estilos or self.ESTILOS_FOTOS,
            metadata=metadata or {},
        )

    def chacra_pampeana(
        self,
        hectareas: float | int = 5,
        municipio: str = "Ca\u00f1uelas",
        epoca: str = "verano pampeano",
        momento: str = "golden hour",
    ) -> GenerationRequest:
        """Vista de chacra tradicional pampeana con casa principal al fondo."""
        base = self.plantillas.get("chacra_pampeana", "")
        desc = (
            f"{hectareas} hectares pampas farm, traditional estancia house, {municipio}, Argentina"
        )
        prompt = f"{desc}, {epoca}, {momento}, {base}, real estate photography"
        return self._req(
            prompt,
            ASPECT_CHACRA,
            self.ESTILOS_CINEMATIC,
            {"tipo": "chacra", "hectareas": hectareas, "municipio": municipio},
        )

    def country_premium(
        self,
        nombre: str = "El Casco",
        amenities: str = "golf, club house, pileta, canchas de tenis",
        momento: str = "blue hour",
    ) -> GenerationRequest:
        """Entrada de country premium con amenities."""
        base = self.plantillas.get("country_premium", "")
        prompt = (
            f"{nombre} gated community entrance, {amenities}, "
            f"{momento}, {base}, Buenos Aires suburbs"
        )
        return self._req(
            prompt, ASPECT_COUNTRY, self.ESTILOS_CINEMATIC, {"tipo": "country", "nombre": nombre}
        )

    def lote_periurbano(
        self, metros_cuadrados: int = 1000, municipio: str = "Pilar"
    ) -> GenerationRequest:
        """Lote bald\u00edo periurbano listo para construir."""
        base = self.plantillas.get("lote_periurbano", "")
        prompt = (
            f"{metros_cuadrados} sqm suburban building lot in {municipio}, "
            f"Buenos Aires province, ready to build, {base}"
        )
        return self._req(
            prompt,
            ASPECT_INSTAGRAM_SQUARE,
            {"tipo": "lote_periurbano", "metros": metros_cuadrados, "municipio": municipio},
        )

    def vista_aerea_loteo(
        self, n_lotes: int = 24, municipio: str = "Ca\u00f1uelas"
    ) -> GenerationRequest:
        """Vista aerea con drone de un loteo en desarrollo."""
        base = self.plantillas.get("vista_aerea_loteo", "")
        prompt = (
            f"aerial drone view of {n_lotes} lot subdivision in {municipio}, "
            f"Buenos Aires province, {base}"
        )
        return self._req(
            prompt,
            ASPECT_VISTA_AEREA,
            self.ESTILOS_AEREAS,
            {"tipo": "aerea", "n_lotes": n_lotes, "municipio": municipio},
        )

    def loteo_en_desarrollo(
        self, etapa: str = "Etapa 2", municipio: str = "Escobar"
    ) -> GenerationRequest:
        """Foto de obra de loteo en ejecucion (movimiento de suelo)."""
        base = self.plantillas.get("loteo_en_desarrollo", "")
        prompt = (
            f"{etapa} real estate development in {municipio}, Buenos Aires province, "
            f"earthworks in progress, {base}"
        )
        return self._req(
            prompt,
            ASPECT_INSTAGRAM_LANDSCAPE,
            self.ESTILOS_FOTOS,
            {"tipo": "loteo_obra", "etapa": etapa, "municipio": municipio},
        )

    def campo_mediano(
        self, hectareas: int = 50, rubro: str = "ganadero mixto", municipio: str = "Brandsen"
    ) -> GenerationRequest:
        """Campo de hectareas medias para inversion productiva."""
        base = self.plantillas.get("campo_mediano", "")
        prompt = f"{hectareas} hectares {rubro} farm in {municipio}, Buenos Aires province, {base}"
        return self._req(
            prompt,
            ASPECT_VISTA_AEREA,
            self.ESTILOS_CINEMATIC,
            {"tipo": "campo", "hectareas": hectareas, "rubro": rubro, "municipio": municipio},
        )

    def campo_grande(
        self, hectareas: int = 300, rubro: str = "agricola-ganadero", municipio: str = "Saladillo"
    ) -> GenerationRequest:
        """Campo grande (300+ ha) para inversion seria."""
        base = self.plantillas.get("campo_grande", "")
        prompt = (
            f"{hectareas} hectares {rubro} farm in {municipio}, Buenos Aires province, "
            f"investment grade agricultural land, {base}"
        )
        return self._req(
            prompt,
            ASPECT_VISTA_AEREA,
            self.ESTILOS_CINEMATIC,
            {
                "tipo": "campo_grande",
                "hectareas": hectareas,
                "rubro": rubro,
                "municipio": municipio,
            },
        )

    def lote_inversion_chico(
        self, metros_cuadrados: int = 600, municipio: str = "Pilar"
    ) -> GenerationRequest:
        """Lote chico urbano-rural para primera inversion o vivienda."""
        base = self.plantillas.get("lote_inversion_chico", "")
        prompt = (
            f"{metros_cuadrados} sqm affordable building lot in {municipio}, "
            f"Buenos Aires province, {base}"
        )
        return self._req(
            prompt,
            ASPECT_INSTAGRAM_SQUARE,
            {"tipo": "lote_chico", "metros": metros_cuadrados, "municipio": municipio},
        )

    def pileta_quinta(self, hectareas: float = 2, municipio: str = "Escobar") -> GenerationRequest:
        """Quinta de fin de semana con pileta."""
        base = self.plantillas.get("pileta_quinta", "")
        prompt = (
            f"weekend quinta with pool on {hectareas} hectares in {municipio}, "
            f"Buenos Aires province, {base}"
        )
        return self._req(
            prompt,
            ASPECT_INSTAGRAM_LANDSCAPE,
            self.ESTILOS_CINEMATIC,
            {"tipo": "quinta", "hectareas": hectareas, "municipio": municipio},
        )

    def estancia_productiva(
        self, hectareas: int = 200, municipio: str = "San Antonio de Areco"
    ) -> GenerationRequest:
        """Estancia tradicional con operacion ganadera/agricola."""
        base = self.plantillas.get("estancia_productiva", "")
        prompt = (
            f"productive traditional estancia, {hectareas} hectares in {municipio}, "
            f"Buenos Aires province, {base}"
        )
        return self._req(
            prompt,
            ASPECT_VISTA_AEREA,
            self.ESTILOS_CINEMATIC,
            {"tipo": "estancia", "hectareas": hectareas, "municipio": municipio},
        )

    def emprendimiento_agroturistico(
        self, hectareas: int = 20, municipio: str = "Tandil"
    ) -> GenerationRequest:
        """Emprendimiento agroturistico (bodegas, lodges, cabalgatas)."""
        base = self.plantillas.get("emprendimiento_agroturistico", "")
        prompt = (
            f"agritourism estate, {hectareas} hectares in {municipio}, "
            f"Buenos Aires province, {base}"
        )
        return self._req(
            prompt,
            ASPECT_INSTAGRAM_LANDSCAPE,
            self.ESTILOS_CINEMATIC,
            {"tipo": "agroturismo", "hectareas": hectareas, "municipio": municipio},
        )

    def lote_comercial_ruta(
        self, metros_cuadrados: int = 2000, municipio: str = "Campana"
    ) -> GenerationRequest:
        """Lote comercial sobre ruta para inversion productiva."""
        base = self.plantillas.get("lote_comercial_ruta", "")
        prompt = (
            f"commercial lot {metros_cuadrados} sqm on highway in {municipio}, "
            f"Buenos Aires province, {base}"
        )
        return self._req(
            prompt,
            ASPECT_INSTAGRAM_LANDSCAPE,
            {"tipo": "lote_comercial", "metros": metros_cuadrados, "municipio": municipio},
        )

    def amanecer_pampa(self, municipio: str = "Luj\u00e1n") -> GenerationRequest:
        """Atmosfera: amanecer sobre la pampa con omb\u00fa solitario."""
        base = self.plantillas.get("amanecer_pampa", "")
        prompt = f"sunrise over pampas fields in {municipio}, Buenos Aires province, {base}"
        return self._req(
            prompt,
            ASPECT_VISTA_AEREA,
            self.ESTILOS_CINEMATIC,
            {"tipo": "amanecer", "municipio": municipio},
        )

    def atardecer_campo(
        self, hectareas: float | int = 5, municipio: str = "Mercedes"
    ) -> GenerationRequest:
        """Atmosfera: atardecer dramatico sobre campo con molino."""
        base = self.plantillas.get("atardecer_campo", "")
        prompt = (
            f"sunset over {hectareas} hectares field with classic windmill in {municipio}, "
            f"Buenos Aires province, {base}"
        )
        return self._req(
            prompt,
            ASPECT_VISTA_AEREA,
            self.ESTILOS_CINEMATIC,
            {"tipo": "atardecer", "hectareas": hectareas, "municipio": municipio},
        )

    def tranquera_argentina(self, municipio: str = "Ca\u00f1uelas") -> GenerationRequest:
        """Detalle: tranquera de madera tradicional con alambrado."""
        base = self.plantillas.get("tranquera_argentina", "")
        prompt = (
            f"rustic wooden gate entrance to farm in {municipio}, Buenos Aires province, {base}"
        )
        return self._req(
            prompt,
            ASPECT_INSTAGRAM_SQUARE,
            self.ESTILOS_FOTOS,
            {"tipo": "tranquera", "municipio": municipio},
        )

    def molino_tanque_australiano(self, municipio: str = "Roque P\u00e9rez") -> GenerationRequest:
        """Icono rural: molino y tanque australiano."""
        base = self.plantillas.get("molino_tanque", "")
        prompt = f"classic windmill and water tank in {municipio}, Buenos Aires province, {base}"
        return self._req(
            prompt,
            ASPECT_INSTAGRAM_SQUARE,
            self.ESTILOS_FOTOS,
            {"tipo": "molino", "municipio": municipio},
        )

    def casco_estancia(self, municipio: str = "San Antonio de Areco") -> GenerationRequest:
        """Casco de estancia tradicional argentina."""
        base = self.plantillas.get("casco_estancia", "")
        prompt = (
            f"traditional Argentine estancia main house in {municipio}, "
            f"Buenos Aires province, {base}"
        )
        return self._req(
            prompt,
            ASPECT_INSTAGRAM_LANDSCAPE,
            self.ESTILOS_CINEMATIC,
            {"tipo": "estancia", "municipio": municipio},
        )

    def variaciones(self, prompt_base: str, n: int = 4) -> list[GenerationRequest]:
        """Genera N variaciones de un mismo prompt con seeds distintos."""
        seeds = random.sample(range(2**31), n)
        return [
            GenerationRequest(
                prompt=prompt_base,
                seed=seed,
                aspect_ratio=ASPECT_REEL,
                metadata={"variacion": i + 1},
            )
            for i, seed in enumerate(seeds)
        ]


class VerticalConstruccion:
    """Generador de prompts para obras y servicios de construccion (fase 2)."""

    ESTILOS_FOTOS = ["Fooocus V2", "Fooocus Enhance", "ads-real estate"]
    ESTILOS_CINEMATIC = ["Fooocus V2", "Fooocus Enhance", "photo-cinematic"]

    def __init__(self, prompts_db: dict[str, Any]):
        self.db = prompts_db
        self.negativos = prompts_db.get("negativos_default", "")
        self.plantillas = prompts_db.get("plantillas_base", {})

    def _req(
        self,
        prompt: str,
        aspect: str,
        estilos: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> GenerationRequest:
        return GenerationRequest(
            prompt=prompt,
            negative_prompt=self.negativos,
            aspect_ratio=aspect,
            styles=estilos or self.ESTILOS_FOTOS,
            metadata=metadata or {},
        )

    def movimiento_suelo(
        self, maquinaria: str = "retroexcavadora Komatsu", municipio: str = "Pilar"
    ) -> GenerationRequest:
        """Foto de obra: movimiento de suelo con maquinaria pesada."""
        prompt = (
            f"{maquinaria} working on earthworks at construction site in {municipio}, "
            f"Buenos Aires province, Argentina, professional construction photography, "
            f"golden hour, dust, real estate development in progress"
        )
        return self._req(
            prompt,
            ASPECT_INSTAGRAM_LANDSCAPE,
            {"tipo": "movimiento_suelo", "maquinaria": maquinaria, "municipio": municipio},
        )

    def obra_gruesa(
        self, etapa: str = "hormig\u00f3n armado", municipio: str = "Escobar"
    ) -> GenerationRequest:
        """Foto de obra: etapa de obra gruesa."""
        prompt = (
            f"residential construction site in {etapa} stage, {municipio}, "
            f"Buenos Aires province, concrete structure, brick walls rising, "
            f"professional construction photography, daylight"
        )
        return self._req(
            prompt,
            ASPECT_INSTAGRAM_SQUARE,
            {"tipo": "obra_gruesa", "etapa": etapa, "municipio": municipio},
        )

    def steel_framing(self, municipio: str = "Ca\u00f1uelas") -> GenerationRequest:
        """Foto de obra: construccion en seco con steel frame."""
        prompt = (
            f"steel frame house construction in {municipio}, Buenos Aires province, "
            f"metal structure, panels being installed, professional construction photography"
        )
        return self._req(
            prompt, ASPECT_INSTAGRAM_SQUARE, {"tipo": "steel_frame", "municipio": municipio}
        )

    def render_proyecto(
        self,
        estilo: str = "casa de campo tradicional",
        hectareas: float = 5,
        municipio: str = "Cañuelas",
    ) -> GenerationRequest:
        """Render arquitectonico de casa proyectada sobre chacra."""
        prompt = (
            f"architectural rendering of {estilo} on {hectareas} hectares pampas lot "
            f"in {municipio}, Buenos Aires province, photorealistic visualization, "
            f"golden hour, dramatic sky"
        )
        return self._req(
            prompt,
            ASPECT_INSTAGRAM_LANDSCAPE,
            estilos=self.ESTILOS_FOTOS + ["misc-architectural"],
            metadata={
                "tipo": "render_proyecto",
                "estilo": estilo,
                "hectareas": hectareas,
                "municipio": municipio,
            },
        )

    # ============== PRE-CONSTRUCCION ==============

    def anteproyecto_arquitectonico(
        self, estilo: str = "minimalista moderno", municipio: str = "Cañuelas"
    ) -> GenerationRequest:
        """Antaproyecto: planos y renders arquitectonicos."""
        base = self.plantillas.get("anteproyecto_arquitectonico", "")
        prompt = (
            f"architectural design phase, {estilo} country house for {municipio}, "
            f"Buenos Aires province, blueprints and 3d renders on architect desk, "
            f"{base}"
        )
        return self._req(
            prompt,
            ASPECT_INSTAGRAM_LANDSCAPE,
            self.ESTILOS_CINEMATIC,
            {"tipo": "anteproyecto", "estilo": estilo, "municipio": municipio},
        )

    def render_exterior_casa(
        self, estilo: str = "moderna minimalista", municipio: str = "Cañuelas"
    ) -> GenerationRequest:
        """Render exterior fotorrealista de una casa."""
        base = self.plantillas.get("render_exterior_casa", "")
        prompt = (
            f"photorealistic exterior render, {estilo} country house, "
            f"{municipio}, Buenos Aires province, {base}"
        )
        return self._req(
            prompt,
            ASPECT_INSTAGRAM_LANDSCAPE,
            estilos=self.ESTILOS_FOTOS + ["misc-architectural"],
            metadata={"tipo": "render_exterior", "estilo": estilo, "municipio": municipio},
        )

    def render_interior_casa(
        self, ambiente: str = "living", municipio: str = "Cañuelas"
    ) -> GenerationRequest:
        """Render interior fotorrealista de un ambiente."""
        base = self.plantillas.get("render_interior_casa", "")
        prompt = (
            f"photorealistic interior render of {ambiente} in modern country house, "
            f"{municipio}, Buenos Aires province, {base}"
        )
        return self._req(
            prompt,
            ASPECT_INSTAGRAM_SQUARE,
            estilos=self.ESTILOS_FOTOS + ["misc-architectural"],
            metadata={"tipo": "render_interior", "ambiente": ambiente, "municipio": municipio},
        )

    def estudio_de_suelo(self, municipio: str = "Cañuelas") -> GenerationRequest:
        """Estudio geotécnico / muestreo de suelo."""
        base = self.plantillas.get("estudio_de_suelo", "")
        prompt = (
            f"soil study and geotechnical sampling at construction site in {municipio}, "
            f"Buenos Aires province, {base}"
        )
        return self._req(
            prompt,
            ASPECT_INSTAGRAM_LANDSCAPE,
            self.ESTILOS_FOTOS,
            {"tipo": "estudio_suelo", "municipio": municipio},
        )

    def relevamiento_topografico(self, municipio: str = "Cañuelas") -> GenerationRequest:
        """Relevamiento topografico con teodolito."""
        base = self.plantillas.get("relevamiento_topografico", "")
        prompt = (
            f"topographic land survey with theodolite at rural construction site in "
            f"{municipio}, Buenos Aires province, {base}"
        )
        return self._req(
            prompt,
            ASPECT_INSTAGRAM_LANDSCAPE,
            self.ESTILOS_FOTOS,
            {"tipo": "relevamiento", "municipio": municipio},
        )

    # ============== OBRA GRUESA ==============

    def replanteo_obra(self, municipio: str = "Cañuelas") -> GenerationRequest:
        """Replanteo: marcacion de ejes y limites en el terreno."""
        base = self.plantillas.get("replanteo_obra", "")
        prompt = (
            f"construction site survey and staking with stakes and string lines in "
            f"{municipio}, Buenos Aires province, {base}"
        )
        return self._req(
            prompt,
            ASPECT_INSTAGRAM_LANDSCAPE,
            self.ESTILOS_FOTOS,
            {"tipo": "replanteo", "municipio": municipio},
        )

    def excavacion_fundaciones(
        self, maquinaria: str = "retroexcavadora", municipio: str = "Cañuelas"
    ) -> GenerationRequest:
        """Excavacion de zanjas para fundaciones."""
        base = self.plantillas.get("excavacion_fundaciones", "")
        prompt = (
            f"foundation trench excavation with {maquinaria} at suburban construction "
            f"site in {municipio}, Buenos Aires province, {base}"
        )
        return self._req(
            prompt,
            ASPECT_INSTAGRAM_LANDSCAPE,
            self.ESTILOS_FOTOS,
            {"tipo": "excavacion", "maquinaria": maquinaria, "municipio": municipio},
        )

    def fundaciones_hormigon(self, municipio: str = "Cañuelas") -> GenerationRequest:
        """Hormigonado de fundaciones con armadura."""
        base = self.plantillas.get("fundaciones_hormigon", "")
        prompt = (
            f"concrete foundation being poured with rebar at construction site in "
            f"{municipio}, Buenos Aires province, {base}"
        )
        return self._req(
            prompt,
            ASPECT_INSTAGRAM_SQUARE,
            self.ESTILOS_FOTOS,
            {"tipo": "fundaciones", "municipio": municipio},
        )

    def estructura_hormigon(self, municipio: str = "Cañuelas") -> GenerationRequest:
        """Estructura de hormigon armado en construccion."""
        base = self.plantillas.get("estructura_hormigon", "")
        prompt = (
            f"reinforced concrete structure rising, columns and beams with formwork at "
            f"construction site in {municipio}, Buenos Aires province, {base}"
        )
        return self._req(
            prompt,
            ASPECT_INSTAGRAM_LANDSCAPE,
            self.ESTILOS_FOTOS,
            {"tipo": "estructura", "municipio": municipio},
        )

    def mamposteria_ladrillo(self, municipio: str = "Cañuelas") -> GenerationRequest:
        """Albañil levantando pared de ladrillo."""
        base = self.plantillas.get("mamposteria_ladrillo", "")
        prompt = (
            f"bricklayer laying bricks on rising exterior wall at construction site in "
            f"{municipio}, Buenos Aires province, {base}"
        )
        return self._req(
            prompt,
            ASPECT_INSTAGRAM_SQUARE,
            self.ESTILOS_FOTOS,
            {"tipo": "mamposteria", "municipio": municipio},
        )

    def cubierta_techo(
        self, tipo_techo: str = "chapa", municipio: str = "Cañuelas"
    ) -> GenerationRequest:
        """Construccion del techo/cubierta."""
        base = self.plantillas.get("cubierta_techo", "")
        prompt = (
            f"roof construction in progress with {tipo_techo} covering at suburban "
            f"construction site in {municipio}, Buenos Aires province, {base}"
        )
        return self._req(
            prompt,
            ASPECT_INSTAGRAM_LANDSCAPE,
            self.ESTILOS_FOTOS,
            {"tipo": "cubierta", "material": tipo_techo, "municipio": municipio},
        )

    # ============== STEEL FRAME ==============

    def steel_frame_estructura(self, municipio: str = "Cañuelas") -> GenerationRequest:
        """Estructura de steel frame en montaje."""
        base = self.plantillas.get("steel_frame_estructura", "")
        prompt = (
            f"steel frame house under construction with galvanized steel structure "
            f"rising at {municipio}, Buenos Aires province, {base}"
        )
        return self._req(
            prompt,
            ASPECT_INSTAGRAM_LANDSCAPE,
            self.ESTILOS_FOTOS,
            {"tipo": "steel_frame_estructura", "municipio": municipio},
        )

    def steel_frame_cerramiento(self, municipio: str = "Cañuelas") -> GenerationRequest:
        """Steel frame con cerramiento exterior (placas cementicias)."""
        base = self.plantillas.get("steel_frame_cerramiento", "")
        prompt = (
            f"steel frame house with exterior cement board panels being installed at "
            f"{municipio}, Buenos Aires province, {base}"
        )
        return self._req(
            prompt,
            ASPECT_INSTAGRAM_SQUARE,
            self.ESTILOS_FOTOS,
            {"tipo": "steel_frame_cerramiento", "municipio": municipio},
        )

    # ============== TERMINACIONES ==============

    def revoque_grueso(self, municipio: str = "Cañuelas") -> GenerationRequest:
        """Aplicacion de revoque grueso interior."""
        base = self.plantillas.get("revoque_grueso", "")
        prompt = (
            f"construction worker applying rough plaster to interior walls at {municipio}, "
            f"Buenos Aires province, {base}"
        )
        return self._req(
            prompt,
            ASPECT_INSTAGRAM_SQUARE,
            self.ESTILOS_FOTOS,
            {"tipo": "revoque_grueso", "municipio": municipio},
        )

    def colocacion_aberturas(
        self, tipo: str = "aluminio DVH", municipio: str = "Cañuelas"
    ) -> GenerationRequest:
        """Colocacion de aberturas (ventanas/puertas)."""
        base = self.plantillas.get("colocacion_aberturas", "")
        prompt = (
            f"{tipo} window frame installation at construction site in {municipio}, "
            f"Buenos Aires province, {base}"
        )
        return self._req(
            prompt,
            ASPECT_INSTAGRAM_SQUARE,
            self.ESTILOS_FOTOS,
            {"tipo": "aberturas", "material": tipo, "municipio": municipio},
        )

    def colocacion_pisos(
        self, tipo_piso: str = "porcelanato", municipio: str = "Cañuelas"
    ) -> GenerationRequest:
        """Colocacion de pisos."""
        base = self.plantillas.get("colocacion_pisos", "")
        prompt = (
            f"{tipo_piso} floor tiles being installed at construction site in "
            f"{municipio}, Buenos Aires province, {base}"
        )
        return self._req(
            prompt,
            ASPECT_INSTAGRAM_SQUARE,
            self.ESTILOS_FOTOS,
            {"tipo": "pisos", "material": tipo_piso, "municipio": municipio},
        )

    def pintura_interior(self, municipio: str = "Cañuelas") -> GenerationRequest:
        """Pintura interior con rodillo."""
        base = self.plantillas.get("pintura_interior", "")
        prompt = (
            f"interior painter applying white paint to wall with roller at modern house "
            f"under construction in {municipio}, Buenos Aires province, {base}"
        )
        return self._req(
            prompt,
            ASPECT_INSTAGRAM_SQUARE,
            self.ESTILOS_FOTOS,
            {"tipo": "pintura", "municipio": municipio},
        )

    # ============== ENTREGA Y DETALLES ==============

    def casa_terminada_frente(
        self, estilo: str = "minimalista moderno", municipio: str = "Cañuelas"
    ) -> GenerationRequest:
        """Casa terminada vista del frente."""
        base = self.plantillas.get("casa_terminada_frente", "")
        prompt = (
            f"newly completed country house front view, {estilo} style, manicured garden "
            f"in {municipio}, Buenos Aires province, {base}"
        )
        return self._req(
            prompt,
            ASPECT_INSTAGRAM_LANDSCAPE,
            estilos=self.ESTILOS_FOTOS + ["ads-luxury"],
            metadata={"tipo": "casa_terminada", "estilo": estilo, "municipio": municipio},
        )

    def entrega_llaves(self, municipio: str = "Cañuelas") -> GenerationRequest:
        """Momento de entrega de llaves al cliente."""
        base = self.plantillas.get("entrega_llaves", "")
        prompt = (
            f"homeowner couple receiving keys to their new country house, doorway "
            f"of new construction in {municipio}, Buenos Aires province, {base}"
        )
        return self._req(
            prompt,
            ASPECT_INSTAGRAM_LANDSCAPE,
            self.ESTILOS_CINEMATIC,
            {"tipo": "entrega_llaves", "municipio": municipio},
        )

    def fachada_moderna_minimalista(self, municipio: str = "Cañuelas") -> GenerationRequest:
        """Fachada moderna minimalista (render o foto)."""
        base = self.plantillas.get("fachada_moderna_minimalista", "")
        prompt = (
            f"modern minimalist house facade with large glass windows in {municipio}, "
            f"Buenos Aires province, {base}"
        )
        return self._req(
            prompt,
            ASPECT_INSTAGRAM_LANDSCAPE,
            estilos=self.ESTILOS_FOTOS + ["ads-luxury"],
            metadata={"tipo": "fachada_moderna", "municipio": municipio},
        )

    def detalle_madera_arquitectonico(self, municipio: str = "Cañuelas") -> GenerationRequest:
        """Detalle arquitectonico de madera + concreto."""
        base = self.plantillas.get("detalle_madera_arquitectonico", "")
        prompt = (
            f"architectural detail closeup, wooden beams meeting concrete in modern "
            f"rustic construction in {municipio}, Buenos Aires province, {base}"
        )
        return self._req(
            prompt,
            ASPECT_INSTAGRAM_SQUARE,
            self.ESTILOS_FOTOS,
            {"tipo": "detalle_arquitectonico", "municipio": municipio},
        )

    # ============== MAQUINARIA ==============

    def equipo_pesado_construccion(
        self, maquinaria: str = "excavadora CAT", municipio: str = "Cañuelas"
    ) -> GenerationRequest:
        """Equipo pesado en obra."""
        base = self.plantillas.get("equipo_pesado_construccion", "")
        prompt = (
            f"{maquinaria} heavy construction equipment at suburban building site in "
            f"{municipio}, Buenos Aires province, {base}"
        )
        return self._req(
            prompt,
            ASPECT_INSTAGRAM_LANDSCAPE,
            self.ESTILOS_FOTOS,
            {"tipo": "equipo_pesado", "maquinaria": maquinaria, "municipio": municipio},
        )

    def grua_obra(self, municipio: str = "Cañuelas") -> GenerationRequest:
        """Grua torre en obra."""
        base = self.plantillas.get("grua_obra", "")
        prompt = (
            f"tower crane at construction site lifting materials in {municipio}, "
            f"Buenos Aires province, {base}"
        )
        return self._req(
            prompt,
            ASPECT_INSTAGRAM_LANDSCAPE,
            self.ESTILOS_FOTOS,
            {"tipo": "grua", "municipio": municipio},
        )

    def motoniveladora(self, municipio: str = "Cañuelas") -> GenerationRequest:
        """Motoniveladora nivelando camino."""
        base = self.plantillas.get("motoniveladora", "")
        prompt = (
            f"motor grader leveling dirt road at rural construction site in {municipio}, "
            f"Buenos Aires province, {base}"
        )
        return self._req(
            prompt,
            ASPECT_INSTAGRAM_LANDSCAPE,
            self.ESTILOS_FOTOS,
            {"tipo": "motoniveladora", "municipio": municipio},
        )

    def equipo_humano_obra(
        self, n_personas: int = 8, municipio: str = "Cañuelas"
    ) -> GenerationRequest:
        """Equipo humano de obra."""
        base = self.plantillas.get("equipo_humano_obra", "")
        prompt = (
            f"construction team of {n_personas} workers posing at construction site in "
            f"{municipio}, Buenos Aires province, helmets and safety vests, {base}"
        )
        return self._req(
            prompt,
            ASPECT_INSTAGRAM_LANDSCAPE,
            self.ESTILOS_FOTOS,
            {"tipo": "equipo_humano", "n_personas": n_personas, "municipio": municipio},
        )


class CaptionFactory:
    """Generador de captions rioplatenses y hashtags zonales para Instagram."""

    def __init__(self, captions_db: dict[str, Any]):
        self.db = captions_db

    @staticmethod
    def _slug_municipio(municipio: str) -> str:
        """Elimina acentos y espacios para hashtags."""
        import unicodedata

        texto = unicodedata.normalize("NFD", municipio)
        texto = "".join(c for c in texto if unicodedata.category(c) != "Mn")
        return texto.lower().replace(" ", "").replace("\u00a0", "")

    def caption(self, tipo: str, tono: str, **kwargs) -> str:
        """Devuelve el caption formateado segun tipo + tono + variables."""
        plantillas = self.db["plantillas"].get(tipo, [])
        candidatos = [p for p in plantillas if p.get("tono") == tono] or plantillas
        if not candidatos:
            return f"\ud83c\udfe1 {kwargs.get('tema', '')}"
        plantilla = random.choice(candidatos)["texto"]
        try:
            return plantilla.format(**kwargs)
        except KeyError:
            return plantilla

    def hashtags(
        self,
        nichos: list[str] | None = None,
        municipio: str | None = None,
        n: int = 20,
        blacklist: list[str] | None = None,
        must_include: list[str] | None = None,
    ) -> list[str]:
        """Devuelve hashtags mezclados por nicho + municipio.

        blacklist: hashtags a excluir (ej: ['#inversion'])
        must_include: hashtags que DEBEN estar en el resultado
        """
        nichos = nichos or ["general"]
        blacklist = [h.lower().lstrip("#") for h in (blacklist or [])]
        must_include = [h if h.startswith("#") else f"#{h}" for h in (must_include or [])]

        pool: list[str] = []
        for nicho in nichos:
            pool.extend(self.db["hashtags_por_nicho"].get(nicho, []))
        if municipio:
            slug = self._slug_municipio(municipio)
            for plantilla in self.db.get("hashtags_zona_template", []):
                pool.append(plantilla.format(municipio_sin_espacios=slug))

        # Filtrar blacklist
        if blacklist:
            pool = [h for h in pool if h.lstrip("#").lower() not in blacklist]

        # Asegurar must_include
        for h in must_include:
            if h not in pool:
                pool.append(h)

        random.shuffle(pool)
        # Si must_include quedo fuera por el shuffle, los reinsertamos al inicio
        resultado = list(pool[:n])
        for h in must_include:
            if h not in resultado:
                resultado.insert(0, h)
        return resultado[:n]

    def post_lote_venta(
        self,
        tema: str,
        municipio: str,
        hectareas: str = "5 hectareas",
        distancia_caba: str = "65 km",
        servicios_disponibles: str = "luz eléctrica, alambrado perimetral, calle de tierra mejorada",
        tono: str = "emotivo",
        unidades_disponibles: str = "1",
        nichos: list[str] | None = None,
    ) -> dict[str, Any]:
        nichos = nichos or ["general", "campo", "inversion"]
        caption_text = self.caption(
            "lote_venta",
            tono,
            tema=tema,
            municipio=municipio,
            hectareas=hectareas,
            distancia_caba=distancia_caba,
            servicios_disponibles=servicios_disponibles,
            unidades_disponibles=unidades_disponibles,
        )
        hashtags = self.hashtags(nichos, municipio)
        return self._armar_post(tema, "lote_venta", municipio, tono, caption_text, hashtags)

    def post_country(
        self,
        nombre_country: str,
        municipio: str,
        metros_cuadrados: int = 1000,
        orientacion: str = "norte",
        amenities_lista: str = "Club house, pileta, canchas de tenis, golf",
        unidades_disponibles: str = "3",
        precio_desde: str = "85.000",
        cuotas: str = "24",
        fecha_entrega: str = "diciembre 2026",
        etapa: str = "1",
        distancia_caba: str = "45 km",
        tono: str = "premium",
    ) -> dict[str, Any]:
        caption_text = self.caption(
            "country",
            tono,
            nombre_country=nombre_country,
            metros_cuadrados=metros_cuadrados,
            orientacion=orientacion,
            amenities_lista=amenities_lista,
            unidades_disponibles=unidades_disponibles,
            distancia_caba=distancia_caba,
            etapa=etapa,
            precio_desde=precio_desde,
            cuotas=cuotas,
            fecha_entrega=fecha_entrega,
        )
        hashtags = self.hashtags(["country", "inversion"], municipio)
        tema = f"Lote en {nombre_country}"
        return self._armar_post(tema, "country", municipio, tono, caption_text, hashtags)

    def post_campo(
        self,
        hectareas: str,
        municipio: str,
        rubro: str = "ganadero mixto",
        aptitud: str = "agr\u00edcola-ganadera",
        precio_usd: str = "8.500",
        distancia_caba: str = "120 km",
        tono: str = "inversion",
    ) -> dict[str, Any]:
        caption_text = self.caption(
            "campo",
            tono,
            hectareas=hectareas,
            municipio=municipio,
            rubro=rubro,
            aptitud=aptitud,
            precio_usd=precio_usd,
            distancia_caba=distancia_caba,
        )
        hashtags = self.hashtags(["campo", "inversion"], municipio)
        tema = f"{hectareas} en {municipio}"
        return self._armar_post(tema, "campo", municipio, tono, caption_text, hashtags)

    def post_preventa(
        self,
        nombre_loteo: str,
        municipio: str,
        etapa: str = "2",
        metros_cuadrados: int = 1000,
        precio_lanzamiento: str = "45.000",
        precio_postentrega: str = "62.000",
        senia: str = "5.000",
        unidades_disponibles: int = 6,
        tono: str = "oportunidad",
    ) -> dict[str, Any]:
        caption_text = self.caption(
            "preventa_loteo",
            tono,
            etapa=etapa,
            nombre_loteo=nombre_loteo,
            municipio=municipio,
            metros_cuadrados=metros_cuadrados,
            precio_lanzamiento=precio_lanzamiento,
            precio_postentrega=precio_postentrega,
            seña=senia,
            unidades_disponibles=unidades_disponibles,
        )
        hashtags = self.hashtags(["general", "inversion"], municipio)
        tema = f"Pre-venta {nombre_loteo}"
        return self._armar_post(tema, "preventa_loteo", municipio, tono, caption_text, hashtags)

    def post_lote_periurbano(
        self,
        municipio: str,
        metros_cuadrados: int = 1000,
        metros_asfalto: int = 200,
        tono: str = "practico",
    ) -> dict[str, Any]:
        caption_text = self.caption(
            "lote_periurbano",
            tono,
            municipio=municipio,
            metros_cuadrados=metros_cuadrados,
            metros_asfalto=metros_asfalto,
        )
        hashtags = self.hashtags(["general"], municipio)
        tema = f"Terreno en {municipio}"
        return self._armar_post(tema, "lote_periurbano", municipio, tono, caption_text, hashtags)

    def post_testimonial_cliente(
        self,
        cliente: str,
        historia: str,
        resultado: str,
        tema: str = "casa en el campo",
        tiempo: str = "8 meses",
        tono: str = "emotivo",
        nichos: list[str] | None = None,
    ) -> dict[str, Any]:
        nichos = nichos or ["casas", "construccion", "general"]
        caption_text = self.caption(
            "testimonial_cliente",
            tono,
            cliente=cliente,
            historia=historia,
            resultado=resultado,
            tema=tema,
            tiempo=tiempo,
        )
        hashtags = self.hashtags(nichos)
        return self._armar_post(
            f"Testimonio {cliente}", "testimonial_cliente", "", tono, caption_text, hashtags
        )

    def post_preguntas_frecuentes(
        self,
        tema: str,
        preguntas_respuestas: list[tuple[str, str]],
        tono: str = "practico",
        nichos: list[str] | None = None,
    ) -> dict[str, Any]:
        """Recibe lista de tuplas (pregunta, respuesta) hasta 5."""
        nichos = nichos or ["general"]
        if not 1 <= len(preguntas_respuestas) <= 5:
            raise ValueError("Debe haber entre 1 y 5 preguntas")
        kwargs = {"tema": tema}
        for i, (preg, resp) in enumerate(preguntas_respuestas, 1):
            kwargs[f"pregunta_{i}"] = preg
            kwargs[f"respuesta_{i}"] = resp
        # Rellenar las que falten
        for i in range(len(preguntas_respuestas) + 1, 6):
            kwargs[f"pregunta_{i}"] = ""
            kwargs[f"respuesta_{i}"] = ""
        caption_text = self.caption("preguntas_frecuentes", tono, **kwargs)
        hashtags = self.hashtags(nichos)
        return self._armar_post(
            f"FAQ: {tema}", "preguntas_frecuentes", "", tono, caption_text, hashtags
        )

    def post_obra_avance_semanal(
        self,
        semana: int,
        municipio: str,
        etapa: str,
        avance: int,
        tareas: list[str],
        proxima_etapa: str,
        tono: str = "practico",
        nichos: list[str] | None = None,
    ) -> dict[str, Any]:
        nichos = nichos or ["construccion", "casas"]
        tareas = (tareas + ["", "", ""])[:3]
        caption_text = self.caption(
            "obra_avance_semanal",
            tono,
            semana=semana,
            municipio=municipio,
            etapa=etapa,
            avance=avance,
            tarea_1=tareas[0],
            tarea_2=tareas[1],
            tarea_3=tareas[2],
            proxima_etapa=proxima_etapa,
        )
        hashtags = self.hashtags(nichos, municipio)
        return self._armar_post(
            f"Obra semana {semana} - {municipio}",
            "obra_avance_semanal",
            municipio,
            tono,
            caption_text,
            hashtags,
        )

    def post_reel_hook(self, tema: str, tono: str = "emotivo") -> dict[str, Any]:
        """Caption corto para reel (1-2 lineas)."""
        caption_text = self.caption("reel_hook_corto", tono, tema=tema)
        hashtags = self.hashtags(["general"], "")
        return self._armar_post(
            f"Reel: {tema}", "reel_hook_corto", "", tono, caption_text, hashtags
        )

    # ============== POSTS DE CONSTRUCCION ==============

    def post_presupuesto_obra(
        self,
        zona: str = "Cañuelas",
        metros_cuadrados: int = 120,
        obra_gruesa: str = "650",
        instalaciones: str = "180",
        terminaciones: str = "350",
        llave_en_mano: str = "1300",
        rango_min: str = "95.000",
        rango_max: str = "180.000",
        porcentaje_materiales: str = "45",
        porcentaje_mano_obra: str = "30",
        porcentaje_maquinaria: str = "10",
        porcentaje_honorarios: str = "10",
        porcentaje_otros: str = "5",
        tono: str = "practico",
    ) -> dict[str, Any]:
        """Post sobre presupuesto / cuanto cuesta construir."""
        caption_text = self.caption(
            "presupuesto_obra",
            tono,
            zona=zona,
            metros_cuadrados=metros_cuadrados,
            obra_gruesa=obra_gruesa,
            instalaciones=instalaciones,
            terminaciones=terminaciones,
            llave_en_mano=llave_en_mano,
            rango_min=rango_min,
            rango_max=rango_max,
            porcentaje_materiales=porcentaje_materiales,
            porcentaje_mano_obra=porcentaje_mano_obra,
            porcentaje_maquinaria=porcentaje_maquinaria,
            porcentaje_honorarios=porcentaje_honorarios,
            porcentaje_otros=porcentaje_otros,
        )
        hashtags = self.hashtags(["construccion", "arquitectura", "general"], zona)
        return self._armar_post(
            f"Presupuesto en {zona}", "presupuesto_obra", zona, tono, caption_text, hashtags
        )

    def post_etapas_obra(
        self,
        metros_cuadrados: int = 120,
        n_etapas: int = 8,
        etapa_1: str = "Replanteo y movimiento de suelo",
        etapa_2: str = "Fundaciones",
        etapa_3: str = "Estructura y columnas",
        etapa_4: str = "Mampostería",
        etapa_5: str = "Losa y techo",
        etapa_6: str = "Instalaciones",
        etapa_7: str = "Revoques y terminaciones",
        etapa_8: str = "Aberturas, pisos y pintura",
        plazo_total: str = "8",
        tono: str = "educativo",
    ) -> dict[str, Any]:
        """Post sobre las 8 etapas de una obra."""
        caption_text = self.caption(
            "etapas_obra",
            tono,
            metros_cuadrados=metros_cuadrados,
            n_etapas=n_etapas,
            etapa_1=etapa_1,
            etapa_2=etapa_2,
            etapa_3=etapa_3,
            etapa_4=etapa_4,
            etapa_5=etapa_5,
            etapa_6=etapa_6,
            etapa_7=etapa_7,
            etapa_8=etapa_8,
            plazo_total=plazo_total,
        )
        hashtags = self.hashtags(["construccion", "ingenieria"])
        return self._armar_post(
            "Etapas de una obra", "etapas_obra", "", tono, caption_text, hashtags
        )

    def post_steel_frame_vs_tradicional(self, tono: str = "educativo") -> dict[str, Any]:
        """Comparativa steel frame vs construccion tradicional."""
        caption_text = self.caption("steel_frame_vs_tradicional", tono)
        hashtags = self.hashtags(["construccion", "casas", "general"])
        return self._armar_post(
            "Steel Frame vs Tradicional",
            "steel_frame_vs_tradicional",
            "",
            tono,
            caption_text,
            hashtags,
        )

    def post_planos_render(
        self,
        meses: int = 8,
        metros_cuadrados: int = 120,
        estilo: str = "moderna minimalista",
        tono: str = "aspiracional",
    ) -> dict[str, Any]:
        """Mockup planos vs realidad."""
        caption_text = self.caption("planos_render", tono, meses=meses)
        hashtags = self.hashtags(["arquitectura", "casas"])
        return self._armar_post(
            f"Planos vs Realidad ({estilo})", "planos_render", "", tono, caption_text, hashtags
        )

    def post_aberturas_instalaciones(
        self,
        puntos_electricos: int = 35,
        puntos_sanitarios: int = 8,
        tipo_termotanque: str = "solar",
        tono: str = "educativo",
    ) -> dict[str, Any]:
        """Detalles tecnicos de instalaciones."""
        caption_text = self.caption(
            "aberturas_instalaciones",
            tono,
            puntos_electricos=puntos_electricos,
            puntos_sanitarios=puntos_sanitarios,
            tipo_termotanque=tipo_termotanque,
        )
        hashtags = self.hashtags(["construccion", "ingenieria"])
        return self._armar_post(
            "Instalaciones y aberturas", "aberturas_instalaciones", "", tono, caption_text, hashtags
        )

    def post_pisos_revestimientos(
        self,
        opcion_1: str = "Porcelanato",
        costo_1: str = "USD 35",
        opcion_2: str = "Vinílico SPC",
        costo_2: str = "USD 22",
        opcion_3: str = "Madera engineered",
        costo_3: str = "USD 50",
        tono: str = "aspiracional",
    ) -> dict[str, Any]:
        """Comparativa de pisos y revestimientos."""
        caption_text = self.caption(
            "pisos_revestimientos",
            tono,
            opcion_1=opcion_1,
            costo_1=costo_1,
            opcion_2=opcion_2,
            costo_2=costo_2,
            opcion_3=opcion_3,
            costo_3=costo_3,
        )
        hashtags = self.hashtags(["decoracion", "diseno_interior", "casas"])
        return self._armar_post(
            "Pisos y revestimientos", "pisos_revestimientos", "", tono, caption_text, hashtags
        )

    def post_obra_terminada_entrega(
        self,
        cliente: str = "Familia Pérez",
        meses: int = 9,
        metros_cuadrados: int = 130,
        tiempo_total: str = "9 meses",
        nombre_obra: str = "Casa Pérez",
        etapa_cumplida: str = "Entrega de llaves",
        tono: str = "emotivo",
    ) -> dict[str, Any]:
        """Hito de entrega de obra."""
        caption_text = self.caption(
            "obra_terminada_entrega",
            tono,
            cliente=cliente,
            meses=meses,
            metros_cuadrados=metros_cuadrados,
            tiempo_total=tiempo_total,
            nombre_obra=nombre_obra,
            etapa_cumplida=etapa_cumplida,
        )
        hashtags = self.hashtags(["construccion", "casas", "general"])
        return self._armar_post(
            f"Entrega {nombre_obra}", "obra_terminada_entrega", "", tono, caption_text, hashtags
        )

    def post_plazo_construccion(
        self,
        metros_cuadrados: int = 120,
        plantas: int = 1,
        plazo_tradicional: str = "9-12",
        plazo_steel_frame: str = "6-8",
        plazo_llave: str = "10-14",
        tono: str = "practico",
    ) -> dict[str, Any]:
        """Tiempos de construccion."""
        caption_text = self.caption(
            "plazo_construccion",
            tono,
            metros_cuadrados=metros_cuadrados,
            plantas=plantas,
            plazo_tradicional=plazo_tradicional,
            plazo_steel_frame=plazo_steel_frame,
            plazo_llave=plazo_llave,
        )
        hashtags = self.hashtags(["construccion", "casas"])
        return self._armar_post(
            "Plazos de construcción", "plazo_construccion", "", tono, caption_text, hashtags
        )

    def post_garantia_postventa(self, tono: str = "profesional") -> dict[str, Any]:
        """Cobertura de garantia postventa."""
        caption_text = self.caption("garantia_postventa", tono)
        hashtags = self.hashtags(["construccion", "casas"])
        return self._armar_post(
            "Garantía postventa", "garantia_postventa", "", tono, caption_text, hashtags
        )

    def post_materiales_premium(
        self,
        tipo_ladrillo: str = "portante 18x18x33",
        tipo_cable: str = "antiinflamable LSZH",
        tipo_cañeria: str = "PPR termo-fusion",
        tono: str = "aspiracional",
    ) -> dict[str, Any]:
        """Comparativa de materiales premium vs economicos."""
        caption_text = self.caption(
            "materiales_premium",
            tono,
            tipo_ladrillo=tipo_ladrillo,
            tipo_cable=tipo_cable,
            tipo_cañeria=tipo_cañeria,
        )
        hashtags = self.hashtags(["construccion", "ingenieria"])
        return self._armar_post(
            "Materiales premium", "materiales_premium", "", tono, caption_text, hashtags
        )

    def post_errores_comunes_construccion(self, tono: str = "educativo") -> dict[str, Any]:
        """Errores frecuentes al construir."""
        caption_text = self.caption("errores_comunes_construccion", tono)
        hashtags = self.hashtags(["construccion", "casas"])
        return self._armar_post(
            "Errores comunes", "errores_comunes_construccion", "", tono, caption_text, hashtags
        )

    def post_equipo_trabajo_maquinaria(
        self,
        zona: str = "Cañuelas",
        n_excavadoras: int = 2,
        marca: str = "Komatsu",
        n_bulldozers: int = 1,
        n_camiones: int = 3,
        n_hormigoneras: int = 1,
        n_andamios: int = 20,
        tono: str = "profesional",
    ) -> dict[str, Any]:
        """Detalle del parque de maquinaria."""
        caption_text = self.caption(
            "equipo_trabajo_maquinaria",
            tono,
            zona=zona,
            n_excavadoras=n_excavadoras,
            marca=marca,
            n_bulldozers=n_bulldozers,
            n_camiones=n_camiones,
            n_hormigoneras=n_hormigoneras,
            n_andamios=n_andamios,
        )
        hashtags = self.hashtags(["construccion", "ingenieria", "general"], zona)
        return self._armar_post(
            f"Equipo pesado en {zona}",
            "equipo_trabajo_maquinaria",
            zona,
            tono,
            caption_text,
            hashtags,
        )

    def post_permisos_tramites(
        self,
        zona: str = "Cañuelas",
        plazo_min: str = "2",
        plazo_max: str = "6",
        tono: str = "practico",
    ) -> dict[str, Any]:
        """Tramites municipales para construir."""
        caption_text = self.caption(
            "permisos_tramites", tono, zona=zona, plazo_min=plazo_min, plazo_max=plazo_max
        )
        hashtags = self.hashtags(["permisos", "construccion", "general"], zona)
        return self._armar_post(
            f"Trámites en {zona}", "permisos_tramites", zona, tono, caption_text, hashtags
        )

    def post_diseno_interior_acabados(self, tono: str = "aspiracional") -> dict[str, Any]:
        """Diseno de interiores y acabados."""
        caption_text = self.caption("diseno_interior_acabados", tono)
        hashtags = self.hashtags(["diseno_interior", "decoracion", "casas"])
        return self._armar_post(
            "Diseño de interiores", "diseno_interior_acabados", "", tono, caption_text, hashtags
        )

    def _armar_post(
        self,
        tema: str,
        tipo: str,
        municipio: str,
        tono: str,
        caption_text: str,
        hashtags: list[str],
    ) -> dict[str, Any]:
        return {
            "fecha_creacion": datetime.now().isoformat(timespec="seconds"),
            "tema": tema,
            "tipo": tipo,
            "municipio": municipio,
            "tono": tono,
            "caption": caption_text,
            "hashtags": hashtags,
            "caption_completo": caption_text + "\n\n" + " ".join(hashtags),
        }


class RealestateStudio:
    """Orquestador principal. Punto de entrada del estudio."""

    def __init__(self, fooocus_url: str = FOOOCUS_DEFAULT_URL):
        self.client = FooocusClient(fooocus_url)
        self.prompts_db = self._cargar_json(PROMPTS_DB, default=self._prompts_default())
        self.captions_db = self._cargar_json(CAPTIONS_DB, default=self._captions_default())
        self.lotes = VerticalLotes(self.prompts_db)
        self.construccion = VerticalConstruccion(self.prompts_db)
        self.post = CaptionFactory(self.captions_db)

    @staticmethod
    def _cargar_json(ruta: Path, default: dict) -> dict:
        if ruta.exists():
            return json.loads(ruta.read_text(encoding="utf-8"))
        ruta.write_text(json.dumps(default, indent=2, ensure_ascii=False), encoding="utf-8")
        return default

    def fooocus_activo(self) -> bool:
        return self.client.disponible()

    def guardar_prompt(
        self, req: GenerationRequest, nombre: str, subcarpeta: str = "outputs"
    ) -> Path:
        carpeta = ROOT / "inmuebles" / subcarpeta
        carpeta.mkdir(parents=True, exist_ok=True)
        ruta = carpeta / f"{nombre}.json"
        ruta.write_text(json.dumps(req.to_dict(), indent=2, ensure_ascii=False))
        return ruta

    def guardar_post(self, post: dict[str, Any], nombre: str, proyecto: str | None = None) -> Path:
        if proyecto:
            carpeta = LOTES_DIR / proyecto / "posts"
        else:
            carpeta = POSTS_DIR
        carpeta.mkdir(parents=True, exist_ok=True)
        ruta = carpeta / f"{nombre}.json"
        ruta.write_text(json.dumps(post, indent=2, ensure_ascii=False), encoding="utf-8")
        return ruta

    # ---------------- Bases por defecto (no se usan si los JSON existen) ----------------

    def _prompts_default(self) -> dict[str, Any]:
        return {
            "plantillas_base": {
                "chacra_pampeana": "wide rural landscape, pampas grass, omb\u00fa trees",
                "country_premium": "luxury gated community entrance, manicured grounds",
            },
            "negativos_default": "blurry, low quality, distorted, watermark, text, logo",
        }

    def _captions_default(self) -> dict[str, Any]:
        return {
            "plantillas": {"lote_venta": [{"tono": "emotivo", "texto": "{tema}"}]},
            "hashtags_por_nicho": {"general": ["#lotes"]},
            "hashtags_zona_template": ["#{municipio_sin_espacios}"],
        }


def demo() -> None:
    """Demostracion del estudio con un lote de ejemplo en el AMBA."""
    studio = RealestateStudio()
    print("=" * 60)
    print("REALESTATE STUDIO AMBA - Demo")
    print("=" * 60)
    print(f"Fooocus activo: {studio.fooocus_activo()}")
    print()

    print("--- PROMPT: Chacra 5 ha en Ca\u00f1uelas ---")
    req = studio.lotes.chacra_pampeana(hectareas=5, municipio="Ca\u00f1uelas")
    print(f"Prompt: {req.prompt}\n")
    print(f"Aspecto: {req.aspect_ratio}")
    print(f"Estilos: {req.styles}")
    print()

    print("--- CAPTION: Post de venta ---")
    post = studio.post.post_lote_venta(
        tema="5 ha en Ca\u00f1uelas, a 65 km de CABA",
        municipio="Ca\u00f1uelas",
        hectareas="5 hectareas",
        distancia_caba="65 km",
        tono="emotivo",
    )
    print(post["caption_completo"])
    print()

    ruta_prompt = studio.guardar_prompt(req, "chacra_canuelas_5ha", subcarpeta="outputs")
    ruta_post = studio.guardar_post(post, "venta_chacra_canuelas", proyecto="chacra-canuelas-5ha")
    print(f"Prompt guardado: {ruta_prompt}")
    print(f"Post guardado:   {ruta_post}")


if __name__ == "__main__":
    demo()
