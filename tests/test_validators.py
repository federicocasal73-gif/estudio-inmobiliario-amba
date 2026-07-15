"""Tests del modulo de validacion (validators.py).

Cubre el patron principal del estudio: validar posts antes de publicar.
Siguiendo python-testing-patterns: parametrized + fixtures + edge cases.
"""

from __future__ import annotations

import pytest

from validators import (
    validate_caption,
    validate_hashtags,
    validate_hectareas,
    validate_municipio,
    validate_post,
)


class TestValidateCaption:
    """Tests de validacion de caption."""

    def test_valid_short_caption(self):
        # Arrange & Act
        result = validate_caption("Hola mundo")

        # Assert
        assert result.ok is True
        assert result.metadata["longitud"] == 10

    def test_empty_caption_fails(self):
        # Act
        result = validate_caption("")

        # Assert
        assert result.ok is False
        assert "vacio" in result.errores[0].lower()

    def test_caption_at_limit_succeeds(self):
        # Arrange
        text = "a" * 2200

        # Act
        result = validate_caption(text)

        # Assert
        assert result.ok is True

    def test_caption_over_limit_fails(self):
        # Arrange
        text = "a" * 2201

        # Act
        result = validate_caption(text)

        # Assert
        assert result.ok is False
        assert "2201" in result.errores[0]

    @pytest.mark.parametrize(
        "text,expected_ok",
        [
            ("", False),
            ("short", True),
            ("a" * 2199, True),  # borde
            ("a" * 2200, True),  # limite exacto
            ("a" * 2201, False),  # 1 mas del limite
            ("a" * 5000, False),  # mucho mas
        ],
    )
    def test_caption_length_parametrized(self, text: str, expected_ok: bool):
        # Act
        result = validate_caption(text)

        # Assert
        assert result.ok is expected_ok

    def test_caption_with_unicode_passes(self):
        # Arrange (emojis son 1 character cada uno en len() en Python)
        text = "🌾 Hermosa chacra 🏡 en Cañuelas" * 50

        # Act
        result = validate_caption(text)

        # Assert (puede pasar o fallar segun longitud, no crash)
        assert isinstance(result.ok, bool)


class TestValidateHashtags:
    """Tests de validacion de hashtags."""

    def test_valid_hashtags(self):
        # Act
        result = validate_hashtags(["#lotes", "#chacras"])

        # Assert
        assert result.ok is True

    def test_empty_list_warning(self):
        # Act
        result = validate_hashtags([])

        # Assert (warning no es error)
        assert result.ok is True
        assert len(result.advertencias) > 0

    def test_too_many_hashtags_fails(self):
        # Arrange
        tags = [f"#tag{i}" for i in range(31)]

        # Act
        result = validate_hashtags(tags)

        # Assert
        assert result.ok is False
        assert "31" in result.errores[0]

    def test_exactly_30_hashtags_ok(self):
        # Arrange (limite exacto)
        tags = [f"#tag{i}" for i in range(30)]

        # Act
        result = validate_hashtags(tags)

        # Assert
        assert result.ok is True

    def test_hashtag_without_hash_fails(self):
        # Act
        result = validate_hashtags(["lotes sin #"])

        # Assert
        assert result.ok is False

    def test_hashtag_with_space_fails(self):
        # Act
        result = validate_hashtags(["#lotes con espacio"])

        # Assert
        assert result.ok is False

    def test_blacklist_filtering(self):
        # Act
        result = validate_hashtags(
            ["#lotes", "#chacras"],
            blacklist=["chacras"],
        )

        # Assert
        assert result.ok is False
        assert any("#chacras" in e for e in result.errores)

    def test_must_include_presente(self):
        # Act
        result = validate_hashtags(
            ["#lotes", "#patrimonio"],
            must_include=["#patrimonio"],
        )

        # Assert
        assert result.ok is True

    def test_must_include_faltante_es_warning(self):
        # Act
        result = validate_hashtags(
            ["#lotes"],
            must_include=["#patrimonio"],
        )

        # Assert (warning, no error)
        assert result.ok is True
        assert len(result.advertencias) > 0


class TestValidateMunicipio:
    """Tests de validacion de municipio."""

    @pytest.mark.parametrize(
        "municipio,esperado_en_lista,esperado_ok",
        [
            ("Canuelas", True, True),
            ("Pilar", True, True),
            ("Escobar", True, True),
            ("Lujan", True, True),
            ("Lobos", True, True),
            ("Mar del Plata", False, True),  # warning, no error por default
            ("Buenos Aires", False, True),
            ("", None, False),  # vacio SI es error
        ],
    )
    def test_municipio_en_lista_o_warning(
        self, municipio: str, esperado_en_lista: bool | None, esperado_ok: bool
    ):
        # Act
        result = validate_municipio(municipio)

        # Assert
        assert result.ok is esperado_ok
        if esperado_en_lista is True:
            assert result.metadata.get("en_lista") is True
        elif esperado_en_lista is False:
            assert len(result.advertencias) > 0

    def test_estricto_falla_si_no_esta(self):
        # Act
        result = validate_municipio("Mar del Plata", estricto=True)

        # Assert
        assert result.ok is False


class TestValidateHectareas:
    """Tests de validacion de hectareas."""

    @pytest.mark.parametrize(
        "hectareas,esperado_ok",
        [
            (5, True),
            (0.5, True),
            (100, True),
            (0, False),
            (-1, False),
            (-5.5, False),
        ],
    )
    def test_hectareas_positivas(self, hectareas, esperado_ok):
        # Act
        result = validate_hectareas(hectareas)

        # Assert
        assert result.ok is esperado_ok

    def test_huge_hectareas_warning(self):
        # Act
        result = validate_hectareas(5000)

        # Assert (no falla pero avisa)
        assert result.ok is True
        assert len(result.advertencias) > 0


class TestValidatePost:
    """Tests del wrapper validate_post (caption + hashtags + municipio + ha)."""

    def test_valid_post(self, sample_post):
        # Act
        result = validate_post(
            caption=sample_post["caption_completo"],
            hashtags=sample_post["hashtags"],
            municipio=sample_post["municipio"],
            hectareas=5,
        )

        # Assert
        assert result.ok is True

    def test_post_with_invalid_caption(self):
        # Act
        result = validate_post(
            caption="",  # vacio
            hashtags=["#lotes"],
            municipio="Cañuelas",
            hectareas=5,
        )

        # Assert
        assert result.ok is False
        assert any("vacio" in e for e in result.errores)

    def test_post_with_invalid_hectareas(self):
        # Act
        result = validate_post(
            caption="texto valido",
            hashtags=["#lotes"],
            municipio="Cañuelas",
            hectareas=-1,
        )

        # Assert
        assert result.ok is False

    def test_post_with_blacklist_hashtag(self):
        # Act
        result = validate_post(
            caption="texto",
            hashtags=["#lotes", "#inversion"],
            hashtags_blacklist=["inversion"],
            municipio="Cañuelas",
            hectareas=5,
        )

        # Assert
        assert result.ok is False
