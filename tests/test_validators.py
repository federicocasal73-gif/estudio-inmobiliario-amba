"""Tests para validators.py - Validaciones centralizadas."""

from __future__ import annotations

from pathlib import Path

import pytest

from validators import (
    ResultadoValidacion,
    validate_caption,
    validate_hashtags,
    validate_municipio,
    validate_hectareas,
    validate_carrusel,
    validate_imagen,
    validate_post,
    safe_post,
    IG_CAPTION_MAX_CHARS,
    IG_HASHTAGS_MAX,
    IG_CARRUSEL_MIN,
    IG_CARRUSEL_MAX,
)


class TestResultadoValidacion:
    def test_ok_default(self):
        r = ResultadoValidacion(ok=True)
        assert r.ok is True
        assert r.errores == []
        assert r.advertencias == []
        assert r.metadata == {}

    def test_to_dict(self):
        r = ResultadoValidacion(ok=True)
        d = r.to_dict()
        assert d["ok"] is True
        assert d["errores"] == []
        assert d["advertencias"] == []
        assert d["metadata"] == {}

    def test_agregar_error(self):
        r = ResultadoValidacion(ok=True)
        r.agregar_error("error 1")
        assert r.ok is False
        assert "error 1" in r.errores

    def test_agregar_warning(self):
        r = ResultadoValidacion(ok=True)
        r.agregar_warning("warn 1")
        assert r.ok is True
        assert "warn 1" in r.advertencias


class TestValidateCaption:
    def test_ok_normal(self):
        r = validate_caption("Hola mundo")
        assert r.ok is True
        assert r.metadata["longitud"] == 10

    def test_caption_none(self):
        r = validate_caption(None)
        assert r.ok is False
        assert any("None" in e for e in r.errores)

    def test_caption_no_string(self):
        r = validate_caption(123)
        assert r.ok is False

    def test_caption_vacio(self):
        r = validate_caption("")
        assert r.ok is False

    def test_caption_demasiado_largo(self):
        r = validate_caption("a" * (IG_CAPTION_MAX_CHARS + 1))
        assert r.ok is False
        assert any("demasiado largo" in e for e in r.errores)

    def test_caption_cerca_del_limite(self):
        r = validate_caption("a" * int(IG_CAPTION_MAX_CHARS * 0.95))
        assert r.ok is True
        assert len(r.advertencias) > 0

    def test_caption_en_limite(self):
        r = validate_caption("a" * int(IG_CAPTION_MAX_CHARS * 0.89))
        assert r.ok is True
        assert len(r.advertencias) == 0


class TestValidateHashtags:
    def test_ok_hashtags(self):
        r = validate_hashtags(["#lotes", "#chacras", "#campo"])
        assert r.ok is True
        assert r.metadata["cantidad"] == 3

    def test_hashtags_none(self):
        r = validate_hashtags(None)
        assert r.ok is True
        assert len(r.advertencias) > 0

    def test_hashtags_no_lista(self):
        r = validate_hashtags("not a list")
        assert r.ok is False

    def test_hashtags_vacio(self):
        r = validate_hashtags([])
        assert r.ok is True
        assert len(r.advertencias) > 0

    def test_hashtags_demasiados(self):
        r = validate_hashtags([f"#tag{i}" for i in range(IG_HASHTAGS_MAX + 1)])
        assert r.ok is False

    def test_hashtags_formato_invalido(self):
        r = validate_hashtags(["#lotes", "sin_hash", "#con espacio"])
        assert r.ok is False

    def test_hashtags_blacklist(self):
        r = validate_hashtags(["#lotes", "#chacras"], blacklist=["chacras"])
        assert r.ok is False
        assert any("blacklist" in e for e in r.errores)

    def test_hashtags_must_include_falta(self):
        r = validate_hashtags(
            ["#lotes"],
            must_include=["#campo"],
        )
        assert len(r.advertencias) > 0

    def test_hashtags_must_include_ok(self):
        r = validate_hashtags(
            ["#lotes", "#campo"],
            must_include=["campo"],
        )
        assert len(r.advertencias) == 0


class TestValidateMunicipio:
    def test_ok_municipio(self):
        r = validate_municipio("Canuelas")
        assert r.ok is True
        assert r.metadata.get("en_lista") is True

    def test_municipio_vacio(self):
        r = validate_municipio("")
        assert r.ok is False

    def test_municipio_no_amba(self):
        r = validate_municipio("Mar del Plata")
        assert r.ok is True
        assert any("no esta" in w for w in r.advertencias)

    def test_municipio_no_amba_estricto(self):
        r = validate_municipio("Mar del Plata", estricto=True)
        assert r.ok is False

    def test_municipio_con_acentos(self):
        r = validate_municipio("Cañuelas")
        assert r.ok is True

    def test_municipio_zona_norte(self):
        r = validate_municipio("Pilar")
        assert r.ok is True

    def test_municipio_zona_oeste(self):
        r = validate_municipio("Moreno")
        assert r.ok is True

    def test_municipio_zona_sur(self):
        r = validate_municipio("Lobos")
        assert r.ok is True


