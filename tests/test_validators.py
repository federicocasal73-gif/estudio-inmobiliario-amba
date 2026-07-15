"""Tests del modulo validators.py.

Cubre:
  - ResultadoValidacion dataclass
  - _slug_municipio, _normalizar_municipio
  - validate_caption: None, string, vacio, largo, warning
  - validate_hashtags: None, formato, cantidad, blacklist, must_include
  - validate_municipio: AMBA, no AMBA, estricto
  - validate_hectareas: negativo, 0, >1000, valid
  - validate_carrusel: cantidad, archivos, tamano
  - validate_imagen: existe, tamano, extension
  - validate_post: composite, todos los sub-validators
  - safe_post: wrapper
"""

from __future__ import annotations

from pathlib import Path

import pytest

from validators import (
    IG_CAPTION_MAX_CHARS,
    IG_CARRUSEL_MAX,
    IG_CARRUSEL_MIN,
    IG_HASHTAGS_MAX,
    IG_IMAGE_MAX_MB,
    MUNICIPIOS_AMBA,
    ResultadoValidacion,
    _normalizar_municipio,
    _slug_municipio,
    safe_post,
    validate_caption,
    validate_carrusel,
    validate_hashtags,
    validate_hectareas,
    validate_imagen,
    validate_municipio,
    validate_post,
)

# ===== ResultadoValidacion =====


class TestResultadoValidacion:
    def test_ok_default(self):
        r = ResultadoValidacion(ok=True)
        assert r.ok is True
        assert r.errores == []
        assert r.advertencias == []
        assert r.metadata == {}

    def test_to_dict(self):
        r = ResultadoValidacion(ok=True, metadata={"longitud": 100})
        d = r.to_dict()
        assert d["ok"] is True
        assert d["metadata"]["longitud"] == 100

    def test_agregar_error(self):
        r = ResultadoValidacion(ok=True)
        r.agregar_error("algo fallo")
        assert r.ok is False
        assert "algo fallo" in r.errores

    def test_agregar_warning(self):
        r = ResultadoValidacion(ok=True)
        r.agregar_warning("cuidado")
        assert r.ok is True
        assert "cuidado" in r.advertencias

    def test_agregar_multiple_errors(self):
        r = ResultadoValidacion(ok=True)
        r.agregar_error("e1")
        r.agregar_error("e2")
        assert r.ok is False
        assert len(r.errores) == 2


# ===== Helpers =====


class TestSlugMunicipio:
    def test_canuelas(self):
        assert _slug_municipio("Cañuelas") == "canuelas"

    def test_lujan(self):
        assert _slug_municipio("Luján") == "lujan"

    def test_capilla_del_senor(self):
        assert _slug_municipio("Capilla del Senor") == "capilladelsenor"

    def test_exaltacion(self):
        assert _slug_municipio("Exaltacion de la Cruz") == "exaltaciondelacruz"

    def test_vacio(self):
        assert _slug_municipio("") == ""


class TestNormalizarMunicipio:
    def test_canuelas(self):
        result = _normalizar_municipio("canuelas")
        assert result == "Canuelas"

    def test_empty(self):
        assert _normalizar_municipio("") == ""


# ===== validate_caption =====


class TestValidateCaption:
    def test_caption_valido(self):
        r = validate_caption("Mi lote en Cañuelas")
        assert r.ok is True
        assert r.metadata["longitud"] == len("Mi lote en Cañuelas")

    def test_caption_vacio(self):
        r = validate_caption("")
        assert r.ok is False
        assert len(r.errores) > 0

    def test_caption_none(self):
        r = validate_caption(None)
        assert r.ok is False

    def test_caption_no_string(self):
        r = validate_caption(123)
        assert r.ok is False

    def test_caption_demasiado_largo(self):
        r = validate_caption("x" * (IG_CAPTION_MAX_CHARS + 1))
        assert r.ok is False

    def test_caption_limite_exacto(self):
        r = validate_caption("x" * IG_CAPTION_MAX_CHARS)
        assert r.ok is True

    def test_caption_warning_cerca_limite(self):
        r = validate_caption("x" * 1981)  # > 90% of 2200
        assert r.ok is True
        assert len(r.advertencias) > 0


# ===== validate_hashtags =====


