"""Tests para carruseles.py - Sistema de carruseles Instagram."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from carruseles import (
    Carrusel,
    CarruselFactory,
    CaptionNarrativo,
    Slide,
    ASPECT_INSTAGRAM_POST,
)


@pytest.fixture
def mock_studio():
    studio = MagicMock()

    # lotes
    studio.lotes.chacra_pampeana.return_value = MagicMock(
        prompt="chacra pampeana", aspect_ratio="896*1152", styles=["Fooocus V2"]
    )
    studio.lotes.vista_aerea_loteo.return_value = MagicMock(
        prompt="vista aerea", aspect_ratio="1152*896", styles=["Fooocus V2"]
    )
    studio.lotes.tranquera_argentina.return_value = MagicMock(
        prompt="tranquera", aspect_ratio="896*1152", styles=["Fooocus V2"]
    )
    studio.lotes.molino_tanque_australiano.return_value = MagicMock(
        prompt="molino", aspect_ratio="896*1152", styles=["Fooocus V2"]
    )
    studio.lotes.country_premium.return_value = MagicMock(
        prompt="country", aspect_ratio="896*1152", styles=["Fooocus V2"]
    )
    studio.lotes.loteo_en_desarrollo.return_value = MagicMock(
        prompt="loteo", aspect_ratio="1152*896", styles=["Fooocus V2"]
    )
    studio.lotes.amanecer_pampa.return_value = MagicMock(
        prompt="amanecer", aspect_ratio="896*1152", styles=["Fooocus V2"]
    )

    # construccion
    studio.construccion.render_proyecto.return_value = MagicMock(
        prompt="render", aspect_ratio="1152*896", styles=["Fooocus V2"]
    )
    studio.construccion.obra_gruesa.return_value = MagicMock(
        prompt="obra", aspect_ratio="896*1152", styles=["Fooocus V2"]
    )
    for method_name in [
        "replanteo_obra", "excavacion_fundaciones", "fundaciones_hormigon",
        "estructura_hormigon", "mamposteria_ladrillo", "cubierta_techo",
        "revoque_grueso", "colocacion_aberturas", "colocacion_pisos",
        "pintura_interior", "anteproyecto_arquitectonico", "steel_frame_estructura",
        "steel_frame_cerramiento", "casa_terminada_frente", "render_exterior_casa",
        "estudio_de_suelo", "permisos_tramites", "movimiento_suelo",
        "diseno_interior_acabados", "entrega_llaves", "garantia_postventa",
        "fachada_moderna_minimalista", "render_interior_casa",
    ]:
        setattr(
            studio.construccion,
            method_name,
            MagicMock(return_value=MagicMock(prompt=f"prompt_{method_name}", aspect_ratio="896*1152", styles=["Fooocus V2"])),
        )

    # post
    studio.post.hashtags.return_value = ["#lotes", "#campo", "#inversion", "#canuelas"]
    studio.post.post_reel_hook.return_value = {"caption": "Reel hook corto"}

    return studio


class TestSlide:
    def test_creation(self):
        s = Slide(numero=1, tipo="portada", descripcion="Test slide")
        assert s.numero == 1
        assert s.tipo == "portada"
        assert s.aspect_ratio == ASPECT_INSTAGRAM_POST

    def test_to_dict(self):
        s = Slide(numero=1, tipo="foto", descripcion="Test")
        d = s.to_dict()
        assert isinstance(d, dict)
        assert d["numero"] == 1


class TestCarrusel:
    def test_creation(self):
        c = Carrusel(
            tema="Test",
            tipo="lote_premium",
            municipio="Canuelas",
            tono="emotivo",
            slides=[Slide(numero=1, tipo="portada", descripcion="s1")],
            caption_narrativo="Caption test",
            hashtags=["#test"],
        )
        assert c.tema == "Test"
        assert c.n_slides == 1

    def test_caption_completo(self):
        c = Carrusel(
            tema="T",
            tipo="t",
            municipio="M",
            tono="emotivo",
            slides=[],
            caption_narrativo="Caption",
            hashtags=["#a", "#b"],
        )
        assert c.caption_completo == "Caption\n\n#a #b"

    def test_to_dict(self):
        c = Carrusel(
            tema="T",
            tipo="t",
            municipio="M",
            tono="emotivo",
            slides=[Slide(numero=1, tipo="portada", descripcion="s1")],
            caption_narrativo="C",
            hashtags=["#t"],
        )
        d = c.to_dict()
        assert "n_slides" in d
        assert "caption_completo" in d


class TestCaptionNarrativo:
    def test_unir_emotivo(self):
        slides = [Slide(numero=1, tipo="foto", descripcion="Test", texto_overlay="Texto 1")]
        result = CaptionNarrativo.unir("Tema test", "Canuelas", slides, tono="emotivo")
        assert "Tema test" in result
        assert "Canuelas" in result
        assert "Slide 1" in result

    def test_unir_inversion(self):
        slides = [Slide(numero=1, tipo="foto", descripcion="Test")]
        result = CaptionNarrativo.unir("Tema", "Pilar", slides, tono="inversion")
        assert "Tema" in result

    def test_unir_premium(self):
        slides = [Slide(numero=1, tipo="foto", descripcion="Test")]
        result = CaptionNarrativo.unir("Tema", "Escobar", slides, tono="premium")
        assert "Tema" in result

    def test_unir_desconocido(self):
        slides = [Slide(numero=1, tipo="foto", descripcion="Test")]
        result = CaptionNarrativo.unir("T", "M", slides, tono="random")
        assert "T" in result

    def test_unir_varios_slides(self):
        slides = [
            Slide(numero=1, tipo="foto", descripcion="s1", texto_overlay="Texto 1"),
            Slide(numero=2, tipo="dato", descripcion="s2"),
            Slide(numero=3, tipo="cta", descripcion="s3"),
        ]
        result = CaptionNarrativo.unir("T", "M", slides)
        assert "Slide 1" in result
        assert "Slide 2" in result
        assert "Slide 3" in result

    def test_unir_gancho_custom(self):
        slides = [Slide(numero=1, tipo="foto", descripcion="s1")]
        result = CaptionNarrativo.unir("T", "M", slides, gancho_inicial="Mi gancho")
        assert "Mi gancho" in result


class TestCarruselFactory:
    def test_lote_premium(self, mock_studio):
        factory = CarruselFactory(mock_studio)
        c = factory.lote_premium(
            tema="5 ha en Canuelas",
            municipio="Canuelas",
            hectareas=5,
            precio_usd="USD 60.000",
            n_slides=6,
        )
        assert c.tipo == "lote_premium"
        assert c.n_slides == 6
        assert c.municipio == "Canuelas"

    def test_lote_premium_min_slides(self, mock_studio):
        factory = CarruselFactory(mock_studio)
        c = factory.lote_premium(
            tema="T", municipio="M", hectareas=5, n_slides=2
        )
        assert c.n_slides >= 4

    def test_country_etapa(self, mock_studio):
        factory = CarruselFactory(mock_studio)
        c = factory.country_etapa(
            nombre_country="El Casco",
            municipio="Pilar",
            etapa="2",
            n_lotes=12,
            n_slides=5,
        )
        assert c.tipo == "country_etapa"
        assert c.n_slides == 5

    def test_country_etapa_min_slides(self, mock_studio):
        factory = CarruselFactory(mock_studio)
        c = factory.country_etapa(
            nombre_country="X", municipio="M", n_slides=1
        )
        assert c.n_slides >= 3

    def test_country_etapa_7_slides(self, mock_studio):
        factory = CarruselFactory(mock_studio)
        c = factory.country_etapa(
            nombre_country="X", municipio="M", n_slides=7
        )
        assert c.n_slides == 7

    def test_obra_avance(self, mock_studio):
        factory = CarruselFactory(mock_studio)
        c = factory.obra_avance(
            nombre_obra="Casa Perez",
            municipio="Escobar",
            semana=3,
            etapa="mamposteria",
            n_slides=4,
        )
        assert c.tipo == "obra_avance"
        assert c.n_slides == 4

    def test_obra_avance_con_foto(self, mock_studio, tmp_path):
        foto = tmp_path / "foto.jpg"
        foto.write_bytes(b"\x00" * 1024)
        factory = CarruselFactory(mock_studio)
        c = factory.obra_avance(
            nombre_obra="Casa X",
            municipio="M",
            semana=1,
            etapa="fundaciones",
            foto_antes_path=str(foto),
            n_slides=3,
        )
        assert c.n_slides >= 3

    def test_obra_avance_min_slides(self, mock_studio):
        factory = CarruselFactory(mock_studio)
        c = factory.obra_avance(
            nombre_obra="X", municipio="M", semana=1, etapa="etapa", n_slides=1
        )
        assert c.n_slides >= 3

    def test_servicios(self, mock_studio):
        factory = CarruselFactory(mock_studio)
        c = factory.servicios(
            empresa="Construcciones Rurales",
            municipio="Canuelas",
            n_slides=6,
        )
        assert c.tipo == "servicios"
        # 6 servicios default + portada + CTA = 8
        assert c.n_slides == 8

    def test_servicios_custom_servicios(self, mock_studio):
        factory = CarruselFactory(mock_studio)
        c = factory.servicios(
            empresa="Test",
            municipio="M",
            servicios=["Servicio A", "Servicio B"],
            n_slides=4,
        )
        assert c.n_slides == 4

    def test_story(self, mock_studio):
        factory = CarruselFactory(mock_studio)
        c = factory.story(tema="T", municipio="M")
        assert c.tipo == "story"
        assert c.n_slides == 3

    def test_story_custom_prompts(self, mock_studio):
        factory = CarruselFactory(mock_studio)
        c = factory.story(
            tema="T", municipio="M",
            imagen_prompts=["prompt1", "prompt2"],
        )
        assert c.n_slides == 2

    def test_reel(self, mock_studio):
        factory = CarruselFactory(mock_studio)
        c = factory.reel(tema="T", municipio="M")
        assert c.tipo == "reel"
        assert c.n_slides == 1

    def test_reel_custom_prompt(self, mock_studio):
        factory = CarruselFactory(mock_studio)
        c = factory.reel(tema="T", municipio="M", prompt_principal="mi prompt")
        assert c.n_slides == 1

    def test_etapas_construccion(self, mock_studio):
        factory = CarruselFactory(mock_studio)
        c = factory.etapas_construccion(municipio="Canuelas", n_slides=8)
        assert c.tipo == "etapas_construccion"
        assert c.n_slides >= 8

    def test_etapas_construccion_min(self, mock_studio):
        factory = CarruselFactory(mock_studio)
        c = factory.etapas_construccion(n_slides=3)
        assert c.n_slides >= 8

    def test_steel_frame_completo(self, mock_studio):
        factory = CarruselFactory(mock_studio)
        c = factory.steel_frame_completo(municipio="Canuelas", n_slides=6)
        assert c.tipo == "steel_frame"
        assert c.n_slides == 6

    def test_steel_frame_min(self, mock_studio):
        factory = CarruselFactory(mock_studio)
        c = factory.steel_frame_completo(n_slides=2)
        assert c.n_slides >= 5

    def test_llave_en_mano(self, mock_studio):
        factory = CarruselFactory(mock_studio)
        c = factory.llave_en_mano_completo(municipio="Canuelas", n_slides=8)
        assert c.tipo == "llave_en_mano"
        assert c.n_slides == 8

    def test_llave_en_mano_min(self, mock_studio):
        factory = CarruselFactory(mock_studio)
        c = factory.llave_en_mano_completo(n_slides=3)
        assert c.n_slides >= 7

    def test_terminaciones(self, mock_studio):
        factory = CarruselFactory(mock_studio)
        c = factory.terminaciones_detalle(municipio="Canuelas", n_slides=6)
        assert c.tipo == "terminaciones"
        assert c.n_slides == 6

    def test_terminaciones_min(self, mock_studio):
        factory = CarruselFactory(mock_studio)
        c = factory.terminaciones_detalle(n_slides=2)
        assert c.n_slides >= 5

    def test_obra_completa(self, mock_studio):
        factory = CarruselFactory(mock_studio)
        c = factory.obra_completa(
            nombre_obra="Casa Test",
            municipio="Canuelas",
            n_slides=8,
        )
        assert c.tipo == "obra_completa"
        assert c.n_slides == 8

    def test_obra_completa_min(self, mock_studio):
        factory = CarruselFactory(mock_studio)
        c = factory.obra_completa(nombre_obra="X", n_slides=3)
        assert c.n_slides >= 6

    def test_guardar(self, mock_studio, tmp_path):
        import carruseles
        original_root = carruseles.ROOT
        carruseles.ROOT = tmp_path

        try:
            factory = CarruselFactory(mock_studio)
            c = factory.lote_premium(
                tema="T", municipio="M", hectareas=5, n_slides=4
            )
            carpeta = factory.guardar(c, "test_carrusel", proyecto="test-proyecto")
            assert carpeta.exists()
            assert (carpeta / "carrusel.json").exists()
            assert (carpeta / "carrusel.md").exists()
            assert (carpeta / "caption_instagram.txt").exists()
            assert (carpeta / "slides").is_dir()
        finally:
            carruseles.ROOT = original_root

    def test_guardar_sin_proyecto(self, mock_studio, tmp_path):
        import carruseles
        original_root = carruseles.ROOT
        carruseles.ROOT = tmp_path

        try:
            factory = CarruselFactory(mock_studio)
            c = factory.servicios(empresa="X", municipio="M", n_slides=4)
            carpeta = factory.guardar(c, "test_servicios")
            assert carpeta.exists()
        finally:
            carruseles.ROOT = original_root

    def test_helpers(self):
        assert CarruselFactory._overlay_portada(5, "Canuelas", "USD 60k") == "5 ha · Canuelas · USD 60k"
        assert CarruselFactory._overlay_portada(5, "M", None) == "5 ha · M"
        assert "Lo vemos" in CarruselFactory._overlay_cta("USD 60k", "65 km")
        assert "DM o link" in CarruselFactory._overlay_cta(None, None)
        assert "Últimas unidades" in CarruselFactory._overlay_cta_country("USD 85k", "45 km", 12)
        assert CarruselFactory._proxima_etapa("fundaciones") == "estructura y columnas"
        assert CarruselFactory._proxima_etapa("desconocida") == "avance de obra"


class TestAplicarMejoraASlide:
    def test_n_slide_out_of_range(self, mock_studio):
        factory = CarruselFactory(mock_studio)
        c = factory.lote_premium(tema="T", municipio="M", hectareas=5, n_slides=4)
        with pytest.raises(ValueError, match="fuera de rango"):
            factory.aplicar_mejora_a_slide(c, 99)

    def test_slide_no_es_placeholder(self, mock_studio):
        factory = CarruselFactory(mock_studio)
        c = factory.lote_premium(tema="T", municipio="M", hectareas=5, n_slides=4)
        result = factory.aplicar_mejora_a_slide(c, 1)
        assert result["exito"] is False
        assert "placeholder_foto" in result["mensaje"]

    def test_slide_placeholder_sin_path(self, mock_studio):
        factory = CarruselFactory(mock_studio)
        c = factory.lote_premium(tema="T", municipio="M", hectareas=5, n_slides=4)
        slide = c.slides[0]
        slide.tipo = "placeholder_foto"
        slide.metadata = {}
        result = factory.aplicar_mejora_a_slide(c, 1)
        assert result["exito"] is False
        assert "placeholder_foto_path" in result["mensaje"]

    def test_slide_placeholder_path_not_exists(self, mock_studio, tmp_path):
        factory = CarruselFactory(mock_studio)
        c = factory.lote_premium(tema="T", municipio="M", hectareas=5, n_slides=4)
        slide = c.slides[0]
        slide.tipo = "placeholder_foto"
        slide.metadata = {"placeholder_foto_path": "/nonexistent/photo.jpg"}
        result = factory.aplicar_mejora_a_slide(c, 1)
        assert result["exito"] is False
        assert "no encontrada" in result["mensaje"].lower() or "imagen" in result["mensaje"].lower()

    def test_aplicar_mejora_a_todos_los_placeholders(self, mock_studio):
        factory = CarruselFactory(mock_studio)
        c = factory.lote_premium(tema="T", municipio="M", hectareas=5, n_slides=4)
        resultados = factory.aplicar_mejora_a_todos_los_placeholders(c)
        assert len(resultados) == 0


class TestCarruselesAttributeErrorFallbacks:
    def test_llave_en_mano_attribute_error(self, mock_studio):
        # Remove the method to trigger AttributeError
        del mock_studio.construccion.permisos_tramites
        factory = CarruselFactory(mock_studio)
        c = factory.llave_en_mano_completo(municipio="M", n_slides=8)
        assert c.n_slides >= 7

    def test_terminaciones_attribute_error(self, mock_studio):
        del mock_studio.construccion.fachada_moderna_minimalista
        factory = CarruselFactory(mock_studio)
        c = factory.terminaciones_detalle(municipio="M", n_slides=6)
        assert c.n_slides >= 5

    def test_obra_completa_attribute_error(self, mock_studio):
        del mock_studio.construccion.estructura_hormigon
        factory = CarruselFactory(mock_studio)
        c = factory.obra_completa(nombre_obra="Casa X", municipio="M", n_slides=7)
        assert c.n_slides >= 6


class TestCarruselMarkdownWithPlaceholder:
    def test_placeholder_foto_path_in_markdown(self, mock_studio):
        from carruseles import CarruselFactory
        c = Carrusel(
            tema="Test",
            tipo="obra_avance",
            municipio="M",
            tono="emotivo",
            slides=[
                Slide(
                    numero=1,
                    tipo="placeholder_foto",
                    descripcion="Foto antes",
                    metadata={"placeholder_foto_path": "fotos/antes.jpg"},
                ),
            ],
            caption_narrativo="Test caption",
            hashtags=["#test"],
        )
        md = CarruselFactory._a_markdown(c)
        assert "fotos/antes.jpg" in md
        assert "Foto requerida" in md


class TestDemo:
    def test_demo(self, mock_studio):
        import carruseles
        from unittest.mock import patch
        original_root = carruseles.ROOT

        try:
            carruseles.ROOT = Path("/tmp/demo_test")
            with patch("realestate_studio.RealestateStudio", return_value=mock_studio):
                from carruseles import demo
                demo()
        finally:
            carruseles.ROOT = original_root