class TestValidateHectareas:
    def test_ok_hectareas(self):
        r = validate_hectareas(5)
        assert r.ok is True
        assert r.metadata["hectareas"] == 5.0

    def test_hectareas_cero(self):
        r = validate_hectareas(0)
        assert r.ok is False

    def test_hectareas_negativas(self):
        r = validate_hectareas(-1)
        assert r.ok is False

    def test_hectareas_muy_grandes(self):
        r = validate_hectareas(5000)
        assert r.ok is True
        assert len(r.advertencias) > 0

    def test_hectareas_string_invalido(self):
        r = validate_hectareas("abc")
        assert r.ok is False

    def test_hectareas_none(self):
        r = validate_hectareas(None)
        assert r.ok is False

    def test_hectareas_float(self):
        r = validate_hectareas(5.5)
        assert r.ok is True
        assert r.metadata["hectareas"] == 5.5


class TestValidateCarrusel:
    def test_ok_carrusel(self, tmp_path):
        files = []
        for i in range(3):
            f = tmp_path / f"img{i}.jpg"
            f.write_bytes(b"\x00" * 1024)
            files.append(str(f))
        r = validate_carrusel(files)
        assert r.ok is True

    def test_carrusel_no_lista(self):
        r = validate_carrusel("not a list")
        assert r.ok is False

    def test_carrusel_pocas_imagenes(self, tmp_path):
        f = tmp_path / "img.jpg"
        f.write_bytes(b"\x00" * 1024)
        r = validate_carrusel([str(f)])
        assert r.ok is False

    def test_carrusel_demasiadas(self, tmp_path):
        files = []
        for i in range(IG_CARRUSEL_MAX + 1):
            f = tmp_path / f"img{i}.jpg"
            f.write_bytes(b"\x00" * 1024)
            files.append(str(f))
        r = validate_carrusel(files)
        assert r.ok is False

    def test_carrusel_imagen_no_existe(self, tmp_path):
        r = validate_carrusel(["/nonexistent/img.jpg"])
        assert r.ok is False

    def test_carrusel_imagen_grande(self, tmp_path):
        f = tmp_path / "big.jpg"
        f.write_bytes(b"\x00" * (9 * 1024 * 1024))
        r = validate_carrusel([str(f), str(f)])
        assert r.ok is False


class TestValidateImagen:
    def test_ok_imagen(self, tmp_path):
        f = tmp_path / "img.jpg"
        f.write_bytes(b"\x00" * 1024)
        r = validate_imagen(f)
        assert r.ok is True

    def test_imagen_no_existe(self):
        r = validate_imagen("/nonexistent/img.jpg")
        assert r.ok is False

    def test_imagen_grande(self, tmp_path):
        f = tmp_path / "big.jpg"
        f.write_bytes(b"\x00" * (9 * 1024 * 1024))
        r = validate_imagen(f)
        assert r.ok is False

    def test_imagen_extension_rara(self, tmp_path):
        f = tmp_path / "img.bmp"
        f.write_bytes(b"\x00" * 1024)
        r = validate_imagen(f)
        assert r.ok is True
        assert len(r.advertencias) > 0


class TestValidatePost:
    def test_ok_post(self):
        r = validate_post(
            caption="Hermosa chacra en Cañuelas",
            hashtags=["#lotes", "#chacras"],
            municipio="Canuelas",
            hectareas=5,
        )
        assert r.ok is True

    def test_post_caption_malo(self):
        r = validate_post(caption="")
        assert r.ok is False

    def test_post_con_blacklist(self):
        r = validate_post(
            caption="Test",
            hashtags=["#lotes", "#chacras"],
            hashtags_blacklist=["chacras"],
        )
        assert r.ok is False

    def test_post_con_estricto_municipio(self):
        r = validate_post(
            caption="Test",
            municipio="Mar del Plata",
            estricto_municipio=True,
        )
        assert r.ok is False

    def test_post_solo_caption(self):
        r = validate_post(caption="Solo caption")
        assert r.ok is True

    def test_post_con_hashtags_none(self):
        r = validate_post(caption="Test", hashtags=None)
        assert r.ok is True


class TestSafePost:
    def test_safe_post_agrega_validacion(self):
        post = {
            "caption_completo": "Test caption",
            "hashtags": ["#test"],
        }
        result = safe_post(post)
        assert "_validacion" in result
        assert result["_validacion"]["ok"] is True

    def test_safe_post_con_kwargs(self):
        post = {
            "caption_completo": "Test",
            "hashtags": ["#test"],
        }
        result = safe_post(post, municipio="Canuelas")
        assert "_validacion" in result


class TestDemoValidators:
    def test_demo(self):
        from validators import demo
        demo()

    def test_slug_municipio(self):
        from validators import _slug_municipio
        assert _slug_municipio("Cañuelas") == "canuelas"
        assert _slug_municipio("San Vicente") == "sanvicente"
        assert _slug_municipio("25 de Mayo") == "25demayo"

    def test_normalizar_municipio(self):
        from validators import _normalizar_municipio
        assert _normalizar_municipio("cañuelas") == "Canuelas"
        assert _normalizar_municipio("") == ""
