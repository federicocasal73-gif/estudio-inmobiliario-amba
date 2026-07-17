"""Tests para caption_variants.py - Generador de variantes A/B testing."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from caption_variants import CaptionVariants, VarianteCaption


@pytest.fixture
def mock_studio():
    studio = MagicMock()
    studio.post.post_lote_venta.return_value = {
        "caption": "Hermosa chacra a la venta",
        "hashtags": ["#lotes", "#chacras"],
        "caption_completo": "Hermosa chacra a la venta\n\n#lotes #chacras",
        "tema": "5 ha en Canuelas",
    }
    studio.post.post_country.return_value = {
        "caption": "Country premium",
        "hashtags": ["#country"],
        "caption_completo": "Country premium\n\n#country",
        "tema": "Country Los Alamos",
    }
    studio.post.post_campo.return_value = {
        "caption": "Campo productivo",
        "hashtags": ["#campo"],
        "caption_completo": "Campo productivo\n\n#campo",
        "tema": "Campo 10ha",
    }
    studio.post.post_preventa.return_value = {
        "caption": "Preventa loteo",
        "hashtags": ["#preventa"],
        "caption_completo": "Preventa loteo\n\n#preventa",
        "tema": "Loteo nuevo",
    }
    studio.post.post_lote_periurbano.return_value = {
        "caption": "Lote periurbano",
        "hashtags": ["#lotes"],
        "caption_completo": "Lote periurbano\n\n#lotes",
        "tema": "Lote Glew",
    }
    studio.post.post_testimonial_cliente.return_value = {
        "caption": "Testimonio cliente",
        "hashtags": ["#testimonio"],
        "caption_completo": "Testimonio\n\n#testimonio",
        "tema": "Cliente feliz",
    }
    studio.post.post_preguntas_frecuentes.return_value = {
        "caption": "FAQ",
        "hashtags": ["#faq"],
        "caption_completo": "FAQ\n\n#faq",
        "tema": "Preguntas frecuentes",
    }
    studio.post.post_obra_avance_semanal.return_value = {
        "caption": "Avance obra",
        "hashtags": ["#obra"],
        "caption_completo": "Avance obra\n\n#obra",
        "tema": "Obra semana 5",
    }
    studio.post.post_reel_hook.return_value = {
        "caption": "Reel hook",
        "hashtags": ["#reel"],
        "caption_completo": "Reel hook\n\n#reel",
        "tema": "Hook corto",
    }
    return studio


class TestVarianteCaption:
    def test_creation(self):
        v = VarianteCaption(
            variante_id="v1_emotivo",
            tipo="lote_venta",
            tono="emotivo",
            nicho=["general"],
            tema="Test",
            caption="Caption",
            hashtags=["#test"],
            caption_completo="Caption\n\n#test",
        )
        assert v.variante_id == "v1_emotivo"
        assert v.tipo == "lote_venta"
        assert v.tono == "emotivo"

    def test_to_dict(self):
        v = VarianteCaption(
            variante_id="v1_test",
            tipo="lote_venta",
            tono="emotivo",
            nicho=["general"],
            tema="T",
            caption="C",
            hashtags=["#t"],
            caption_completo="C\n\n#t",
        )
        d = v.to_dict()
        assert isinstance(d, dict)
        assert d["variante_id"] == "v1_test"
        assert "fecha_creacion" in d

    def test_default_metadata(self):
        v = VarianteCaption(
            variante_id="v1",
            tipo="t",
            tono="emotivo",
            nicho=[],
            tema="",
            caption="",
            hashtags=[],
            caption_completo="",
        )
        assert v.metadata == {}
        assert v.fecha_creacion != ""


class TestCaptionVariants:
    def test_generar_lote_venta(self, mock_studio):
        cv = CaptionVariants(mock_studio)
        variantes = cv.generar(
            tipo="lote_venta",
            n=3,
            tema="5 ha en Canuelas",
            municipio="Canuelas",
            hectareas="5 ha",
            distancia_caba="65 km",
            tonos=["emotivo", "inversion", "premium"],
        )
        assert len(variantes) == 3
        assert variantes[0].tono == "emotivo"
        assert variantes[1].tono == "inversion"
        assert variantes[2].tono == "premium"
        assert all(v.tipo == "lote_venta" for v in variantes)

    def test_generar_con_tonos_default(self, mock_studio):
        cv = CaptionVariants(mock_studio)
        variantes = cv.generar(
            tipo="lote_venta",
            n=2,
            tema="Test",
            municipio="Canuelas",
        )
        assert len(variantes) == 2

    def test_generar_country(self, mock_studio):
        cv = CaptionVariants(mock_studio)
        variantes = cv.generar(
            tipo="country",
            n=2,
            tema="Country test",
            municipio="Ezeiza",
        )
        assert len(variantes) == 2

    def test_generar_campo(self, mock_studio):
        cv = CaptionVariants(mock_studio)
        variantes = cv.generar(
            tipo="campo",
            n=1,
            tema="Campo test",
            municipio="Cañuelas",
        )
        assert len(variantes) == 1

    def test_generar_pocos_tonos(self, mock_studio):
        cv = CaptionVariants(mock_studio)
        variantes = cv.generar(
            tipo="lote_venta",
            n=5,
            tema="Test",
            municipio="Canuelas",
            tonos=["emotivo"],
        )
        assert len(variantes) == 5
        assert all(v.tono == "emotivo" for v in variantes)

    def test_generar_con_nichos_custom(self, mock_studio):
        cv = CaptionVariants(mock_studio)
        variantes = cv.generar(
            tipo="lote_venta",
            n=1,
            tema="Test",
            municipio="Canuelas",
            nichos=["custom_nicho"],
        )
        assert len(variantes) == 1
        assert "custom_nicho" in variantes[0].nicho

    def test_generar_tipo_no_soportado(self, mock_studio):
        cv = CaptionVariants(mock_studio)
        variantes = cv.generar(
            tipo="tipo_inexistente",
            n=1,
            tema="Test",
            municipio="Canuelas",
        )
        assert len(variantes) == 1
        assert "ERROR" in variantes[0].caption or "ERROR" in variantes[0].caption_completo

    def test_tonos_por_tipo_lote_venta(self, mock_studio):
        cv = CaptionVariants(mock_studio)
        tonos = cv._tonos_por_tipo("lote_venta")
        assert "emotivo" in tonos
        assert "inversion" in tonos

    def test_tonos_por_tipo_desconocido(self, mock_studio):
        cv = CaptionVariants(mock_studio)
        tonos = cv._tonos_por_tipo("tipo_random")
        assert tonos == ["emotivo"]

    def test_nichos_por_tipo_lote_venta(self, mock_studio):
        cv = CaptionVariants(mock_studio)
        nichos = cv._nichos_por_tipo("lote_venta")
        assert "general" in nichos
        assert "campo" in nichos

    def test_nichos_por_tipo_desconocido(self, mock_studio):
        cv = CaptionVariants(mock_studio)
        nichos = cv._nichos_por_tipo("tipo_random")
        assert nichos == ["general"]

    def test_guardar(self, mock_studio, tmp_path):
        import caption_variants
        original_root = caption_variants.ROOT
        caption_variants.ROOT = tmp_path

        try:
            cv = CaptionVariants(mock_studio)
            variantes = cv.generar(
                tipo="lote_venta",
                n=2,
                tema="Test",
                municipio="Canuelas",
                tonos=["emotivo", "premium"],
            )
            carpeta = cv.guardar(variantes, proyecto="test-proyecto")
            assert carpeta.exists()

            json_files = list(carpeta.glob("*.json"))
            txt_files = list(carpeta.glob("*.txt"))
            assert len(json_files) == 1
            assert len(txt_files) == 1

            data = json.loads(json_files[0].read_text(encoding="utf-8"))
            assert data["n_variantes"] == 2
            assert len(data["variantes"]) == 2
        finally:
            caption_variants.ROOT = original_root

    def test_guardar_sin_proyecto(self, mock_studio, tmp_path):
        import caption_variants
        original_root = caption_variants.ROOT
        caption_variants.ROOT = tmp_path

        try:
            cv = CaptionVariants(mock_studio)
            variantes = cv.generar(
                tipo="lote_venta",
                n=1,
                tema="Test",
                municipio="Canuelas",
            )
            carpeta = cv.guardar(variantes)
            assert carpeta.exists()
        finally:
            caption_variants.ROOT = original_root

    def test_mejor_caption_sin_criterios(self, mock_studio):
        cv = CaptionVariants(mock_studio)
        variantes = cv.generar(
            tipo="lote_venta",
            n=3,
            tema="Test",
            municipio="Canuelas",
        )
        mejor = cv.mejor_caption_para_publicar(variantes)
        assert mejor in variantes

    def test_mejor_caption_con_tono_preferido(self, mock_studio):
        cv = CaptionVariants(mock_studio)
        variantes = cv.generar(
            tipo="lote_venta",
            n=3,
            tema="Test",
            municipio="Canuelas",
            tonos=["premium", "emotivo", "inversion"],
        )
        mejor = cv.mejor_caption_para_publicar(
            variantes,
            criterios={"tono_preferido": ["emotivo", "inversion", "premium"]},
        )
        assert mejor.tono == "emotivo"

    def test_mejor_caption_con_max_caracteres(self, mock_studio):
        cv = CaptionVariants(mock_studio)
        variantes = cv.generar(
            tipo="lote_venta",
            n=3,
            tema="Test",
            municipio="Canuelas",
        )
        mejor = cv.mejor_caption_para_publicar(
            variantes,
            criterios={"max_caracteres": 50},
        )
        assert mejor is not None

    def test_mejor_caption_con_nicho_preferido(self, mock_studio):
        cv = CaptionVariants(mock_studio)
        variantes = cv.generar(
            tipo="lote_venta",
            n=3,
            tema="Test",
            municipio="Canuelas",
        )
        mejor = cv.mejor_caption_para_publicar(
            variantes,
            criterios={"nicho_preferido": "campo"},
        )
        assert mejor is not None

    def test_mejor_caption_todos_los_tipos(self, mock_studio):
        cv = CaptionVariants(mock_studio)
        for tipo in [
            "lote_venta",
            "country",
            "campo",
            "preventa_loteo",
            "lote_periurbano",
            "testimonial_cliente",
            "preguntas_frecuentes",
            "obra_avance_semanal",
            "reel_hook_corto",
        ]:
            variantes = cv.generar(
                tipo=tipo,
                n=1,
                tema="Test",
                municipio="Canuelas",
            )
            assert len(variantes) >= 1
