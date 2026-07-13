"""Tests de los verticales y posts del modulo realestate_studio.

Tests principales sobre la API publica del estudio:
- VerticalLotes.chacra_pampeana() y similares
- CaptionFactory.post_*()
"""
from __future__ import annotations

import pytest

from realestate_studio import RealestateStudio, VerticalLotes


class TestRealestateStudioInit:
    """Tests del constructor del orquestador principal."""

    def test_init_creates_all_verticals(self):
        # Act
        studio = RealestateStudio()

        # Assert
        assert isinstance(studio.lotes, VerticalLotes)
        assert studio.post is not None  # CaptionFactory
        assert studio.construccion is not None


class TestVerticalLotes:
    """Tests de las funciones de generacion de prompts rurales."""

    def setup_method(self):
        self.studio = RealestateStudio()
        self.lotes = self.studio.lotes

    def test_chacra_pampeana_generates_prompt(self):
        # Act
        req = self.lotes.chacra_pampeana(
            hectareas=5, municipio="Cañuelas", momento="atardecer")

        # Assert
        assert req.prompt
        assert "Cañuelas" in req.prompt or "pampas" in req.prompt.lower()
        assert "5" in req.prompt
        assert req.aspect_ratio

    def test_chacra_pampeana_metadata(self):
        # Act
        req = self.lotes.chacra_pampeana(
            hectareas=5, municipio="Cañuelas")

        # Assert
        assert req.metadata["tipo"] == "chacra"
        assert req.metadata["hectareas"] == 5
        assert req.metadata["municipio"] == "Cañuelas"

    @pytest.mark.parametrize("municipio", [
        "Cañuelas", "Pilar", "Escobar", "Mercedes", "Luján",
    ])
    def test_chacra_pampeana_with_various_municipios(self, municipio):
        # Act
        req = self.lotes.chacra_pampeana(hectareas=5, municipio=municipio)

        # Assert
        assert municipio in req.prompt or municipio.lower() in req.prompt.lower()
        # Acentos pueden quitarse, validar que el slug aparece

    def test_campo_grande_with_more_hectareas(self):
        # Act
        req = self.lotes.campo_grande(hectareas=300, municipio="Saladillo")

        # Assert
        assert req.prompt
        assert "300" in req.prompt
        assert "Saladillo" in req.prompt

    def test_lote_inversion_chico_uses_small_area(self):
        # Act
        req = self.lotes.lote_inversion_chico(
            metros_cuadrados=600, municipio="Pilar")

        # Assert
        assert "600" in req.prompt
        assert req.aspect_ratio


class TestCaptionFactory:
    """Tests del factory de captions y hashtags."""

    def setup_method(self):
        self.studio = RealestateStudio()
        self.post = self.studio.post

    def test_post_lote_venta_has_required_fields(self):
        # Act
        post = self.post.post_lote_venta(
            tema="5 ha en Cañuelas",
            municipio="Cañuelas",
            hectareas="5 ha",
            distancia_caba="65 km",
            tono="emotivo",
        )

        # Assert
        assert post["caption"]
        assert post["caption_completo"]
        assert isinstance(post["hashtags"], list)
        assert post["tono"] == "emotivo"

    def test_post_presupuesto_obra(self):
        # Act
        post = self.post.post_presupuesto_obra(
            zona="Cañuelas", metros_cuadrados=130,
        )

        # Assert
        assert "USD" in post["caption"]
        assert "130" in post["caption"] or "m²" in post["caption"]

    def test_post_etapas_obra_includes_8_default(self):
        # Act
        post = self.post.post_etapas_obra(metros_cuadrados=120)

        # Assert (el template usa emojis 1️⃣ 2️⃣ 3️⃣ en vez de "Etapa 1:")
        assert "1️⃣" in post["caption"]
        assert "8️⃣" in post["caption"] or "8 " in post["caption"] or "Etapa 8" in post["caption"]
        assert post["caption"] is not None

    @pytest.mark.parametrize("tono", ["emotivo", "inversion", "practico", "premium"])
    def test_post_lote_venta_with_all_tonos(self, tono):
        # Act
        post = self.post.post_lote_venta(
            tema="test", municipio="Cañuelas",
            hectareas="5", distancia_caba="65 km", tono=tono,
        )

        # Assert
        assert post["tono"] == tono
        assert post["caption"]


class TestHashtags:
    """Tests de hashtags con blacklist y must_include."""

    def setup_method(self):
        self.studio = RealestateStudio()
        self.post = self.studio.post

    def test_hashtags_basic(self):
        # Act
        tags = self.post.hashtags(["general"], "Cañuelas")

        # Assert
        assert isinstance(tags, list)
        assert len(tags) > 0

    def test_hashtags_with_blacklist(self):
        # Act
        tags = self.post.hashtags(["general"], "Cañuelas",
                                  blacklist=["#lotes"])

        # Assert (debe excluir solo "#lotes" exacto, no variaciones como "#lotesencanuelas")
        assert "#lotes" not in tags
        # Las variaciones pueden quedar, eso es por diseno

    def test_hashtags_with_must_include(self):
        # Act
        tags = self.post.hashtags(["general"], "Cañuelas",
                                  must_include=["#patrimonio"])

        # Assert
        assert "#patrimonio" in tags


class TestPostValidates:
    """Tests de integracion: posts que pasan por validators."""

    def setup_method(self):
        self.studio = RealestateStudio()
        self.post = self.studio.post

    def test_emotivo_caption_passes_2200_chars(self):
        # Act
        post = self.post.post_lote_venta(
            tema="5 ha en Cañuelas",
            municipio="Cañuelas",
            hectareas="5 ha",
            distancia_caba="65 km",
            tono="emotivo",
        )

        # Assert (caption completo <= 2200)
        assert len(post["caption_completo"]) <= 2200
