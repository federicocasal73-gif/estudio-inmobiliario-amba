"""Tests del modulo carruseles.py.

Cubre:
  - Slide dataclass
  - Carrusel dataclass (n_slides, caption_completo, to_dict)
  - CaptionNarrativo.unir: emotivo, inversion, premium, default
  - CarruselFactory: lote_premium, country_etapa, obra_avance, servicios,
    story, reel, etapas_construccion, steel_frame_completo,
    llave_en_mano_completo, terminaciones_detalle, obra_completa
  - guardar: JSON, slides, markdown, caption
  - _a_markdown
  - _overlay_portada, _overlay_cta, _overlay_cta_country, _proxima_etapa
  - aplicar_mejora_a_slide: placeholder_foto, non-placeholder, out of range
  - aplicar_mejora_a_todos_los_placeholders
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from carruseles import (
    ASPECT_INSTAGRAM_POST,
    ROOT,
    CaptionNarrativo,
    Carrusel,
    CarruselFactory,
    Slide,
)

# ===== Fixtures: Mocks =====


def _mock_studio():
    """Crea un mock de RealestateStudio con lotes, construccion y post."""
    studio = MagicMock()

    def _make_req(prompt, aspect, styles):
        req = MagicMock()
        req.prompt = prompt
        req.aspect_ratio = aspect
        req.styles = styles
        return req

    # Mock lotes
    studio.lotes.chacra_pampeana = MagicMock(
        side_effect=lambda **kw: _make_req("prompt_chacra", ASPECT_INSTAGRAM_POST, ["Fooocus V2"])
    )
    studio.lotes.vista_aerea_loteo = MagicMock(
        side_effect=lambda **kw: _make_req("prompt_aerea", "1152*896", ["Fooocus V2"])
    )
    studio.lotes.tranquera_argentina = MagicMock(
        side_effect=lambda **kw: _make_req(
            "prompt_tranquera", ASPECT_INSTAGRAM_POST, ["Fooocus V2"]
        )
    )
    studio.lotes.molino_tanque_australiano = MagicMock(
        side_effect=lambda **kw: _make_req("prompt_molino", ASPECT_INSTAGRAM_POST, ["Fooocus V2"])
    )
    studio.lotes.country_premium = MagicMock(
        side_effect=lambda **kw: _make_req("prompt_country", "1152*896", ["Fooocus V2"])
    )
    studio.lotes.loteo_en_desarrollo = MagicMock(
        side_effect=lambda **kw: _make_req("prompt_loteo", "1152*896", ["Fooocus V2"])
    )
    studio.lotes.amanecer_pampa = MagicMock(
        side_effect=lambda **kw: _make_req("prompt_amanecer", ASPECT_INSTAGRAM_POST, ["Fooocus V2"])
    )

    # Mock construccion
    studio.construccion.render_proyecto = MagicMock(
        side_effect=lambda **kw: _make_req("prompt_render", ASPECT_INSTAGRAM_POST, ["Fooocus V2"])
    )
    studio.construccion.obra_gruesa = MagicMock(
        side_effect=lambda **kw: _make_req("prompt_obra", ASPECT_INSTAGRAM_POST, ["Fooocus V2"])
    )
    studio.construccion.replanteo_obra = MagicMock(
        side_effect=lambda **kw: _make_req(
            "prompt_replanteo", ASPECT_INSTAGRAM_POST, ["Fooocus V2"]
        )
    )
    studio.construccion.excavacion_fundaciones = MagicMock(
        side_effect=lambda **kw: _make_req(
            "prompt_excavacion", ASPECT_INSTAGRAM_POST, ["Fooocus V2"]
        )
    )
    studio.construccion.fundaciones_hormigon = MagicMock(
        side_effect=lambda **kw: _make_req(
            "prompt_fundaciones", ASPECT_INSTAGRAM_POST, ["Fooocus V2"]
        )
    )
    studio.construccion.estructura_hormigon = MagicMock(
        side_effect=lambda **kw: _make_req(
            "prompt_estructura", ASPECT_INSTAGRAM_POST, ["Fooocus V2"]
        )
    )
    studio.construccion.mamposteria_ladrillo = MagicMock(
        side_effect=lambda **kw: _make_req(
            "prompt_mamposteria", ASPECT_INSTAGRAM_POST, ["Fooocus V2"]
        )
    )
    studio.construccion.cubierta_techo = MagicMock(
        side_effect=lambda **kw: _make_req("prompt_cubierta", ASPECT_INSTAGRAM_POST, ["Fooocus V2"])
    )
    studio.construccion.revoque_grueso = MagicMock(
        side_effect=lambda **kw: _make_req("prompt_revoque", ASPECT_INSTAGRAM_POST, ["Fooocus V2"])
    )
    studio.construccion.colocacion_aberturas = MagicMock(
        side_effect=lambda **kw: _make_req(
            "prompt_aberturas", ASPECT_INSTAGRAM_POST, ["Fooocus V2"]
        )
    )
    studio.construccion.colocacion_pisos = MagicMock(
        side_effect=lambda **kw: _make_req("prompt_pisos", ASPECT_INSTAGRAM_POST, ["Fooocus V2"])
    )
    studio.construccion.pintura_interior = MagicMock(
        side_effect=lambda **kw: _make_req("prompt_pintura", ASPECT_INSTAGRAM_POST, ["Fooocus V2"])
    )
    studio.construccion.anteproyecto_arquitectonico = MagicMock(
        side_effect=lambda **kw: _make_req("prompt_diseno", ASPECT_INSTAGRAM_POST, ["Fooocus V2"])
    )
    studio.construccion.steel_frame_estructura = MagicMock(
        side_effect=lambda **kw: _make_req("prompt_steel", ASPECT_INSTAGRAM_POST, ["Fooocus V2"])
    )
    studio.construccion.steel_frame_cerramiento = MagicMock(
        side_effect=lambda **kw: _make_req(
            "prompt_cerramiento", ASPECT_INSTAGRAM_POST, ["Fooocus V2"]
        )
    )
    studio.construccion.render_exterior_casa = MagicMock(
        side_effect=lambda **kw: _make_req("prompt_exterior", ASPECT_INSTAGRAM_POST, ["Fooocus V2"])
    )
    studio.construccion.estudio_de_suelo = MagicMock(
        side_effect=lambda **kw: _make_req("prompt_suelo", ASPECT_INSTAGRAM_POST, ["Fooocus V2"])
    )
    studio.construccion.permisos_tramites = MagicMock(
        side_effect=lambda **kw: _make_req("prompt_permisos", ASPECT_INSTAGRAM_POST, ["Fooocus V2"])
    )
    studio.construccion.movimiento_suelo = MagicMock(
        side_effect=lambda **kw: _make_req(
            "prompt_movimiento", ASPECT_INSTAGRAM_POST, ["Fooocus V2"]
        )
    )
    studio.construccion.diseno_interior_acabados = MagicMock(
        side_effect=lambda **kw: _make_req("prompt_interior", ASPECT_INSTAGRAM_POST, ["Fooocus V2"])
    )
    studio.construccion.entrega_llaves = MagicMock(
        side_effect=lambda **kw: _make_req("prompt_entrega", ASPECT_INSTAGRAM_POST, ["Fooocus V2"])
    )
    studio.construccion.garantia_postventa = MagicMock(
        side_effect=lambda **kw: _make_req("prompt_garantia", ASPECT_INSTAGRAM_POST, ["Fooocus V2"])
    )
    studio.construccion.render_interior_casa = MagicMock(
        side_effect=lambda **kw: _make_req(
            "prompt_render_interior", ASPECT_INSTAGRAM_POST, ["Fooocus V2"]
        )
    )
    studio.construccion.casa_terminada_frente = MagicMock(
        side_effect=lambda **kw: _make_req(
            "prompt_casa_terminada", ASPECT_INSTAGRAM_POST, ["Fooocus V2"]
        )
    )
    studio.construccion.fachada_moderna_minimalista = MagicMock(
        side_effect=lambda **kw: _make_req("prompt_fachada", ASPECT_INSTAGRAM_POST, ["Fooocus V2"])
    )

    # Mock post
    studio.post.hashtags = MagicMock(return_value=["#lotes", "#campo", "#inversion"])

    return studio


# ===== Slide dataclass =====


class TestSlide:
    def test_creacion(self):
        s = Slide(
            numero=1,
            tipo="portada",
            descripcion="Portada de prueba",
            prompt="prompt test",
            texto_overlay="Overlay test",
        )
        assert s.numero == 1
        assert s.tipo == "portada"
        assert s.prompt == "prompt test"
        assert s.aspect_ratio == ASPECT_INSTAGRAM_POST

    def test_to_dict(self):
        s = Slide(
            numero=1,
            tipo="foto",
            descripcion="Test",
            prompt="prompt",
            metadata={"key": "value"},
        )
        d = s.to_dict()
        assert d["numero"] == 1
        assert d["tipo"] == "foto"
        assert d["metadata"]["key"] == "value"

    def test_slide_sin_prompt(self):
        s = Slide(numero=1, tipo="dato", descripcion="Dato", prompt="")
        assert s.prompt == ""

    def test_slide_metadata_default(self):
        s = Slide(numero=1, tipo="foto", descripcion="Test")
        assert s.metadata == {}


# ===== Carrusel dataclass =====


class TestCarrusel:
    def test_n_slides(self):
        slides = [
            Slide(numero=1, tipo="portada", descripcion="P"),
            Slide(numero=2, tipo="foto", descripcion="F"),
        ]
        c = Carrusel(
            tema="Test",
            tipo="lote_premium",
            municipio="Cañuelas",
            tono="emotivo",
            slides=slides,
            caption_narrativo="Caption test",
            hashtags=["#lotes"],
        )
        assert c.n_slides == 2

    def test_caption_completo(self):
        c = Carrusel(
            tema="Test",
            tipo="lote_premium",
            municipio="Cañuelas",
            tono="emotivo",
            slides=[],
            caption_narrativo="Caption base",
            hashtags=["#lotes", "#campo"],
        )
        assert c.caption_completo == "Caption base\n\n#lotes #campo"

    def test_to_dict(self):
        c = Carrusel(
            tema="Test",
            tipo="lote_premium",
            municipio="Cañuelas",
            tono="emotivo",
            slides=[Slide(numero=1, tipo="portada", descripcion="P")],
            caption_narrativo="Caption",
            hashtags=["#lotes"],
        )
        d = c.to_dict()
        assert d["n_slides"] == 1
        assert d["caption_completo"] == "Caption\n\n#lotes"

    def test_fecha_creacion(self):
        c = Carrusel(
            tema="T",
            tipo="t",
            municipio="M",
            tono="emotivo",
            slides=[],
            caption_narrativo="",
            hashtags=[],
        )
        assert c.fecha_creacion  # non-empty string


# ===== CaptionNarrativo =====


class TestCaptionNarrativo:
    def _slides(self, n=3):
        return [
            Slide(
                numero=i + 1,
                tipo="foto",
                descripcion=f"Slide {i + 1}",
                texto_overlay=f"Overlay {i + 1}",
            )
            for i in range(n)
        ]

    def test_emotivo(self):
        caption = CaptionNarrativo.unir("Tema Test", "Cañuelas", self._slides(), tono="emotivo")
        assert "Tema Test" in caption
        assert "Cañuelas" in caption
        assert "3 imágenes" in caption

    def test_inversion(self):
        caption = CaptionNarrativo.unir("Tema", "Pilar", self._slides(), tono="inversion")
        assert "📈" in caption
        assert "Los números" in caption

    def test_premium(self):
        caption = CaptionNarrativo.unir("Tema", "Escobar", self._slides(), tono="premium")
        assert "✨" in caption
        assert "3 slides" in caption

    def test_default_tono(self):
        caption = CaptionNarrativo.unir("Tema", "Cañuelas", self._slides(), tono="otro")
        assert "Tema" in caption
        assert "Cañuelas" in caption

    def test_slides_sin_overlay(self):
        slides = [Slide(numero=1, tipo="foto", descripcion="Sin overlay")]
        caption = CaptionNarrativo.unir("T", "M", slides, gancho_inicial="Gancho fijo")
        assert "Sin overlay" in caption

    def test_gancho_inicial_custom(self):
        caption = CaptionNarrativo.unir("T", "M", self._slides(), gancho_inicial="Mi gancho")
        assert "Mi gancho" in caption

    def test_cierre(self):
        caption = CaptionNarrativo.unir("T", "M", self._slides())
        assert "📍 M, Buenos Aires" in caption


# ===== CarruselFactory =====


class TestCarruselFactory:
    def setup_method(self):
        self.studio = _mock_studio()
        self.factory = CarruselFactory(self.studio)

    # --- lote_premium ---

    def test_lote_premium_6_slides(self):
        c = self.factory.lote_premium(
            tema="5 ha en Cañuelas",
            municipio="Cañuelas",
            hectareas=5,
            precio_usd="USD 60.000",
            n_slides=6,
        )
        assert c.tipo == "lote_premium"
        assert c.municipio == "Cañuelas"
        assert c.n_slides == 6
        assert len(c.hashtags) > 0
        # Check that prompts were called
        self.studio.lotes.chacra_pampeana.assert_called_once()
        self.studio.lotes.vista_aerea_loteo.assert_called_once()

    def test_lote_premium_min_slides(self):
        c = self.factory.lote_premium(tema="T", municipio="M", hectareas=2, n_slides=2)
        assert c.n_slides >= 4  # minimum is 4

    def test_lote_premium_metadata(self):
        c = self.factory.lote_premium(
            tema="T",
            municipio="Cañuelas",
            hectareas=3,
            precio_usd="USD 50.000",
            distancia_caba="60 km",
        )
        assert c.metadata["hectareas"] == 3
        assert c.metadata["precio_usd"] == "USD 50.000"
        assert c.metadata["distancia_caba"] == "60 km"

    # --- country_etapa ---

    def test_country_etapa_5_slides(self):
        c = self.factory.country_etapa(
            nombre_country="El Casco",
            municipio="Pilar",
            etapa="2",
            n_slides=5,
        )
        assert c.tipo == "country_etapa"
        assert c.n_slides >= 5
        self.studio.lotes.country_premium.assert_called_once()

    def test_country_etapa_min_slides(self):
        c = self.factory.country_etapa(nombre_country="Test", municipio="M", n_slides=2)
        assert c.n_slides >= 3  # minimum is 3

    def test_country_etapa_metadata(self):
        c = self.factory.country_etapa(
            nombre_country="El Casco",
            municipio="Pilar",
            etapa="3",
            n_lotes=20,
            precio_desde="USD 100.000",
        )
        assert c.metadata["nombre_country"] == "El Casco"
        assert c.metadata["etapa"] == "3"
        assert c.metadata["n_lotes"] == 20

    # --- obra_avance ---

    def test_obra_avance_con_foto(self, tmp_path):
        foto = tmp_path / "foto.jpg"
        foto.write_bytes(b"\xff" * 100)
        c = self.factory.obra_avance(
            nombre_obra="Casa Perez",
            municipio="Escobar",
            semana=3,
            etapa="mamposteria",
            foto_antes_path=str(foto),
            n_slides=4,
        )
        assert c.tipo == "obra_avance"
        assert c.n_slides >= 3

    def test_obra_avance_sin_foto(self):
        c = self.factory.obra_avance(
            nombre_obra="Casa Lopez",
            municipio="Escobar",
            semana=5,
            etapa="estructura",
            n_slides=3,
        )
        assert c.tipo == "obra_avance"
        # Check placeholder path
        placeholder = [s for s in c.slides if s.tipo == "placeholder_foto"]
        assert len(placeholder) > 0

    def test_obra_avance_min_slides(self):
        c = self.factory.obra_avance(
            nombre_obra="Test", municipio="M", semana=1, etapa="replanteo", n_slides=2
        )
        assert c.n_slides >= 3

    # --- servicios ---

    def test_servicios_default(self):
        c = self.factory.servicios()
        assert c.tipo == "servicios"
        assert c.municipio == "Cañuelas"
        assert c.n_slides >= 6  # default 6

    def test_servicios_custom(self):
        c = self.factory.servicios(
            empresa="Mi Empresa",
            municipio="Pilar",
            servicios=["Diseño", "Construccion"],
            n_slides=4,
        )
        assert c.tipo == "servicios"
        assert c.metadata["empresa"] == "Mi Empresa"
        assert len(c.metadata["servicios"]) == 2

    def test_servicios_hashtags_modificados(self):
        """Verifica que se reemplaza #casas por #casasllaveenmano."""
        c = self.factory.servicios()
        assert "#casasllaveenmano" in c.hashtags

    # --- story ---

    def test_story(self):
        c = self.factory.story(tema="Mi historia", municipio="Cañuelas")
        assert c.tipo == "story"
        assert c.metadata["formato"] == "story"
        assert len(c.slides) >= 3

    def test_story_con_prompts(self):
        c = self.factory.story(
            tema="Test",
            municipio="M",
            imagen_prompts=["prompt1", "prompt2"],
        )
        assert len(c.slides) == 2

    # --- reel ---

    def test_reel(self):
        c = self.factory.reel(tema="Mi reel", municipio="Cañuelas")
        assert c.tipo == "reel"
        assert c.n_slides == 1
        assert c.metadata["duracion_segundos"] == 30

    def test_reel_custom_duracion(self):
        c = self.factory.reel(tema="T", municipio="M", duracion_segundos=60)
        assert c.metadata["duracion_segundos"] == 60

    # --- etapas_construccion ---

    def test_etapas_construccion(self):
        c = self.factory.etapas_construccion(metros_cuadrados=120, n_slides=10)
        assert c.tipo == "etapas_construccion"
        assert c.n_slides >= 8

    def test_etapas_construccion_min(self):
        c = self.factory.etapas_construccion(n_slides=5)
        assert c.n_slides >= 8

    # --- steel_frame_completo ---

    def test_steel_frame_completo(self):
        c = self.factory.steel_frame_completo(n_slides=6)
        assert c.tipo == "steel_frame"
        assert c.n_slides >= 5
        assert "Steel Frame" in c.tema

    def test_steel_frame_min(self):
        c = self.factory.steel_frame_completo(n_slides=3)
        assert c.n_slides >= 5

    # --- llave_en_mano_completo ---

    def test_llave_en_mano_completo(self):
        c = self.factory.llave_en_mano_completo(n_slides=8)
        assert c.tipo == "llave_en_mano"
        assert c.n_slides >= 7
        assert "Llave en mano" in c.tema

    def test_llave_en_mano_min(self):
        c = self.factory.llave_en_mano_completo(n_slides=4)
        assert c.n_slides >= 7

    # --- terminaciones_detalle ---

    def test_terminaciones_detalle(self):
        c = self.factory.terminaciones_detalle(n_slides=6)
        assert c.tipo == "terminaciones"
        assert c.n_slides >= 5

    def test_terminaciones_min(self):
        c = self.factory.terminaciones_detalle(n_slides=3)
        assert c.n_slides >= 5

    # --- obra_completa ---

    def test_obra_completa(self):
        c = self.factory.obra_completa(nombre_obra="Casa Test", n_slides=8)
        assert c.tipo == "obra_completa"
        assert c.n_slides >= 6

    def test_obra_completa_min(self):
        c = self.factory.obra_completa(nombre_obra="Test", n_slides=3)
        assert c.n_slides >= 6