class TestValidateHashtags:
    def test_hashtags_validos(self):
        r = validate_hashtags(["#lotes", "#campo"])
        assert r.ok is True
        assert r.metadata["cantidad"] == 2

    def test_hashtags_none(self):
        r = validate_hashtags(None)
        assert r.ok is True
        assert len(r.advertencias) > 0

    def test_hashtags_no_lista(self):
        r = validate_hashtags("#lotes")
        assert r.ok is False

    def test_hashtags_vacios(self):
        r = validate_hashtags([])
        assert r.ok is True
        assert len(r.advertencias) > 0

    def test_hashtags_demasiados(self):
        r = validate_hashtags([f"#tag{i}" for i in range(IG_HASHTAGS_MAX + 1)])
        assert r.ok is False

    def test_hashtags_limite_exacto(self):
        r = validate_hashtags([f"#tag{i}" for i in range(IG_HASHTAGS_MAX)])
        assert r.ok is True

    def test_hashtag_formato_invalido(self):
        r = validate_hashtags(["sin_hash"])
        assert r.ok is False

    def test_hashtag_con_espacio(self):
        r = validate_hashtags(["#lote grande"])
        assert r.ok is False

    def test_hashtag_underscore(self):
        r = validate_hashtags(["#lote_grande"])
        assert r.ok is True

    def test_hashtag_digitos(self):
        r = validate_hashtags(["#lote123"])
        assert r.ok is True

    def test_blacklist(self):
        r = validate_hashtags(
            ["#lotes", "#campo"],
            blacklist=["lotes"],
        )
        assert r.ok is False

    def test_blacklist_case_insensitive(self):
        r = validate_hashtags(
            ["#LOTES", "#campo"],
            blacklist=["LOTEs"],
        )
        assert r.ok is False

    def test_must_include_falta(self):
        r = validate_hashtags(
            ["#lotes"],
            must_include=["campo"],
        )
        assert r.ok is True
        assert len(r.advertencias) > 0

    def test_must_include_presente(self):
        r = validate_hashtags(
            ["#lotes", "#campo"],
            must_include=["campo"],
        )
        assert r.ok is True
        assert len(r.advertencias) == 0


# ===== validate_municipio =====


class TestValidateMunicipio:
    def test_municipio_en_lista(self):
        r = validate_municipio("Cañuelas")
        assert r.ok is True
        assert r.metadata["en_lista"] is True

    def test_municipio_no_en_lista(self):
        r = validate_municipio("Mar del Plata")
        assert r.ok is True
        assert len(r.advertencias) > 0

    def test_municipio_estricto_no_en_lista(self):
        r = validate_municipio("Cordoba", estricto=True)
        assert r.ok is False

    def test_municipio_vacio(self):
        r = validate_municipio("")
        assert r.ok is False

    def test_municipio_none(self):
        r = validate_municipio(None)
        assert r.ok is False

    def test_municipios_cubiertos(self):
        for m in MUNICIPIOS_AMBA:
            r = validate_municipio(m)
            assert r.ok is True, f"Fallo para municipio: {m}"


# ===== validate_hectareas =====


class TestValidateHectareas:
    def test_hectareas_validas(self):
        r = validate_hectareas(5)
        assert r.ok is True
        assert r.metadata["hectareas"] == 5.0

    def test_hectareas_0(self):
        r = validate_hectareas(0)
        assert r.ok is False

    def test_hectareas_negativas(self):
        r = validate_hectareas(-5)
        assert r.ok is False

    def test_hectareas_grandes_warning(self):
        r = validate_hectareas(1500)
        assert r.ok is True
        assert len(r.advertencias) > 0

    def test_hectareas_limite_exacto(self):
        r = validate_hectareas(1000)
        assert r.ok is True

    def test_hectareas_no_numerico(self):
        r = validate_hectareas("abc")
        assert r.ok is False

    def test_hectareas_float(self):
        r = validate_hectareas(5.5)
        assert r.ok is True
        assert r.metadata["hectareas"] == 5.5


# ===== validate_carrusel =====


class TestValidateCarrusel:
    def test_carrusel_valido(self, tmp_path):
        img1 = tmp_path / "img1.jpg"
        img2 = tmp_path / "img2.jpg"
        img1.write_bytes(b"\xff" * 100)
        img2.write_bytes(b"\xff" * 100)
        r = validate_carrusel([str(img1), str(img2)])
        assert r.ok is True

    def test_carrusel_no_lista(self):
        r = validate_carrusel("no_es_lista")
        assert r.ok is False

    def test_carrusel_muy_pocos(self, tmp_path):
        img = tmp_path / "img1.jpg"
        img.write_bytes(b"\xff" * 100)
        r = validate_carrusel([str(img)])
        assert r.ok is False

    def test_carrusel_muy_muchos(self, tmp_path):
        imgs = []
        for i in range(IG_CARRUSEL_MAX + 1):
            img = tmp_path / f"img{i}.jpg"
            img.write_bytes(b"\xff" * 100)
            imgs.append(str(img))
        r = validate_carrusel(imgs)
        assert r.ok is False

    def test_carrusel_limite_min(self, tmp_path):
        imgs = []
        for i in range(IG_CARRUSEL_MIN):
            img = tmp_path / f"img{i}.jpg"
            img.write_bytes(b"\xff" * 100)
            imgs.append(str(img))
        r = validate_carrusel(imgs)
        assert r.ok is True

    def test_carrusel_limite_max(self, tmp_path):
        imgs = []
        for i in range(IG_CARRUSEL_MAX):
            img = tmp_path / f"img{i}.jpg"
            img.write_bytes(b"\xff" * 100)
            imgs.append(str(img))
        r = validate_carrusel(imgs)
        assert r.ok is True

    def test_carrusel_archivo_no_existe(self, tmp_path):
        r = validate_carrusel(["/no/existe/a.jpg", "/no/existe/b.jpg"])
        assert r.ok is False

    def test_carrusel_imagen_grande(self, tmp_path):
        img1 = tmp_path / "ok.jpg"
        img2 = tmp_path / "big.jpg"
        img1.write_bytes(b"\xff" * 100)
        img2.write_bytes(b"\xff" * (IG_IMAGE_MAX_MB * 1024 * 1024 + 1))
        r = validate_carrusel([str(img1), str(img2)])
        assert r.ok is False

    def test_carrusel_imagen_limite_exacto(self, tmp_path):
        img1 = tmp_path / "ok.jpg"
        img2 = tmp_path / "exact.jpg"
        img1.write_bytes(b"\xff" * 100)
        img2.write_bytes(b"\xff" * (IG_IMAGE_MAX_MB * 1024 * 1024))
        r = validate_carrusel([str(img1), str(img2)])
        assert r.ok is True


