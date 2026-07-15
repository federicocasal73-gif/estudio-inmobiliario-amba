"""Tests del modulo mejora_fotos.py.

Cubre:
  - ResultadoMejora dataclass: to_dict, defaults, fecha_procesado
  - MejoraFotos.__init__: con/sin fooocus_url, _check_fooocus
  - MejoraFotos.mejorar: modos natural/magazine/instagram/golden_hour/pampa,
    validaciones, auto_exposure, upscale, resize instagram, ruta custom
  - batch: procesamiento OK, errores filtrados
  - mejorar_con_fooocus: no disponible, disponible
  - _metadata_imagen, _necesita_auto_exposure, _auto_exposure
  - _parametros_efectivos, _aplicar_look, _aplicar_warmth
  - _upscale, _resize_instagram
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from mejora_fotos import HAS_PILLOW, MejoraFotos, ResultadoMejora


# ===== ResultadoMejora dataclass =====


class TestResultadoMejora:
    def test_defaults(self):
        r = ResultadoMejora(
            foto_origen="/a.jpg",
            foto_destino="/b.jpg",
            modo="magazine",
            intensidad="media",
            upscale=1,
        )
        assert r.transformaciones == []
        assert r.metadata_origen == {}
        assert r.metadata_destino == {}
        assert r.fooocus_usado is False
        assert r.fecha_procesado  # not empty

    def test_to_dict(self):
        r = ResultadoMejora(
            foto_origen="/a.jpg",
            foto_destino="/b.jpg",
            modo="pampa",
            intensidad="alta",
            upscale=2,
            transformaciones=["look:pampa"],
            metadata_origen={"w": 800},
        )
        d = r.to_dict()
        assert isinstance(d, dict)
        assert d["modo"] == "pampa"
        assert d["upscale"] == 2
        assert d["transformaciones"] == ["look:pampa"]
        assert d["metadata_origen"] == {"w": 800}

    def test_fecha_procesado_format(self):
        r = ResultadoMejora(
            foto_origen="/a.jpg",
            foto_destino="/b.jpg",
            modo="natural",
            intensidad="baja",
            upscale=1,
        )
        assert "T" in r.fecha_procesado  # ISO format


# ===== MejoraFotos init =====


class TestMejoraFotosInit:
    def test_init_sin_fooocus(self):
        mf = MejoraFotos()
        assert mf.fooocus_url is None
        assert mf.fooocus_disponible is False

    def test_init_con_url_fooocus_falla(self):
        mf = MejoraFotos(fooocus_url="http://localhost:9999")
        assert mf.fooocus_url == "http://localhost:9999"
        assert mf.fooocus_disponible is False


# ===== _check_fooocus =====


class TestCheckFooocus:
    def test_no_url(self):
        mf = MejoraFotos()
        assert mf._check_fooocus() is False

    @patch("urllib.request.urlopen")
    @patch("urllib.request.Request")
    def test_url_ok(self, mock_req, mock_urlopen):
        mock_urlopen.return_value.__enter__ = lambda s: s
        mock_urlopen.return_value.__exit__ = MagicMock(return_value=False)
        mf = MejoraFotos(fooocus_url="http://localhost:7865")
        assert mf.fooocus_disponible is True

    @patch("urllib.request.urlopen", side_effect=Exception("refused"))
    @patch("urllib.request.Request")
    def test_url_falla(self, mock_req, mock_urlopen):
        mf = MejoraFotos(fooocus_url="http://localhost:7865")
        assert mf.fooocus_disponible is False


# ===== _metadata_imagen =====


class TestMetadataImagen:
    def test_metadata(self, tmp_path):
        img_path = tmp_path / "test.jpg"
        img_path.write_bytes(b"\xff" * 100)
        mf = MejoraFotos()
        meta = mf._metadata_imagen(img_path)
        assert meta["archivo"] == "test.jpg"
        assert meta["tamaño_bytes"] == 100


# ===== _parametros_efectivos =====


class TestParametrosEfectivos:
    def test_media_returns_original(self):
        mf = MejoraFotos()
        params = mf._parametros_efectivos("magazine", "media")
        orig = MejoraFotos.PARAMETROS_POR_MODO["magazine"]
        for k in orig:
            assert params[k] == pytest.approx(orig[k], abs=0.01)

    def test_baja_reduces(self):
        mf = MejoraFotos()
        params = mf._parametros_efectivos("natural", "baja")
        orig = MejoraFotos.PARAMETROS_POR_MODO["natural"]
        for k in orig:
            expected = 1.0 + (orig[k] - 1.0) * 0.5
            assert params[k] == pytest.approx(expected, abs=0.01)

    def test_alta_aumenta(self):
        mf = MejoraFotos()
        params = mf._parametros_efectivos("instagram", "alta")
        orig = MejoraFotos.PARAMETROS_POR_MODO["instagram"]
        for k in orig:
            expected = 1.0 + (orig[k] - 1.0) * 1.5
            assert params[k] == pytest.approx(expected, abs=0.01)


# ===== _aplicar_warmth =====


@pytest.mark.skipif(not HAS_PILLOW, reason="Pillow not installed")
class TestAplicarWarmth:
    def test_warm_increases_red(self):
        from PIL import Image

        img = Image.new("RGB", (10, 10), (128, 128, 128))
        result = MejoraFotos._aplicar_warmth(img, 1.3)
        r, g, b = result.split()
        assert r.getpixel((5, 5)) > 128
        assert b.getpixel((5, 5)) < 128

    def test_cool_increases_blue(self):
        from PIL import Image

        img = Image.new("RGB", (10, 10), (128, 128, 128))
        result = MejoraFotos._aplicar_warmth(img, 0.8)
        r, g, b = result.split()
        assert b.getpixel((5, 5)) > 128
        assert r.getpixel((5, 5)) < 128

    def test_neutral_no_change(self):
        from PIL import Image

        img = Image.new("RGB", (10, 10), (128, 128, 128))
        result = MejoraFotos._aplicar_warmth(img, 1.0)
        assert list(result.getpixel((5, 5))) == [128, 128, 128]


# ===== _upscale =====


@pytest.mark.skipif(not HAS_PILLOW, reason="Pillow not installed")
class TestUpscale:
    def test_upscale_2x(self):
        from PIL import Image

        img = Image.new("RGB", (100, 50), (0, 0, 0))
        result = MejoraFotos._upscale(img, 2)
        assert result.size == (200, 100)

    def test_upscale_3x(self):
        from PIL import Image

        img = Image.new("RGB", (10, 10), (0, 0, 0))
        result = MejoraFotos._upscale(img, 3)
        assert result.size == (30, 30)


# ===== _resize_instagram =====


@pytest.mark.skipif(not HAS_PILLOW, reason="Pillow not installed")
class TestResizeInstagram:
    def test_resize(self):
        from PIL import Image

        img = Image.new("RGB", (800, 600), (0, 0, 0))
        result = MejoraFotos._resize_instagram(img, (1080, 1350))
        assert result.size == (1080, 1350)


# ===== _necesita_auto_exposure =====


@pytest.mark.skipif(not HAS_PILLOW, reason="Pillow not installed")
class TestNecesitaAutoExposure:
    def test_oscura(self):
        from PIL import Image

        img = Image.new("RGB", (100, 100), (30, 30, 30))
        assert MejoraFotos._necesita_auto_exposure(img) is True

    def test_clara(self):
        from PIL import Image

        img = Image.new("RGB", (100, 100), (240, 240, 240))
        assert MejoraFotos._necesita_auto_exposure(img) is True

    def test_normal(self):
        from PIL import Image

        img = Image.new("RGB", (100, 100), (128, 128, 128))
        assert MejoraFotos._necesita_auto_exposure(img) is False


# ===== _auto_exposure =====


@pytest.mark.skipif(not HAS_PILLOW, reason="Pillow not installed")
class TestAutoExposure:
    def test_baja_intensidad(self):
        from PIL import Image

        img = Image.new("RGB", (100, 100), (30, 30, 30))
        result = MejoraFotos._auto_exposure(img, "baja")
        assert result.getpixel((50, 50)) != (30, 30, 30)

    def test_media_intensidad(self):
        from PIL import Image

        img = Image.new("RGB", (100, 100), (30, 30, 30))
        result = MejoraFotos._auto_exposure(img, "media")
        assert result.getpixel((50, 50)) != (30, 30, 30)

    def test_alta_intensidad(self):
        from PIL import Image

        img = Image.new("RGB", (100, 100), (30, 30, 30))
        result = MejoraFotos._auto_exposure(img, "alta")
        assert result.getpixel((50, 50)) != (30, 30, 30)


# ===== _aplicar_look =====


@pytest.mark.skipif(not HAS_PILLOW, reason="Pillow not installed")
class TestAplicarLook:
    def test_look_returns_image(self):
        from PIL import Image

        img = Image.new("RGB", (100, 100), (128, 128, 128))
        params = {"brillo": 1.1, "contraste": 1.2, "saturacion": 1.1, "sharpness": 1.3, "warmth": 1.0}
        result = MejoraFotos._aplicar_look(img, params)
        assert result.size == (100, 100)

    def test_look_con_warmth(self):
        from PIL import Image

        img = Image.new("RGB", (100, 100), (128, 128, 128))
        params = {"brillo": 1.0, "contraste": 1.0, "saturacion": 1.0, "sharpness": 1.0, "warmth": 1.3}
        result = MejoraFotos._aplicar_look(img, params)
        assert result.size == (100, 100)


# ===== mejorar() =====


@pytest.mark.skipif(not HAS_PILLOW, reason="Pillow not installed")
class TestMejorar:
    def _make_foto(self, tmp_path, name="foto.jpg", color=(180, 160, 130), size=(200, 150)):
        from PIL import Image

        foto = tmp_path / name
        img = Image.new("RGB", size, color)
        img.save(foto, "JPEG")
        return foto

    def test_modo_natural(self, tmp_path):
        foto = self._make_foto(tmp_path)
        mf = MejoraFotos()
        r = mf.mejorar(foto, modo="natural", intensidad="media", upscale=1)
        assert r.modo == "natural"
        assert r.foto_destino
        assert Path(r.foto_destino).exists()
        assert len(r.transformaciones) >= 2

    def test_modo_magazine(self, tmp_path):
        foto = self._make_foto(tmp_path)
        mf = MejoraFotos()
        r = mf.mejorar(foto, modo="magazine")
        assert r.modo == "magazine"
        assert any("look:magazine" in t for t in r.transformaciones)

    def test_modo_instagram(self, tmp_path):
        foto = self._make_foto(tmp_path)
        mf = MejoraFotos()
        r = mf.mejorar(foto, modo="instagram")
        assert r.modo == "instagram"

    def test_modo_golden_hour(self, tmp_path):
        foto = self._make_foto(tmp_path)
        mf = MejoraFotos()
        r = mf.mejorar(foto, modo="golden_hour")
        assert r.modo == "golden_hour"

    def test_modo_pampa(self, tmp_path):
        foto = self._make_foto(tmp_path)
        mf = MejoraFotos()
        r = mf.mejorar(foto, modo="pampa")
        assert r.modo == "pampa"
        assert any("look:pampa" in t for t in r.transformaciones)

    def test_upscale_2x(self, tmp_path):
        foto = self._make_foto(tmp_path, size=(100, 100))
        mf = MejoraFotos()
        r = mf.mejorar(foto, upscale=2)
        assert any("upscale_x2" in t for t in r.transformaciones)

    def test_upscale_3x(self, tmp_path):
        foto = self._make_foto(tmp_path, size=(100, 100))
        mf = MejoraFotos()
        r = mf.mejorar(foto, upscale=3)
        assert any("upscale_x3" in t for t in r.transformaciones)

    def test_resize_instagram(self, tmp_path):
        foto = self._make_foto(tmp_path, size=(400, 300))
        mf = MejoraFotos()
        r = mf.mejorar(foto, modo="instagram", tamaño_ig=(1080, 1350))
        assert any("resize_instagram" in t for t in r.transformaciones)

    def test_ruta_salida_custom(self, tmp_path):
        foto = self._make_foto(tmp_path)
        salida = tmp_path / "custom" / "output.jpg"
        mf = MejoraFotos()
        r = mf.mejorar(foto, ruta_salida=salida)
        assert Path(r.foto_destino) == salida.resolve()

    def test_ruta_salida_default(self, tmp_path):
        foto = self._make_foto(tmp_path)
        mf = MejoraFotos()
        r = mf.mejorar(foto, modo="magazine")
        assert "mejoras" in r.foto_destino

    def test_modo_invalido(self, tmp_path):
        foto = self._make_foto(tmp_path)
        mf = MejoraFotos()
        with pytest.raises(ValueError, match="modo invalido"):
            mf.mejorar(foto, modo="invalido")

    def test_intensidad_invalida(self, tmp_path):
        foto = self._make_foto(tmp_path)
        mf = MejoraFotos()
        with pytest.raises(ValueError, match="intensidad invalida"):
            mf.mejorar(foto, intensidad="extrema")

    def test_foto_no_existe(self, tmp_path):
        mf = MejoraFotos()
        with pytest.raises(FileNotFoundError):
            mf.mejorar(tmp_path / "nonexistent.jpg")

    def test_metadata_origen_y_destino(self, tmp_path):
        foto = self._make_foto(tmp_path)
        mf = MejoraFotos()
        r = mf.mejorar(foto)
        assert r.metadata_origen["archivo"] == "foto.jpg"
        assert r.metadata_destino["formato"] == "JPEG"
        assert r.metadata_destino["size"]

    def test_intensidad_baja(self, tmp_path):
        foto = self._make_foto(tmp_path)
        mf = MejoraFotos()
        r = mf.mejorar(foto, intensidad="baja")
        assert r.intensidad == "baja"

    def test_intensidad_alta(self, tmp_path):
        foto = self._make_foto(tmp_path)
        mf = MejoraFotos()
        r = mf.mejorar(foto, intensidad="alta")
        assert r.intensidad == "alta"

    def test_auto_exposure_oscura(self, tmp_path):
        from PIL import Image

        foto = tmp_path / "oscura.jpg"
        img = Image.new("RGB", (200, 200), (20, 20, 20))
        img.save(foto, "JPEG")
        mf = MejoraFotos()
        r = mf.mejorar(foto, modo="natural")
        assert any("auto_exposure" in t for t in r.transformaciones)

    def test_auto_exposure_clara(self, tmp_path):
        from PIL import Image

        foto = tmp_path / "clara.jpg"
        img = Image.new("RGB", (200, 200), (245, 245, 245))
        img.save(foto, "JPEG")
        mf = MejoraFotos()
        r = mf.mejorar(foto, modo="natural")
        assert any("auto_exposure" in t for t in r.transformaciones)

    def test_warmth_en_transformaciones(self, tmp_path):
        foto = self._make_foto(tmp_path)
        mf = MejoraFotos()
        r = mf.mejorar(foto, modo="golden_hour", intensidad="alta")
        assert any("warmth=1.40" in t or "warmth=1." in t for t in r.transformaciones)


# ===== batch() =====


@pytest.mark.skipif(not HAS_PILLOW, reason="Pillow not installed")
class TestBatch:
    def _make_fotos(self, tmp_path, n=3):
        from PIL import Image

        fotos = []
        for i in range(n):
            f = tmp_path / f"foto_{i}.jpg"
            img = Image.new("RGB", (100, 100), (100 + i * 30, 120, 100))
            img.save(f, "JPEG")
            fotos.append(f)
        return fotos

    def test_batch_normal(self, tmp_path):
        fotos = self._make_fotos(tmp_path)
        destino = tmp_path / "destino"
        mf = MejoraFotos()
        resultados = mf.batch(tmp_path, destino, modo="natural", intensidad="media")
        assert len(resultados) == 3
        assert all(r.foto_destino for r in resultados)

    def test_batch_sin_fotos(self, tmp_path):
        destino = tmp_path / "destino"
        mf = MejoraFotos()
        resultados = mf.batch(tmp_path, destino)
        assert len(resultados) == 0

    def test_batch_con_error(self, tmp_path):
        from PIL import Image

        # jpg file with invalid content (corrupt JPEG)
        bad = tmp_path / "bad.jpg"
        bad.write_bytes(b"not a real jpeg")
        good = tmp_path / "good.jpg"
        Image.new("RGB", (100, 100), (128, 128, 128)).save(good, "JPEG")
        destino = tmp_path / "destino"
        mf = MejoraFotos()
        resultados = mf.batch(tmp_path, destino)
        # bad file generates error result, good file succeeds
        assert len(resultados) == 2
        errors = [r for r in resultados if any("ERROR" in t for t in r.transformaciones)]
        assert len(errors) == 1

    def test_batch_extensiones_custom(self, tmp_path):
        from PIL import Image

        jpg = tmp_path / "foto.jpg"
        png = tmp_path / "foto.png"
        Image.new("RGB", (100, 100), (128, 128, 128)).save(jpg, "JPEG")
        Image.new("RGB", (100, 100), (128, 128, 128)).save(png, "PNG")
        destino = tmp_path / "destino"
        mf = MejoraFotos()
        resultados = mf.batch(tmp_path, destino, extensiones=(".jpg",))
        assert len(resultados) == 1


# ===== mejorar_con_fooocus =====


@pytest.mark.skipif(not HAS_PILLOW, reason="Pillow not installed")
class TestMejorarConFooocus:
    def _make_foto(self, tmp_path):
        from PIL import Image

        foto = tmp_path / "foto.jpg"
        img = Image.new("RGB", (200, 200), (180, 160, 130))
        img.save(foto, "JPEG")
        return foto

    def test_no_disponible(self, tmp_path):
        foto = self._make_foto(tmp_path)
        mf = MejoraFotos()
        with pytest.raises(RuntimeError, match="Fooocus no esta activo"):
            mf.mejorar_con_fooocus(foto)

    def test_disponible_upscale_2x(self, tmp_path):
        foto = self._make_foto(tmp_path)
        mf = MejoraFotos(fooocus_url="http://localhost:7865")
        # Force fooocus_disponible = True
        mf.fooocus_disponible = True
        r = mf.mejorar_con_fooocus(foto, operacion="upscale_2x")
        assert r.fooocus_usado is False  # pending API integration
        assert any("fooocus_delegated" in t for t in r.transformaciones)

    def test_disponible_upscale_4x(self, tmp_path):
        foto = self._make_foto(tmp_path)
        mf = MejoraFotos(fooocus_url="http://localhost:7865")
        mf.fooocus_disponible = True
        r = mf.mejorar_con_fooocus(foto, operacion="upscale_4x")
        assert any("upscale_x4" in t for t in r.transformaciones)

    def test_operacion_desconocida_default_2x(self, tmp_path):
        foto = self._make_foto(tmp_path)
        mf = MejoraFotos(fooocus_url="http://localhost:7865")
        mf.fooocus_disponible = True
        r = mf.mejorar_con_fooocus(foto, operacion="inpaint")
        assert any("upscale_x2" in t for t in r.transformaciones)


# ===== Constants and class attributes =====


class TestMejoraFotosConstants:
    def test_modos(self):
        assert MejoraFotos.MODOS == ["natural", "magazine", "instagram", "golden_hour", "pampa"]

    def test_intensidades(self):
        assert MejoraFotos.INTENSIDADES == ["baja", "media", "alta"]

    def test_all_modos_have_params(self):
        for modo in MejoraFotos.MODOS:
            assert modo in MejoraFotos.PARAMETROS_POR_MODO
            params = MejoraFotos.PARAMETROS_POR_MODO[modo]
            for key in ("brillo", "contraste", "saturacion", "sharpness", "warmth"):
                assert key in params

    def test_multiplicadores(self):
        assert MejoraFotos.MULTIPLICADOR_INTENSIDAD["baja"] == 0.5
        assert MejoraFotos.MULTIPLICADOR_INTENSIDAD["media"] == 1.0
        assert MejoraFotos.MULTIPLICADOR_INTENSIDAD["alta"] == 1.5