# ===== Helpers =====


class TestHelpers:
    def test_overlay_portada(self):
        overlay = CarruselFactory._overlay_portada(5, "Cañuelas", "USD 60.000")
        assert "5 ha" in overlay
        assert "Cañuelas" in overlay
        assert "USD 60.000" in overlay

    def test_overlay_portada_sin_precio(self):
        overlay = CarruselFactory._overlay_portada(3, "Pilar", None)
        assert "3 ha" in overlay
        assert "Pilar" in overlay

    def test_overlay_cta(self):
        cta = CarruselFactory._overlay_cta("USD 50.000", "60 km")
        assert "¿Lo vemos?" in cta
        assert "USD 50.000" in cta
        assert "60 km" in cta

    def test_overlay_cta_sin_distancia(self):
        cta = CarruselFactory._overlay_cta("USD 50.000", None)
        assert "USD 50.000" in cta

    def test_overlay_cta_country(self):
        cta = CarruselFactory._overlay_cta_country("USD 85.000", "45 km", 12)
        assert "Últimas unidades" in cta
        assert "USD 85.000" in cta
        assert "12 lotes" in cta

    def test_proxima_etapa(self):
        assert CarruselFactory._proxima_etapa("fundaciones") == "estructura y columnas"
        assert CarruselFactory._proxima_etapa("pintura") == "entrega de llaves"

    def test_proxima_etapa_default(self):
        assert CarruselFactory._proxima_etapa("no existe") == "avance de obra"


