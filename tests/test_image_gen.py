"""Tests para image_generator.py - Generador de imagenes IA."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from image_generator import (
    ImageResult,
    StubImageGenerator,
    FooocusImageGenerator,
    get_generator,
    ImageGenerator,
    DEFAULT_OUTPUT_DIR,
)


class TestImageResult:
    def test_creation(self):
        r = ImageResult(prompt="test prompt")
        assert r.prompt == "test prompt"
        assert r.stub is True
        assert r.fooocus_disponible is False
        assert r.output_path is None

    def test_to_dict(self):
        r = ImageResult(prompt="test")
        d = r.to_dict()
        assert isinstance(d, dict)
        assert d["prompt"] == "test"
        assert "fecha" in d

    def test_with_all_fields(self):
        r = ImageResult(
            prompt="test",
            negative_prompt="bad",
            aspect_ratio="896*1152",
            styles=["Fooocus V2"],
            output_path="/tmp/out.jpg",
            fooocus_url="http://localhost:7865",
            fooocus_disponible=True,
            stub=False,
            mensaje="ok",
        )
        assert r.stub is False
        assert r.fooocus_disponible is True


class TestStubImageGenerator:
    def test_init(self):
        gen = StubImageGenerator()
        assert gen.fooocus_url == "http://127.0.0.1:7865"
        assert gen.fooocus_disponible is False

    def test_init_custom_url(self):
        gen = StubImageGenerator(fooocus_url="http://custom:9999")
        assert gen.fooocus_url == "http://custom:9999"

    def test_generar(self, tmp_path):
        gen = StubImageGenerator(output_dir=tmp_path)
        result = gen.generar(
            prompt="5 hectares pampas",
            output_path=tmp_path / "test.jpg",
        )
        assert result.stub is True
        assert result.prompt == "5 hectares pampas"
        assert result.output_path == str(tmp_path / "test.jpg")

    def test_generar_con_kwargs(self, tmp_path):
        gen = StubImageGenerator(output_dir=tmp_path)
        result = gen.generar(
            prompt="test",
            output_path=tmp_path / "test.jpg",
            custom_param="value",
        )
        assert result.metadata.get("kwargs", {}).get("custom_param") == "value"

    def test_generar_sin_output_path(self, tmp_path):
        gen = StubImageGenerator(output_dir=tmp_path)
        result = gen.generar(prompt="test prompt here")
        assert result.output_path is not None
        assert result.stub is True
        assert "test_prompt_here" in result.output_path

    def test_generar_prompt_json(self, tmp_path):
        gen = StubImageGenerator(output_dir=tmp_path)
        output = tmp_path / "test.jpg"
        result = gen.generar(
            prompt="test",
            negative_prompt="bad",
            aspect_ratio="896*1152",
            styles=["Fooocus V2"],
            output_path=output,
        )
        json_path = output.with_suffix(".prompt.json")
        assert json_path.exists()
        data = json.loads(json_path.read_text())
        assert data["prompt"] == "test"

    def test_output_path_sugerido(self, tmp_path):
        gen = StubImageGenerator(output_dir=tmp_path)
        path = gen._output_path_sugerido("5 hectares pampas golden hour real estate")
        assert path.parent == tmp_path
        assert path.suffix == ".jpg"
        assert len(path.stem) > 0

    def test_check_fooocus_no_detectado(self):
        gen = StubImageGenerator(fooocus_url="http://127.0.0.1:19999")
        assert gen.fooocus_disponible is False

    def test_generar_fooocus_no_disponible(self, tmp_path):
        gen = StubImageGenerator(fooocus_url="http://127.0.0.1:19999", output_dir=tmp_path)
        result = gen.generar(prompt="test", output_path=tmp_path / "out.jpg")
        assert "Fooocus no detectado" in result.mensaje


class TestFooocusImageGenerator:
    def test_init(self):
        gen = FooocusImageGenerator()
        assert gen.fooocus_url == "http://127.0.0.1:7865"
        assert gen._cliente is None
        assert gen._endpoint is None

    def test_parsear_aspect(self):
        gen = FooocusImageGenerator()
        assert gen._parsear_aspect("1152*896") == (1152, 896)
        assert gen._parsear_aspect("896x1152") == (896, 1152)
        assert gen._parsear_aspect("invalid") == (1152, 896)

    def test_parsear_aspect_custom(self):
        gen = FooocusImageGenerator()
        assert gen._parsear_aspect("1024*1024") == (1024, 1024)

    @patch("image_generator.FooocusImageGenerator._get_client")
    def test_detectar_endpoint(self, mock_get_client):
        gen = FooocusImageGenerator()
        mock_client = MagicMock()
        mock_client.view_api.return_value = {
            "named_endpoints": {"generate_image": {}, "upload": {}},
            "unnamed_endpoints": {},
        }
        mock_get_client.return_value = mock_client

        endpoint = gen._detectar_endpoint()
        assert endpoint == "generate_image"

    @patch("image_generator.FooocusImageGenerator._get_client")
    def test_detectar_endpoint_cache(self, mock_get_client):
        gen = FooocusImageGenerator()
        gen._endpoint = "cached_endpoint"
        endpoint = gen._detectar_endpoint()
        assert endpoint == "cached_endpoint"
        mock_get_client.assert_not_called()

    @patch("image_generator.FooocusImageGenerator._get_client")
    def test_detectar_endpoint_no_encontrado(self, mock_get_client):
        gen = FooocusImageGenerator()
        mock_client = MagicMock()
        mock_client.view_api.return_value = {
            "named_endpoints": {"upload": {}, "download": {}},
            "unnamed_endpoints": {},
        }
        mock_get_client.return_value = mock_client

        with pytest.raises(RuntimeError, match="No se encontro"):
            gen._detectar_endpoint()

    def test_get_client_no_gradio(self):
        gen = FooocusImageGenerator()
        with patch.dict("sys.modules", {"gradio_client": None}):
            with pytest.raises(RuntimeError, match="gradio-client no instalado"):
                gen._get_client()

    def test_output_path_sugerido(self, tmp_path):
        gen = FooocusImageGenerator(output_dir=tmp_path)
        path = gen._output_path_sugerido("5 hectares pampas golden hour")
        assert path.parent == tmp_path
        assert path.suffix == ".jpg"


class TestGetGenerator:
    def test_get_generator_stub(self):
        with patch.dict("sys.modules", {"gradio_client": None}):
            gen = get_generator()
            assert isinstance(gen, StubImageGenerator)

    def test_get_generator_prefer_real_false(self):
        gen = get_generator(prefer_real=False)
        assert isinstance(gen, StubImageGenerator)

    @patch("image_generator.FooocusImageGenerator")
    @patch("image_generator.StubImageGenerator")
    def test_get_generator_fooocus_available(self, MockStub, MockFooocus):
        mock_stub = MagicMock()
        mock_stub.fooocus_disponible = True
        mock_stub.fooocus_url = "http://127.0.0.1:7865"
        MockStub.return_value = mock_stub

        gen = get_generator(prefer_real=True)
        MockFooocus.assert_called_once_with("http://127.0.0.1:7865")

    @patch("image_generator.StubImageGenerator")
    def test_get_generator_fooocus_fails(self, MockStub):
        mock_stub = MagicMock()
        mock_stub.fooocus_disponible = True
        mock_stub.fooocus_url = "http://127.0.0.1:7865"
        MockStub.return_value = mock_stub

        with patch("image_generator.FooocusImageGenerator", side_effect=Exception("fail")):
            gen = get_generator(prefer_real=True)
            assert gen is mock_stub


class TestFooocusGenerar:
    @patch("image_generator.FooocusImageGenerator._get_client")
    @patch("image_generator.FooocusImageGenerator._detectar_endpoint")
    @patch("image_generator.FooocusImageGenerator._esperar_y_descargar")
    def test_generar_exitoso(self, mock_descargar, mock_endpoint, mock_get_client, tmp_path):
        mock_endpoint.return_value = "generate_image"
        mock_client = MagicMock()
        mock_client.predict.return_value = MagicMock()
        mock_get_client.return_value = mock_client
        gen = FooocusImageGenerator(output_dir=tmp_path)
        result = gen.generar(
            prompt="test prompt",
            output_path=tmp_path / "out.jpg",
        )
        assert result.stub is False
        assert result.fooocus_disponible is True
        mock_descargar.assert_called_once()

    @patch("image_generator.FooocusImageGenerator._get_client")
    @patch("image_generator.FooocusImageGenerator._detectar_endpoint")
    def test_generar_fooocus_error(self, mock_endpoint, mock_get_client, tmp_path):
        mock_endpoint.return_value = "generate_image"
        mock_client = MagicMock()
        mock_client.predict.side_effect = Exception("fooocus crashed")
        mock_get_client.return_value = mock_client
        gen = FooocusImageGenerator(output_dir=tmp_path)
        with pytest.raises(RuntimeError, match="Error enviando a Fooocus"):
            gen.generar(prompt="test", output_path=tmp_path / "out.jpg")

    @patch("image_generator.FooocusImageGenerator._get_client")
    @patch("image_generator.FooocusImageGenerator._detectar_endpoint")
    def test_generar_descarga_error(self, mock_endpoint, mock_get_client, tmp_path):
        mock_endpoint.return_value = "generate_image"
        mock_client = MagicMock()
        mock_client.predict.return_value = MagicMock()
        mock_get_client.return_value = mock_client
        gen = FooocusImageGenerator(output_dir=tmp_path)
        with patch.object(gen, "_esperar_y_descargar", side_effect=RuntimeError("download fail")):
            with pytest.raises(RuntimeError, match="Error descargando resultado"):
                gen.generar(prompt="test", output_path=tmp_path / "out.jpg")

    def test_generar_sin_output_path(self, tmp_path):
        gen = FooocusImageGenerator(output_dir=tmp_path)
        with patch.object(gen, "_get_client") as mock_get, \
             patch.object(gen, "_detectar_endpoint", return_value="generate_image"), \
             patch.object(gen, "_esperar_y_descargar"):
            mock_client = MagicMock()
            mock_client.predict.return_value = MagicMock()
            mock_get.return_value = mock_client
            result = gen.generar(prompt="auto path generation test")
            assert result.output_path is not None

    def test_generar_custom_styles_and_params(self, tmp_path):
        gen = FooocusImageGenerator(output_dir=tmp_path)
        with patch.object(gen, "_get_client") as mock_get, \
             patch.object(gen, "_detectar_endpoint", return_value="generate_image"), \
             patch.object(gen, "_esperar_y_descargar"):
            mock_client = MagicMock()
            mock_client.predict.return_value = MagicMock()
            mock_get.return_value = mock_client
            result = gen.generar(
                prompt="test",
                output_path=tmp_path / "out.jpg",
                steps=50,
                cfg_scale=7.0,
                seed=42,
                styles=["Custom Style"],
            )
            assert result.stub is False


class TestEsperarYDescargar:
    def test_resultado_lista_con_path_local(self, tmp_path):
        gen = FooocusImageGenerator()
        src = tmp_path / "source.jpg"
        src.write_bytes(b"fake image")
        dst = tmp_path / "dest.jpg"
        gen._esperar_y_descargar([str(src)], dst)
        assert dst.exists()
        assert not src.exists()

    def test_resultado_tuple(self, tmp_path):
        gen = FooocusImageGenerator()
        src = tmp_path / "source.jpg"
        src.write_bytes(b"fake image")
        dst = tmp_path / "dest.jpg"
        gen._esperar_y_descargar((str(src),), dst)
        assert dst.exists()

    def test_resultado_string(self, tmp_path):
        gen = FooocusImageGenerator()
        src = tmp_path / "source.jpg"
        src.write_bytes(b"fake image")
        dst = tmp_path / "dest.jpg"
        gen._esperar_y_descargar(str(src), dst)
        assert dst.exists()

    def test_resultado_none_raises(self):
        gen = FooocusImageGenerator()
        with pytest.raises(RuntimeError, match="vacio"):
            gen._esperar_y_descargar(None, Path("/tmp/out.jpg"))

    def test_resultado_http_url(self, tmp_path):
        gen = FooocusImageGenerator()
        dst = tmp_path / "downloaded.jpg"
        with patch("urllib.request.urlopen") as mock_url:
            mock_resp = MagicMock()
            mock_resp.read.return_value = b"image bytes"
            mock_resp.__enter__ = lambda s: s
            mock_resp.__exit__ = MagicMock(return_value=False)
            mock_url.return_value = mock_resp
            gen._esperar_y_descargar("https://example.com/image.jpg", dst)
            assert dst.exists()

    def test_resultado_path_not_exists_and_not_url_raises(self):
        gen = FooocusImageGenerator()
        with pytest.raises(RuntimeError, match="No se pudo obtener"):
            gen._esperar_y_descargar("/nonexistent/path.jpg", Path("/tmp/out.jpg"))


class TestGetClientCaching:
    def test_client_cached(self):
        gen = FooocusImageGenerator()
        mock_client = MagicMock()
        gen._cliente = mock_client
        assert gen._get_client() is mock_client

    def test_detectar_endpoint_view_api_exception(self):
        gen = FooocusImageGenerator()
        mock_client = MagicMock()
        mock_client.view_api.side_effect = Exception("api error")
        gen._cliente = mock_client
        with pytest.raises(RuntimeError, match="No se pudo inspeccionar"):
            gen._detectar_endpoint()


class TestDemo:
    def test_demo(self, tmp_path):
        from image_generator import demo
        with patch("image_generator.get_generator") as mock_get:
            mock_gen = MagicMock()
            mock_gen.fooocus_url = "http://test:7865"
            mock_gen.fooocus_disponible = False
            mock_gen.generar.return_value = ImageResult(
                prompt="test",
                output_path=str(tmp_path / "test.jpg"),
                stub=True,
                mensaje="test message",
            )
            mock_get.return_value = mock_gen
            demo()
            mock_gen.generar.assert_called_once()


class TestImageGeneratorAbstract:
    def test_cannot_instantiate(self):
        with pytest.raises(TypeError):
            ImageGenerator()
