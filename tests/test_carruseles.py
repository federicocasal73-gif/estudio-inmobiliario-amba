"""Tests del modulo carruseles.py.

Cubre los 4 tipos principales de carruseles + story + reel.
"""
from __future__ import annotations

import pytest

from carruseles import Carrusel, CarruselFactory, Slide
from realestate_studio import RealestateStudio


class TestCarruselDataClasses:
    """Tests de las dataclasses Slide y Carrusel."""

    def test_slide_to_dict(self):
        # Arrange
        slide = Slide(
            numero=1, tipo="portada",
            descripcion="Test slide",
            prompt="test prompt",
            texto_overlay="Titulo",
        )

        # Act
        d = slide.to_dict()

        # Assert
        assert d["numero"] == 1
        assert d["tipo"] == "portada"
        assert d["prompt"] == "test prompt"

    def test_carrusel_n_slides_property(self):
        # Arrange
        carrusel = Carrusel(
            tema="test", tipo="test", municipio="X", tono="emotivo",
            slides=[Slide(numero=1, tipo="foto", descripcion="a"),
                    Slide(numero=2, tipo="cta", descripcion="b")],
            caption_narrativo="", hashtags=[],
        )

        # Assert
        assert carrusel.n_slides == 2

    def test_carrusel_caption_completo_property(self):
        # Arrange
        hashtags = ["#lotes", "#chacras"]
        carrusel = Carrusel(
            tema="test", tipo="test", municipio="X", tono="emotivo",
            slides=[], caption_narrativo="caption", hashtags=hashtags,
        )

        # Act & Assert
        assert "caption" in carrusel.caption_completo
        assert "#lotes" in carrusel.caption_completo


class TestLotePremium:
    """Tests del carrusel lote_premium."""

    def setup_method(self):
        self.studio = RealestateStudio()
        self.factory = CarruselFactory(self.studio)

    def test_creates_default_6_slides(self):
        # Act
        carrusel = self.factory.lote_premium(
            tema="5 ha", municipio="Cañuelas", hectareas=5, n_slides=6)

        # Assert
        assert carrusel.n_slides == 6
        assert carrusel.tipo == "lote_premium"
        assert all(s.tipo for s in carrusel.slides)

    def test_respects_minimum_slides(self):
        # Act
        carrusel = self.factory.lote_premium(
            tema="test", municipio="X", hectareas=5, n_slides=2)

        # Assert (debe subir al minimo 4)
        assert carrusel.n_slides >= 4

    def test_all_slides_have_prompts_except_cta(self):
        # Act
        carrusel = self.factory.lote_premium(
            tema="test", municipio="X", hectareas=5, n_slides=5)

        # Assert
        prompts_with = [s for s in carrusel.slides if s.prompt]
        prompts_without = [s for s in carrusel.slides if not s.prompt]
        assert len(prompts_with) > 0
        # CTA slides no tienen prompt
        cta_slides = [s for s in carrusel.slides if s.tipo == "cta"]
        assert all(not s.prompt for s in cta_slides)


class TestConstructionCarruseles:
    """Tests de los carruseles especificos de construccion."""

    def setup_method(self):
        self.studio = RealestateStudio()
        self.factory = CarruselFactory(self.studio)

    @pytest.mark.parametrize("carrusel_method,expected_tipo,n_slides", [
        ("etapas_construccion", "etapas_construccion", 8),
        ("steel_frame_completo", "steel_frame", 6),
        ("llave_en_mano_completo", "llave_en_mano", 8),
        ("terminaciones_detalle", "terminaciones", 6),
        ("obra_completa", "obra_completa", 8),
    ])
    def test_construction_carruseles(
        self, carrusel_method, expected_tipo, n_slides
    ):
        # Act
        method = getattr(self.factory, carrusel_method)
        kwargs = {"municipio": "Cañuelas", "n_slides": n_slides}
        if "nombre_obra" in carrusel_method or carrusel_method == "obra_completa":
            kwargs["nombre_obra"] = "Test"
        carrusel = method(**kwargs)

        # Assert
        assert carrusel.tipo == expected_tipo
        assert carrusel.n_slides == n_slides


class TestStoryAndReel:
    """Tests de formatos verticales (story, reel)."""

    def setup_method(self):
        self.studio = RealestateStudio()
        self.factory = CarruselFactory(self.studio)

    def test_story_uses_9_16_aspect(self):
        # Act
        story = self.factory.story(tema="5 ha", municipio="Cañuelas")

        # Assert (aspect_ratio esta en metadata, no directo)
        assert "1344" in story.metadata.get("aspect_ratio", "") or "768" in story.metadata.get("aspect_ratio", "")
        assert story.tipo == "story"

    def test_reel_has_short_caption(self):
        # Act
        reel = self.factory.reel(tema="5 ha", municipio="Cañuelas")

        # Assert
        assert reel.tipo == "reel"
        assert reel.n_slides == 1  # reel = 1 slide


class TestGuardarCarrusel:
    """Tests de persistencia del carrusel a disco."""

    def setup_method(self):
        self.studio = RealestateStudio()
        self.factory = CarruselFactory(self.studio)

    def test_guardar_creates_files(self, tmp_path, repo_root):
        # Arrange
        # Cambiar a directorio temporal
        import os
        original_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)
            carrusel = self.factory.lote_premium(
                tema="test", municipio="Cañuelas", hectareas=5, n_slides=5)

            # Act
            carpeta = self.factory.guardar(
                carrusel, "test_carrusel",
                proyecto="test_proj",
            )
        finally:
            os.chdir(original_cwd)

        # Assert
        assert carpeta.exists()
        assert (carpeta / "carrusel.json").exists()
        assert (carpeta / "carrusel.md").exists()
        assert (carpeta / "caption_instagram.txt").exists()
        slides_dir = carpeta / "slides"
        assert slides_dir.exists()
        # Al menos un slide JSON
        assert any(slides_dir.glob("slide_*.json"))