# ===== Persistencia =====


class TestPersistencia:
    def test_guardar(self, tmp_path):
        studio = _mock_studio()
        factory = CarruselFactory(studio)
        c = factory.lote_premium(tema="Test", municipio="Cañuelas", hectareas=5, n_slides=4)

        with patch("carruseles.ROOT", tmp_path):
            ruta = factory.guardar(c, "test_carrusel")

        assert (ruta / "carrusel.json").exists()
        assert (ruta / "carrusel.md").exists()
        assert (ruta / "caption_instagram.txt").exists()
        assert (ruta / "slides").exists()

    def test_guardar_slides(self, tmp_path):
        studio = _mock_studio()
        factory = CarruselFactory(studio)
        c = factory.servicios(n_slides=3)

        with patch("carruseles.ROOT", tmp_path):
            ruta = factory.guardar(c, "servicios")

        slides_dir = ruta / "slides"
        slide_files = list(slides_dir.glob("*.json"))
        assert len(slide_files) == c.n_slides

    def test_guardar_con_proyecto(self, tmp_path):
        studio = _mock_studio()
        factory = CarruselFactory(studio)
        c = factory.lote_premium(tema="T", municipio="M", hectareas=3, n_slides=4)

        with patch("carruseles.ROOT", tmp_path):
            ruta = factory.guardar(c, "lote", proyecto="mi-proyecto", vertical="lotes")

        assert "mi-proyecto" in str(ruta)


