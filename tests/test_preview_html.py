"""Tests del modulo preview_html.py.

Cubre:
  - PreviewConfig dataclass
  - _color_para_slide, _color_para_pla, _html_escape
  - PreviewHTML.carrusel: genera HTML de carrusel con slides, caption, hashtags
  - PreviewHTML.post: genera HTML de post simple con/sin imagen
  - Diferentes tipos de slides: placeholder_foto, portada, prompt
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from preview_html import (
    PALETA_PLACEHOLDERS,
    PreviewConfig,
    PreviewHTML,
    _color_para_pla,
    _color_para_slide,
    _html_escape,
)

# ===== Helpers =====


class TestHelpers:
    def test_html_escape_normal(self):
        assert _html_escape("hola") == "hola"

    def test_html_escape_tags(self):
        assert _html_escape("<b>") == "&lt;b&gt;"

    def test_html_escape_ampersand(self):
        assert _html_escape("a & b") == "a &amp; b"

    def test_html_escape_vacio(self):
        assert _html_escape("") == ""
        assert _html_escape(None) == ""

    def test_color_para_slide(self):
        bg, fg = _color_para_slide(0)
        assert bg.startswith("#")
        assert fg.startswith("#")

    def test_color_para_slide_wrap_around(self):
        bg1, _ = _color_para_slide(0)
        bg2, _ = _color_para_slide(len(PALETA_PLACEHOLDERS))
        assert bg1 == bg2

    def test_color_para_pla(self):
        bg, fg = _color_para_pla(0)
        assert bg.startswith("#")


# ===== PreviewConfig =====


class TestPreviewConfig:
    def test_defaults(self):
        c = PreviewConfig()
        assert c.ancho_slide_px == 540
        assert c.alto_slide_px == 675
        assert c.color_fondo == "#fafafa"
        assert c.logo_emoji == "🌾"


# ===== PreviewHTML.carrusel =====


class TestPreviewHTMLCarrusel:
    def _make_carrusel(self, slides_data=None):
        slides = []
        if slides_data is None:
            slides_data = [
                {
                    "numero": 1,
                    "tipo": "portada",
                    "descripcion": "Portada",
                    "prompt": "",
                    "texto_overlay": "Hola",
                    "metadata": {},
                },
                {
                    "numero": 2,
                    "tipo": "beneficio",
                    "descripcion": "Beneficio",
                    "prompt": "prompt aqui",
                    "texto_overlay": "Beneficio",
                    "metadata": {},
                },
            ]
        for s in slides_data:
            mock_slide = MagicMock()
            mock_slide.numero = s["numero"]
            mock_slide.tipo = s["tipo"]
            mock_slide.descripcion = s["descripcion"]
            mock_slide.prompt = s["prompt"]
            mock_slide.texto_overlay = s["texto_overlay"]
            mock_slide.metadata = s.get("metadata", {})
            slides.append(mock_slide)

        mock_carrusel = MagicMock()
        mock_carrusel.slides = slides
        mock_carrusel.tema = "Test Carrusel"
        mock_carrusel.tipo = "lote_venta"
        mock_carrusel.municipio = "Cañuelas"
        mock_carrusel.tono = "emotivo"
        mock_carrusel.caption_narrativo = "Caption de prueba"
        mock_carrusel.hashtags = ["#lote", "#venta"]
        mock_carrusel.metadata = {}
        return mock_carrusel

    def test_genera_html(self, tmp_path):
        preview = PreviewHTML()
        carrusel = self._make_carrusel()
        html_path = preview.carrusel(carrusel, tmp_path / "preview.html")
        assert html_path.exists()
        content = html_path.read_text()
        assert "Test Carrusel" in content
        assert "Caption de prueba" in content
        assert "#lote" in content

    def test_dos_slides(self, tmp_path):
        preview = PreviewHTML()
        carrusel = self._make_carrusel()
        html_path = preview.carrusel(carrusel, tmp_path / "preview.html")
        content = html_path.read_text()
        assert content.count('class="slide"') == 2

    def test_slide_con_prompt(self, tmp_path):
        preview = PreviewHTML()
        carrusel = self._make_carrusel(
            [
                {
                    "numero": 1,
                    "tipo": "beneficio",
                    "descripcion": "X",
                    "prompt": "mi prompt SDXL largo",
                    "texto_overlay": "Y",
                    "metadata": {},
                },
            ]
        )
        html_path = preview.carrusel(carrusel, tmp_path / "preview.html")
        content = html_path.read_text()
        assert "mi prompt SDXL largo" in content

    def test_slide_placeholder_foto(self, tmp_path):
        preview = PreviewHTML()
        slides_data = [
            {
                "numero": 1,
                "tipo": "placeholder_foto",
                "descripcion": "Foto antes",
                "prompt": "",
                "texto_overlay": "Antes",
                "metadata": {"placeholder_foto_path": "/path/foto.jpg"},
            },
        ]
        carrusel = self._make_carrusel(slides_data)
        html_path = preview.carrusel(carrusel, tmp_path / "preview.html")
        content = html_path.read_text()
        assert "/path/foto.jpg" in content

    def test_warning_placeholder(self, tmp_path):
        preview = PreviewHTML()
        slides_data = [
            {
                "numero": 1,
                "tipo": "placeholder_foto",
                "descripcion": "X",
                "prompt": "",
                "texto_overlay": "Y",
                "metadata": {},
            },
        ]
        carrusel = self._make_carrusel(slides_data)
        html_path = preview.carrusel(carrusel, tmp_path / "preview.html")
        content = html_path.read_text()
        assert "placeholder" in content.lower()

    def test_navegacion_js(self, tmp_path):
        preview = PreviewHTML()
        carrusel = self._make_carrusel()
        html_path = preview.carrusel(carrusel, tmp_path / "preview.html")
        content = html_path.read_text()
        assert "function irASlide" in content
        assert "function siguiente" in content
        assert "function anterior" in content

    def test_crea_directorio(self, tmp_path):
        preview = PreviewHTML()
        carrusel = self._make_carrusel()
        html_path = preview.carrusel(carrusel, tmp_path / "subdir" / "preview.html")
        assert html_path.exists()


# ===== PreviewHTML.post =====


class TestPreviewHTMLPost:
    def test_genera_html_post(self, tmp_path):
        preview = PreviewHTML()
        html_path = preview.post(
            tema="5 ha en Cañuelas",
            caption="Caption test",
            hashtags=["#lote"],
            ruta_salida=tmp_path / "post.html",
        )
        assert html_path.exists()
        content = html_path.read_text()
        assert "5 ha en Cañuelas" in content
        assert "Caption test" in content
        assert "#lote" in content

    def test_post_con_imagen(self, tmp_path):
        img = tmp_path / "foto.jpg"
        img.write_bytes(b"\xff\xd8\xff\xe0")

        preview = PreviewHTML()
        html_path = preview.post(
            tema="Test",
            caption="Caption",
            hashtags=[],
            ruta_imagen=img,
            ruta_salida=tmp_path / "post.html",
        )
        content = html_path.read_text()
        assert "file://" in content

    def test_post_sin_imagen(self, tmp_path):
        preview = PreviewHTML()
        html_path = preview.post(
            tema="Test",
            caption="Caption",
            hashtags=[],
            ruta_salida=tmp_path / "post.html",
        )
        content = html_path.read_text()
        assert "Imagen no generada" in content

    def test_post_con_metadata(self, tmp_path):
        preview = PreviewHTML()
        html_path = preview.post(
            tema="Test",
            caption="Caption",
            hashtags=[],
            metadata={"municipio": "Cañuelas", "tono": "emotivo"},
            ruta_salida=tmp_path / "post.html",
        )
        content = html_path.read_text()
        assert "Cañuelas" in content

    def test_post_sin_metadata(self, tmp_path):
        preview = PreviewHTML()
        html_path = preview.post(
            tema="Test",
            caption="Caption",
            hashtags=[],
            ruta_salida=tmp_path / "post.html",
        )
        content = html_path.read_text()
        assert "AMBA" in content

    def test_post_crea_directorio(self, tmp_path):
        preview = PreviewHTML()
        html_path = preview.post(
            tema="T",
            caption="C",
            hashtags=[],
            ruta_salida=tmp_path / "sub" / "post.html",
        )
        assert html_path.exists()

    def test_post_self_contained(self, tmp_path):
        preview = PreviewHTML()
        html_path = preview.post(
            tema="T",
            caption="C",
            hashtags=[],
            ruta_salida=tmp_path / "post.html",
        )
        content = html_path.read_text()
        assert "<!DOCTYPE html>" in content
        assert "</html>" in content


# ===== PreviewHTML con config custom =====


class TestPreviewHTMLCustomConfig:
    def test_config_custom(self, tmp_path):
        config = PreviewConfig(ancho_slide_px=800, logo_emoji="🏡")
        preview = PreviewHTML(config=config)
        assert preview.config.ancho_slide_px == 800
        assert preview.config.logo_emoji == "🏡"