# ===== validate_imagen =====


class TestValidateImagen:
    def test_imagen_valida(self, tmp_path):
        img = tmp_path / "foto.jpg"
        img.write_bytes(b"\xff" * 100)
        r = validate_imagen(str(img))
        assert r.ok is True

    def test_imagen_no_existe(self):
        r = validate_imagen("/no/existe/foto.jpg")
        assert r.ok is False

    def test_imagen_grande(self, tmp_path):
        img = tmp_path / "big.jpg"
        img.write_bytes(b"\xff" * (IG_IMAGE_MAX_MB * 1024 * 1024 + 1))
        r = validate_imagen(str(img))
        assert r.ok is False

    def test_imagen_extension_rara(self, tmp_path):
        img = tmp_path / "foto.bmp"
        img.write_bytes(b"\xff" * 100)
        r = validate_imagen(str(img))
        assert r.ok is True
        assert len(r.advertencias) > 0

    def test_imagen_png(self, tmp_path):
        img = tmp_path / "foto.png"
        img.write_bytes(b"\xff" * 100)
        r = validate_imagen(str(img))
        assert r.ok is True

    def test_imagen_jpeg(self, tmp_path):
        img = tmp_path / "foto.jpeg"
        img.write_bytes(b"\xff" * 100)
        r = validate_imagen(str(img))
        assert r.ok is True


# ===== validate_post =====


class TestValidatePost:
    def test_post_valido(self, tmp_path):
        r = validate_post(
            caption="Lote en Cañuelas",
            hashtags=["#lotes", "#canuelas"],
            municipio="Cañuelas",
            hectareas=5,
        )
        assert r.ok is True

    def test_post_caption_invalido(self):
        r = validate_post(caption="")
        assert r.ok is False

    def test_post_hashtags_invalidos(self):
        r = validate_post(
            caption="test",
            hashtags=["sin_hash"],
        )
        assert r.ok is False

    def test_post_municipio_invalido_estricto(self):
        r = validate_post(
            caption="test",
            municipio="Cordoba",
            estricto_municipio=True,
        )
        assert r.ok is False

    def test_post_hectareas_invalidas(self):
        r = validate_post(
            caption="test",
            hectareas=-5,
        )
        assert r.ok is False

    def test_post_solo_caption(self):
        r = validate_post(caption="test caption")
        assert r.ok is True

    def test_post_sin_hashtags(self):
        r = validate_post(caption="test", hashtags=None)
        assert r.ok is True

    def test_post_metadata_structure(self):
        r = validate_post(
            caption="test",
            hashtags=["#ok"],
            municipio="Cañuelas",
            hectareas=5,
        )
        assert "caption" in r.metadata
        assert "hashtags" in r.metadata
        assert "municipio" in r.metadata
        assert "hectareas" in r.metadata


# ===== safe_post =====


class TestSafePost:
    def test_safe_post_agrega_validacion(self):
        post = {
            "caption_completo": "Test caption",
            "hashtags": ["#lotes"],
        }
        result = safe_post(post, municipio="Cañuelas")
        assert "_validacion" in result
        assert result["_validacion"]["ok"] is True

    def test_safe_post_caption_vacio(self):
        post = {
            "caption_completo": "",
            "hashtags": ["#lotes"],
        }
        result = safe_post(post)
        assert result["_validacion"]["ok"] is False

    def test_safe_post_sin_caption(self):
        post = {"hashtags": ["#lotes"]}
        result = safe_post(post)
        assert "_validacion" in result