# ===== _a_markdown =====


class TestAMarkdown:
    def test_markdown(self):
        slides = [
            Slide(numero=1, tipo="portada", descripcion="Portada", prompt="p1"),
            Slide(numero=2, tipo="dato", descripcion="Dato", texto_overlay="Texto overlay"),
        ]
        c = Carrusel(
            tema="Test Carrusel",
            tipo="lote_premium",
            municipio="Cañuelas",
            tono="emotivo",
            slides=slides,
            caption_narrativo="Caption narrativo",
            hashtags=["#lotes", "#campo"],
        )
        md = CarruselFactory._a_markdown(c)
        assert "Test Carrusel" in md
        assert "Slide 1 · portada" in md
        assert "Prompt SDXL:" in md
        assert "Caption narrativo" in md
        assert "#lotes #campo" in md

    def test_markdown_con_placeholder(self):
        slides = [
            Slide(
                numero=1,
                tipo="placeholder_foto",
                descripcion="Foto real",
                metadata={"placeholder_foto_path": "fotos/test.jpg"},
            )
        ]
        c = Carrusel(
            tema="Test",
            tipo="obra_avance",
            municipio="M",
            tono="practico",
            slides=slides,
            caption_narrativo="",
            hashtags=[],
        )
        md = CarruselFactory._a_markdown(c)
        assert "Foto requerida:" in md
        assert "fotos/test.jpg" in md


