"""Tests para mejora_fotos.py - Motor de mejora de fotos."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from PIL import Image

from mejora_fotos import MejoraFotos, ResultadoMejora, HAS_PILLOW


@pytest.fixture
def test_image(tmp_path):
    """Crea una imagen de prueba de 200x150."""
    img = Image.new("RGB", (200, 150), color=(180, 160, 130))
    path = tmp_path / "test.jpg"
    img.save(path, "JPEG")
    return path


@pytest.fixture
def dark_image(tmp_path):
    """Imagen subexpuesta."""
    img = Image.new("RGB", (200, 150), color=(30, 25, 20))
    path = tmp_path / "dark.jpg"
    img.save(path, "JPEG")
    return path


@pytest.fixture
def bright_image(tmp_path):
    """Imagen sobreexpuesta."""
    img = Image.new("RGB", (200, 150), color=(240, 235, 230))
    path = tmp_path / "bright.jpg"
    img.save(path, "JPEG")
    return path


@pytest.mark.skipif(not HAS_PILLOW, reason="Pillow not installed")
class TestMejoraFotosInit:
    def test_init(self):
        m = MejoraFotos()
        assert m.fooocus_url is None
        assert m.fooocus_disponible is False

    def test_init_custom_url(self):
        m = MejoraFotos(fooocus_url="http://127.0.0.1:7865")
        assert m.fooocus_url == "http://127.0.0.1:7865"

    def test_check_fooocus_no_url(self):
        m = MejoraFotos()
        assert m._check_fooocus() is False

    def test_check_fooocus_unreachable(self):
        m = MejoraFotos(fooocus_url="http://127.0.0.1:19999")
        assert m.fooocus_disponible is False


@pytest.mark.skipif(not HAS_PILLOW, reason="Pillow not installed")
class TestMejorar:
    def test_mejorar_magazine(self, test_image, tmp_path):
        m = MejoraFotos()
        resultado = m.mejorar(
            foto_path=test_image,
            modo="magazine",
            intensidad="media",
            upscale=1,
            ruta_salida=tmp_path / "out.jpg",
        )
        assert resultado.foto_destino != ""
        assert Path(resultado.foto_destino).exists()
        assert any("look:magazine" in t for t in resultado.transformaciones)

    def test_mejorar_natural(self, test_image, tmp_path):
        m = MejoraFotos()
        resultado = m.mejorar(
            foto_path=test_image,
            modo="natural",
            intensidad="baja",
            ruta_salida=tmp_path / "out.jpg",
        )
        assert resultado.modo == "natural"
        assert resultado.intensidad == "baja"

    def test_mejorar_instagram(self, test_image, tmp_path):
        m = MejoraFotos()
        resultado = m.mejorar(
            foto_path=test_image,
            modo="instagram",
            intensidad="alta",
            tamaño_ig=(1080, 1350),
            ruta_salida=tmp_path / "out.jpg",
        )
        assert any("resize_instagram" in t for t in resultado.transformaciones)

    def test_mejorar_golden_hour(self, test_image, tmp_path):
        m = MejoraFotos()
        resultado = m.mejorar(
            foto_path=test_image,
            modo="golden_hour",
            intensidad="media",
            ruta_salida=tmp_path / "out.jpg",
        )
        assert resultado.modo == "golden_hour"

    def test_mejorar_pampa(self, test_image, tmp_path):
        m = MejoraFotos()
        resultado = m.mejorar(
            foto_path=test_image,
            modo="pampa",
            intensidad="media",
            ruta_salida=tmp_path / "out.jpg",
        )
        assert resultado.modo == "pampa"

    def test_mejorar_upscale(self, test_image, tmp_path):
        m = MejoraFotos()
        resultado = m.mejorar(
            foto_path=test_image,
            upscale=2,
            ruta_salida=tmp_path / "out.jpg",
        )
        assert any("upscale_x2" in t for t in resultado.transformaciones)

    def test_mejorar_auto_ruta(self, test_image):
        m = MejoraFotos()
        resultado = m.mejorar(foto_path=test_image)
        assert resultado.foto_destino != ""
        assert Path(resultado.foto_destino).exists()

    def test_mejorar_modo_invalido(self, test_image):
        m = MejoraFotos()
        with pytest.raises(ValueError, match="modo invalido"):
            m.mejorar(foto_path=test_image, modo="invalido")

    def test_mejorar_intensidad_invalida(self, test_image):
        m = MejoraFotos()
        with pytest.raises(ValueError, match="intensidad invalida"):
            m.mejorar(foto_path=test_image, intensidad="invalida")

    def test_mejorar_no_existe(self):
        m = MejoraFotos()
        with pytest.raises(FileNotFoundError):
            m.mejorar(foto_path="/nonexistent.jpg")


@pytest.mark.skipif(not HAS_PILLOW, reason="Pillow not installed")
class TestMejorarAutoExposure:
    def test_dark_image(self, dark_image, tmp_path):
        m = MejoraFotos()
        resultado = m.mejorar(
            foto_path=dark_image,
            modo="natural",
            ruta_salida=tmp_path / "out.jpg",
        )
        assert any("auto_exposure" in t for t in resultado.transformaciones)

    def test_bright_image(self, bright_image, tmp_path):
        m = MejoraFotos()
        resultado = m.mejorar(
            foto_path=bright_image,
            modo="natural",
            ruta_salida=tmp_path / "out.jpg",
        )
        assert any("auto_exposure" in t for t in resultado.transformaciones)


@pytest.mark.skipif(not HAS_PILLOW, reason="Pillow not installed")
class TestBatch:
    def test_batch(self, test_image, tmp_path):
        m = MejoraFotos()
        origenes = tmp_path / "origenes"
        origenes.mkdir()
        (origenes / "foto1.jpg").write_bytes(test_image.read_bytes())
        (origenes / "foto2.jpg").write_bytes(test_image.read_bytes())

        destinos = tmp_path / "destinos"
        resultados = m.batch(
            carpeta_origen=origenes,
            carpeta_destino=destinos,
            modo="magazine",
            intensidad="media",
        )
        assert len(resultados) == 2
        assert all(r.foto_destino != "" for r in resultados)

    def test_batch_vacio(self, tmp_path):
        m = MejoraFotos()
        origenes = tmp_path / "empty"
        origenes.mkdir()
        destinos = tmp_path / "destinos"
        resultados = m.batch(carpeta_origen=origenes, carpeta_destino=destinos)
        assert len(resultados) == 0

    def test_batch_with_error(self, tmp_path):
        m = MejoraFotos()
        origenes = tmp_path / "origenes"
        origenes.mkdir()
        (origenes / "bad.jpg").write_bytes(b"not an image")

        destinos = tmp_path / "destinos"
        resultados = m.batch(
            carpeta_origen=origenes,
            carpeta_destino=destinos,
        )
        assert len(resultados) == 1
        assert any("ERROR" in t for t in resultados[0].transformaciones)


@pytest.mark.skipif(not HAS_PILLOW, reason="Pillow not installed")
class TestMejorarConFooocus:
    def test_no_fooocus(self, test_image):
        m = MejoraFotos()
        with pytest.raises(RuntimeError, match="Fooocus no esta activo"):
            m.mejorar_con_fooocus(test_image)


@pytest.mark.skipif(not HAS_PILLOW, reason="Pillow not installed")
class TestHelpers:
    def test_parametros_efectivos(self):
        m = MejoraFotos()
        params = m._parametros_efectivos("magazine", "media")
        assert "brillo" in params
        assert "contraste" in params
        assert params["brillo"] > 1.0

    def test_parametros_baja(self):
        m = MejoraFotos()
        params = m._parametros_efectivos("natural", "baja")
        assert params["brillo"] < m._parametros_efectivos("natural", "alta")["brillo"]

    def test_aplicar_look(self, test_image):
        img = Image.open(test_image)
        params = {"brillo": 1.1, "contraste": 1.2, "saturacion": 1.1, "sharpness": 1.3, "warmth": 1.0}
        result = MejoraFotos._aplicar_look(img, params)
        assert result.size == img.size

    def test_aplicar_warmth_calido(self, test_image):
        img = Image.open(test_image)
        result = MejoraFotos._aplicar_warmth(img, 1.2)
        assert result.size == img.size

    def test_aplicar_warmth_frio(self, test_image):
        img = Image.open(test_image)
        result = MejoraFotos._aplicar_warmth(img, 0.8)
        assert result.size == img.size

    def test_upscale(self, test_image):
        img = Image.open(test_image)
        result = MejoraFotos._upscale(img, 2)
        assert result.width == img.width * 2
        assert result.height == img.height * 2

    def test_resize_instagram(self, test_image):
        img = Image.open(test_image)
        result = MejoraFotos._resize_instagram(img, (1080, 1350))
        assert result.size == (1080, 1350)

    def test_metadata_imagen(self, test_image):
        m = MejoraFotos()
        meta = m._metadata_imagen(test_image)
        assert "archivo" in meta
        assert "tamaño_bytes" in meta


@pytest.mark.skipif(not HAS_PILLOW, reason="Pillow not installed")
class TestResultadoMejora:
    def test_to_dict(self):
        r = ResultadoMejora(
            foto_origen="/tmp/a.jpg",
            foto_destino="/tmp/b.jpg",
            modo="magazine",
            intensidad="media",
            upscale=1,
        )
        d = r.to_dict()
        assert isinstance(d, dict)
        assert d["modo"] == "magazine"
        assert "fecha_procesado" in d


@pytest.mark.skipif(not HAS_PILLOW, reason="Pillow not installed")
class TestDemo:
    def test_demo(self):
        from mejora_fotos import demo
        demo()
