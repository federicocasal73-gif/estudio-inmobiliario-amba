"""Tests del modulo image_generator.py.

Cubre:
  - ImageResult dataclass: to_dict, defaults
  - StubImageGenerator: generar, fooocus_disponible, _output_path_sugerido
  - FooocusImageGenerator: _parsear_aspect, _detectar_endpoint, generar
  - get_generator: factory con/sin gradio-client, con/sin fooocus
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from image_generator import (
    FooocusImageGenerator,
    ImageResult,
    StubImageGenerator,
    get_generator,
)

# ===== ImageResult =====


class TestImageResult:
    def test_defaults(self):
        r = ImageResult(prompt="test prompt")
        assert r.negative_prompt == ""
        assert r.aspect_ratio == "1152*896"
        assert r.styles == []
        assert r.output_path is None
        assert r.stub is True
        assert r.mensaje == ""

    def test_to_dict(self):
        r = ImageResult(prompt="test", stub=False, fooocus_disponible=True)
        d = r.to_dict()
        assert d["prompt"] == "test"
        assert d["stub"] is False
        assert isinstance(d, dict)


# ===== StubImageGenerator =====


class TestStubImageGenerator:
    def test_generar_basico(self, tmp_path):
        gen = StubImageGenerator(output_dir=tmp_path)
        with patch.object(gen, "_check_fooocus", return_value=False):
            gen.fooocus_disponible = False

        resultado = gen.generar(
            prompt="5 hectares pampas farm",
            output_path=tmp_path / "output.jpg",
        )
        assert resultado.stub is True
        assert resultado.fooocus_disponible is False
        assert resultado.output_path == str(tmp_path / "output.jpg")
        assert "Fooocus no detectado" in resultado.mensaje

    def test_generar_con_fooocus_corriendo(self, tmp_path):
        gen = StubImageGenerator(output_dir=tmp_path)
        gen.fooocus_disponible = True

        resultado = gen.generar(
            prompt="test",
            output_path=tmp_path / "out.jpg",
        )
        assert "Fooocus esta corriendo" in resultado.mensaje

    def test_generar_guarda_prompt_json(self, tmp_path):
        gen = StubImageGenerator(output_dir=tmp_path)
        gen.fooocus_disponible = False

        gen.generar(
            prompt="mi prompt",
            negative_prompt="ugly",
            aspect_ratio="1024*768",
            styles=["V2"],
            output_path=tmp_path / "img.jpg",
        )
        json_path = tmp_path / "img.prompt.json"
        assert json_path.exists()
        data = json.loads(json_path.read_text())
        assert data["prompt"] == "mi prompt"
        assert data["negative_prompt"] == "ugly"
        assert data["aspect_ratio"] == "1024*768"

    def test_output_path_sugerido(self, tmp_path):
        gen = StubImageGenerator(output_dir=tmp_path)
        path = gen._output_path_sugerido("5 hectares pampas farm golden hour")
        assert path.suffix == ".jpg"
        assert "5_hectares_pampas" in path.name

    def test_generar_default_styles(self, tmp_path):
        gen = StubImageGenerator(output_dir=tmp_path)
        gen.fooocus_disponible = False
        resultado = gen.generar(prompt="test", output_path=tmp_path / "o.jpg")
        assert "Fooocus V2" in resultado.styles

    def test_generar_default_output_path(self, tmp_path):
        gen = StubImageGenerator(output_dir=tmp_path)
        gen.fooocus_disponible = False
        resultado = gen.generar(prompt="test prompt largo aca")
        assert resultado.output_path is not None
        assert ".jpg" in resultado.output_path

    def test_check_fooocus_false(self, tmp_path):
        gen = StubImageGenerator(fooocus_url="http://127.0.0.1:19999", output_dir=tmp_path)
        assert gen.fooocus_disponible is False


# ===== FooocusImageGenerator =====


class TestFooocusImageGenerator:
    def test_parsear_aspect(self):
        gen = FooocusImageGenerator()
        w, h = gen._parsear_aspect("1152*896")
        assert w == 1152
        assert h == 896

    def test_parsear_aspect_con_x(self):
        gen = FooocusImageGenerator()
        w, h = gen._parsear_aspect("1024x768")
        assert w == 1024
        assert h == 768

    def test_parsear_aspect_invalido(self):
        gen = FooocusImageGenerator()
        w, h = gen._parsear_aspect("invalido")
        assert w == 1152
        assert h == 896

    def test_detectar_endpoint_cache(self):
        gen = FooocusImageGenerator()
        gen._endpoint = "cached_endpoint"
        assert gen._detectar_endpoint() == "cached_endpoint"

    def test_detectar_endpoint_fallido(self):
        gen = FooocusImageGenerator()
        gen._get_client = MagicMock()
        gen._get_client.return_value.view_api.return_value = {
            "named_endpoints": {"otro_endpoint": {}},
            "unnamed_endpoints": {},
        }
        with pytest.raises(RuntimeError, match="No se encontro"):
            gen._detectar_endpoint()

    def test_detectar_endpoint_exitoso(self):
        gen = FooocusImageGenerator()
        gen._get_client = MagicMock()
        gen._get_client.return_value.view_api.return_value = {
            "named_endpoints": {"generate_image": {}, "other": {}},
            "unnamed_endpoints": {},
        }
        ep = gen._detectar_endpoint()
        assert ep == "generate_image"

    def test_output_path_sugerido(self, tmp_path):
        gen = FooocusImageGenerator(output_dir=tmp_path)
        path = gen._output_path_sugerido("5 hectares pampas farm golden")
        assert path.suffix == ".jpg"
        assert "5_hectares_pampas" in path.name


# ===== get_generator =====


class TestGetGenerator:
    def test_stub_when_gradio_no_instalado(self):
        with patch.dict("sys.modules", {"gradio_client": None}):
            gen = get_generator()
            assert isinstance(gen, StubImageGenerator)

    def test_stub_when_fooocus_no_disponible(self):
        mock_gradio = MagicMock()
        with patch.dict("sys.modules", {"gradio_client": mock_gradio}):
            with patch("image_generator.StubImageGenerator._check_fooocus", return_value=False):
                gen = get_generator()
                assert isinstance(gen, StubImageGenerator)

    def test_real_when_fooocus_disponible(self):
        mock_gradio = MagicMock()
        with patch.dict("sys.modules", {"gradio_client": mock_gradio}):
            with patch("image_generator.StubImageGenerator._check_fooocus", return_value=True):
                gen = get_generator(prefer_real=True)
                assert isinstance(gen, FooocusImageGenerator)

    def test_stub_when_prefer_real_false(self):
        mock_gradio = MagicMock()
        with patch.dict("sys.modules", {"gradio_client": mock_gradio}):
            with patch("image_generator.StubImageGenerator._check_fooocus", return_value=True):
                gen = get_generator(prefer_real=False)
                assert isinstance(gen, StubImageGenerator)
