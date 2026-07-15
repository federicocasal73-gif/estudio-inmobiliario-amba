"""Tests del modulo caption_variants.py.

Cubre:
  - VarianteCaption: to_dict
  - CaptionVariants.generar: OK, tipo no soportado, n > tonos
  - _tonos_por_tipo: tipos conocidos, desconocido
  - _nichos_por_tipo: tipos conocidos, desconocido
  - mejor_caption_para_publicar: sin criterios, max_caracteres, tono_preferido, nicho_preferido
  - guardar: con proyecto, sin proyecto, nombre auto-generado
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from caption_variants import CaptionVariants, VarianteCaption


# ===== VarianteCaption =====


class TestVarianteCaption:
    def test_to_dict(self):
        v = VarianteCaption(
            variante_id="v1_emotivo",
            tipo="lote_venta",
            tono="emotivo",
            nicho=["general"],
            tema="5 ha en Cañuelas",
            caption="Caption test",
            hashtags=["#lote"],
            caption_completo="Caption test\n\n#lote",
        )
        d = v.to_dict()
        assert d["variante_id"] == "v1_emotivo"
        assert d["tipo"] == "lote_venta"
        assert d["tono"] == "emotivo"
        assert d["nicho"] == ["general"]
        assert isinstance(d, dict)

    def test_defaults(self):
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


# ===== _tonos_por_tipo =====


class TestTonosPorTipo:
    def setup_method(self):
        studio = MagicMock()
        self.cv = CaptionVariants(studio)

    def test_lote_venta(self):
        tonos = self.cv._tonos_por_tipo("lote_venta")
        assert "emotivo" in tonos
        assert "practico" in tonos
        assert "inversion" in tonos
        assert "premium" in tonos

    def test_country(self):
        tonos = self.cv._tonos_por_tipo("country")
        assert "premium" in tonos
        assert "familia" in tonos

    def test_campo(self):
        tonos = self.cv._tonos_por_tipo("campo")
        assert "inversion" in tonos
        assert "productor" in tonos

    def test_tipo_desconocido(self):
        tonos = self.cv._tonos_por_tipo("tipo_inventado")
        assert tonos == ["emotivo"]

    def test_tipos_existentes(self):
        tipos_conocidos = [
            "lote_venta", "country", "campo", "preventa_loteo",
            "lote_periurbano", "testimonial_cliente", "preguntas_frecuentes",
            "campo_productivo", "obra_avance_semanal", "reel_hook_corto",
        ]
        for tipo in tipos_conocidos:
            tonos = self.cv._tonos_por_tipo(tipo)
            assert len(tonos) > 0


# ===== _nichos_por_tipo =====


class TestNichosPorTipo:
    def setup_method(self):
        studio = MagicMock()
        self.cv = CaptionVariants(studio)

    def test_lote_venta(self):
        nichos = self.cv._nichos_por_tipo("lote_venta")
        assert "general" in nichos
        assert "campo" in nichos
        assert "inversion" in nichos

    def test_country(self):
        nichos = self.cv._nichos_por_tipo("country")
        assert "country" in nichos

    def test_tipo_desconocido(self):
        nichos = self.cv._nichos_por_tipo("xxx")
        assert nichos == ["general"]


# ===== generar =====


class TestGenerar:
    def _make_cv(self):
        studio = MagicMock()
        return CaptionVariants(studio)

    def test_generar_lote_venta(self):
        cv = self._make_cv()
        cv.studio.post.post_lote_venta.return_value = {
            "caption": "Caption test",
            "hashtags": ["#lote"],
            "caption_completo": "Caption test\n\n#lote",
            "tema": "5 ha en Cañuelas",
        }
        variantes = cv.generar(
            tipo="lote_venta",
            n=3,
            tonos=["emotivo", "practico", "inversion"],
            municipio="Cañuelas",
        )
        assert len(variantes) == 3
        assert variantes[0].tono == "emotivo"
        assert variantes[1].tono == "practico"
        assert variantes[2].tono == "inversion"

    def test_generar_tipo_no_soportado(self):
        cv = self._make_cv()
        variantes = cv.generar(tipo="tipo_falso", n=1)
        assert len(variantes) == 1
        assert "ERROR" in variantes[0].caption or variantes[0].caption != ""

    def test_generar_n_mayor_que_tonos(self):
        cv = self._make_cv()
        cv.studio.post.post_lote_venta.return_value = {
            "caption": "ok",
            "hashtags": [],
            "caption_completo": "ok",
            "tema": "test",
        }
        variantes = cv.generar(
            tipo="lote_venta",
            n=5,
            tonos=["emotivo"],
        )
        assert len(variantes) == 5

    def test_generar_default_tonos(self):
        cv = self._make_cv()
        cv.studio.post.post_lote_venta.return_value = {
            "caption": "ok",
            "hashtags": [],
            "caption_completo": "ok",
            "tema": "test",
        }
        variantes = cv.generar(tipo="lote_venta", n=2)
        assert len(variantes) == 2
        assert variantes[0].tipo == "lote_venta"

    def test_generar_factory_excepcion(self):
        cv = self._make_cv()
        cv.studio.post.post_lote_venta.side_effect = RuntimeError("fail")
        variantes = cv.generar(tipo="lote_venta", n=1)
        assert len(variantes) == 1
        assert "ERROR" in variantes[0].caption_completo

    def test_variantes_tienen_ids(self):
        cv = self._make_cv()
        cv.studio.post.post_lote_venta.return_value = {
            "caption": "ok",
            "hashtags": [],
            "caption_completo": "ok",
            "tema": "test",
        }
        variantes = cv.generar(tipo="lote_venta", n=3, tonos=["a", "b", "c"])
        for i, v in enumerate(variantes, 1):
            assert v.variante_id.startswith(f"v{i}_")


# ===== mejor_caption_para_publicar =====


class TestMejorCaption:
    def _make_variantes(self):
        return [
            VarianteCaption(
                variante_id="v1_emotivo", tipo="lote_venta", tono="emotivo",
                nicho=["general"], tema="t", caption="Corto", hashtags=[],
                caption_completo="Corto",
            ),
            VarianteCaption(
                variante_id="v2_premium", tipo="lote_venta", tono="premium",
                nicho=["campo"], tema="t", caption="Largo " * 100, hashtags=[],
                caption_completo="Largo " * 100,
            ),
            VarianteCaption(
                variante_id="v3_inversion", tipo="lote_venta", tono="inversion",
                nicho=["inversion"], tema="t", caption="Mediano", hashtags=[],
                caption_completo="Mediano",
            ),
        ]

    def test_sin_criterios(self):
        cv = CaptionVariants(MagicMock())
        variantes = self._make_variantes()
        mejor = cv.mejor_caption_para_publicar(variantes)
        assert mejor == variantes[0]

    def test_max_caracteres(self):
        cv = CaptionVariants(MagicMock())
        variantes = self._make_variantes()
        mejor = cv.mejor_caption_para_publicar(variantes, {"max_caracteres": 20})
        assert mejor.variante_id == "v1_emotivo"

    def test_tono_preferido(self):
        cv = CaptionVariants(MagicMock())
        variantes = self._make_variantes()
        mejor = cv.mejor_caption_para_publicar(
            variantes, {"tono_preferido": ["inversion", "emotivo"]}
        )
        assert mejor.tono == "inversion"

    def test_nicho_preferido(self):
        cv = CaptionVariants(MagicMock())
        variantes = self._make_variantes()
        mejor = cv.mejor_caption_para_publicar(
            variantes, {"nicho_preferido": "campo"}
        )
        assert "campo" in mejor.nicho

    def test_criterios_combinados(self):
        cv = CaptionVariants(MagicMock())
        variantes = self._make_variantes()
        mejor = cv.mejor_caption_para_publicar(
            variantes,
            {"tono_preferido": ["emotivo", "premium"], "max_caracteres": 20},
        )
        assert mejor.tono == "emotivo"

    def test_lista_vacia_devuelve_primera(self):
        cv = CaptionVariants(MagicMock())
        variantes = self._make_variantes()
        mejor = cv.mejor_caption_para_publicar(variantes, {"max_caracteres": 5})
        assert mejor == variantes[0]


# ===== guardar =====


class TestGuardar:
    def test_guardar_sin_proyecto(self, tmp_path):
        studio = MagicMock()
        cv = CaptionVariants(studio)
        variantes = [
            VarianteCaption(
                variante_id="v1", tipo="lote_venta", tono="emotivo",
                nicho=[], tema="t", caption="c", hashtags=[],
                caption_completo="c",
            ),
        ]

        with patch("caption_variants.ROOT", tmp_path):
            result = cv.guardar(variantes, nombre="test_variantes")

        assert result.exists()
        json_file = result / "test_variantes.json"
        txt_file = result / "test_variantes.txt"
        assert json_file.exists()
        assert txt_file.exists()

    def test_guardar_con_proyecto(self, tmp_path):
        studio = MagicMock()
        cv = CaptionVariants(studio)
        variantes = [
            VarianteCaption(
                variante_id="v1", tipo="lote_venta", tono="emotivo",
                nicho=[], tema="t", caption="c", hashtags=[],
                caption_completo="c",
            ),
        ]

        with patch("caption_variants.ROOT", tmp_path):
            result = cv.guardar(variantes, proyecto="mi-proyecto")

        expected_dir = tmp_path / "inmuebles" / "lotes" / "mi-proyecto" / "variantes"
        assert result == expected_dir
        assert (result).exists()

    def test_guardar_nombre_auto(self, tmp_path):
        studio = MagicMock()
        cv = CaptionVariants(studio)
        variantes = [
            VarianteCaption(
                variante_id="v1", tipo="country", tono="premium",
                nicho=[], tema="t", caption="c", hashtags=[],
                caption_completo="c",
            ),
        ]

        with patch("caption_variants.ROOT", tmp_path):
            result = cv.guardar(variantes)

        files = list(result.glob("variantes_country_*.json"))
        assert len(files) == 1

    def test_guardar_contenido_json(self, tmp_path):
        studio = MagicMock()
        cv = CaptionVariants(studio)
        variantes = [
            VarianteCaption(
                variante_id="v1", tipo="lote_venta", tono="emotivo",
                nicho=["general"], tema="5 ha", caption="cap", hashtags=["#lote"],
                caption_completo="cap\n\n#lote",
            ),
        ]

        with patch("caption_variants.ROOT", tmp_path):
            result = cv.guardar(variantes, nombre="check_json")

        data = json.loads((result / "check_json.json").read_text())
        assert data["tipo"] == "lote_venta"
        assert data["n_variantes"] == 1
        assert data["variantes"][0]["variante_id"] == "v1"

    def test_guardar_contenido_txt(self, tmp_path):
        studio = MagicMock()
        cv = CaptionVariants(studio)
        variantes = [
            VarianteCaption(
                variante_id="v1", tipo="lote_venta", tono="emotivo",
                nicho=[], tema="t", caption="c", hashtags=[],
                caption_completo="caption completo aca",
            ),
        ]

        with patch("caption_variants.ROOT", tmp_path):
            result = cv.guardar(variantes, nombre="check_txt")

        txt = (result / "check_txt.txt").read_text()
        assert "VARIANTE v1" in txt
        assert "caption completo aca" in txt