# ===== aplicar_mejora_a_slide =====


class TestAplicarMejora:
    def setup_method(self):
        self.studio = _mock_studio()
        self.factory = CarruselFactory(self.studio)

    def test_slide_no_placeholder(self):
        slides = [
            Slide(numero=1, tipo="foto", descripcion="Foto IA", prompt="prompt"),
        ]
        c = Carrusel(
            tema="T",
            tipo="t",
            municipio="M",
            tono="emotivo",
            slides=slides,
            caption_narrativo="",
            hashtags=[],
        )
        result = self.factory.aplicar_mejora_a_slide(c, 1)
        assert result["exito"] is False

    def test_slide_out_of_range(self):
        c = Carrusel(
            tema="T",
            tipo="t",
            municipio="M",
            tono="emotivo",
            slides=[],
            caption_narrativo="",
            hashtags=[],
        )
        with pytest.raises(ValueError):
            self.factory.aplicar_mejora_a_slide(c, 1)

    def test_placeholder_sin_path(self):
        slides = [
            Slide(
                numero=1,
                tipo="placeholder_foto",
                descripcion="Foto",
                metadata={},
            )
        ]
        c = Carrusel(
            tema="T",
            tipo="t",
            municipio="M",
            tono="emotivo",
            slides=slides,
            caption_narrativo="",
            hashtags=[],
        )
        result = self.factory.aplicar_mejora_a_slide(c, 1)
        assert result["exito"] is False

    def test_placeholder_archivo_no_existe(self):
        slides = [
            Slide(
                numero=1,
                tipo="placeholder_foto",
                descripcion="Foto",
                metadata={"placeholder_foto_path": "/no/existe.jpg"},
            )
        ]
        c = Carrusel(
            tema="T",
            tipo="t",
            municipio="M",
            tono="emotivo",
            slides=slides,
            caption_narrativo="",
            hashtags=[],
        )
        result = self.factory.aplicar_mejora_a_slide(c, 1)
        assert result["exito"] is False

    def test_placeholder_con_foto_real(self, tmp_path):
        foto = tmp_path / "foto.jpg"
        foto.write_bytes(b"\xff" * 100)
        slides = [
            Slide(
                numero=1,
                tipo="placeholder_foto",
                descripcion="Foto",
                metadata={"placeholder_foto_path": str(foto)},
            )
        ]
        c = Carrusel(
            tema="T",
            tipo="t",
            municipio="M",
            tono="emotivo",
            slides=slides,
            caption_narrativo="",
            hashtags=[],
        )
        mock_cls = MagicMock()
        mock_instance = MagicMock()
        mock_instance.mejorar.return_value = MagicMock(
            foto_destino="/mejorada.jpg", transformaciones=["crop"]
        )
        mock_cls.return_value = mock_instance
        with patch("mejora_fotos.MejoraFotos", mock_cls):
            result = self.factory.aplicar_mejora_a_slide(c, 1, modo="magazine", intensidad="media")
        assert result["exito"] is True

    def test_aplicar_a_todos_los_placeholders(self, tmp_path):
        foto = tmp_path / "foto.jpg"
        foto.write_bytes(b"\xff" * 100)
        slides = [
            Slide(
                numero=1,
                tipo="foto",
                descripcion="Foto IA",
                prompt="p",
            ),
            Slide(
                numero=2,
                tipo="placeholder_foto",
                descripcion="Foto real",
                metadata={"placeholder_foto_path": str(foto)},
            ),
        ]
        c = Carrusel(
            tema="T",
            tipo="t",
            municipio="M",
            tono="emotivo",
            slides=slides,
            caption_narrativo="",
            hashtags=[],
        )
        mock_cls = MagicMock()
        mock_instance = MagicMock()
        mock_instance.mejorar.return_value = MagicMock(
            foto_destino="/mejorada.jpg", transformaciones=["crop"]
        )
        mock_cls.return_value = mock_instance
        with patch("mejora_fotos.MejoraFotos", mock_cls):
            resultados = self.factory.aplicar_mejora_a_todos_los_placeholders(c)
        assert len(resultados) == 1
        assert resultados[0]["exito"] is True
