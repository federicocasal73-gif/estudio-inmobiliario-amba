"""Tests del modulo studio.py (orquestador end-to-end).

Cubre:
  - PipelineResultado dataclass
  - Studio.__init__
  - pipeline_semana: dry-run, con proyectos, sin proyectos, con validacion
  - _tipo_carrusel_por_dia
  - _nombre_carrusel_desde_slot
  - _publicar_slot: various types, empty post, no images
  - duplicar_proyecto: copytree, cambios JSON
  - _actualizar_prompts_en_json, _actualizar_resumen
  - regenerar_carruseles
  - publicar_carrusel_existente: no existe, JSON invalido, sin imagenes
  - preview_carrusel: no existe, existe
  - generar_imagenes_carrusel: placeholder, sin prompt, con prompt, error
  - guardar_pipeline
  - listar_carruseles: vacio, con proyecto, sin proyecto
  - CLI helpers: _build_batch_items_from_carrusel
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from studio import (
    ROOT,
    PipelineResultado,
    Studio,
    _build_batch_items_from_carrusel,
)

# ===== Fixtures =====


def _mock_studio_deps(tmp_path=None):
    """Mock completo de Studio con todas las dependencias."""
    with (
        patch("studio.RealestateStudio"),
        patch("studio.CalendarioEditorial") as mock_cal_cls,
        patch("studio.CarruselFactory") as mock_car_cls,
        patch("studio.AntesDespuesFactory"),
        patch("studio.MejoraFotos"),
        patch("studio.InstagramAuth"),
        patch("studio.InstagramPublisher") as mock_pub_cls,
        patch("studio.PreviewHTML"),
        patch("studio.get_generator") as mock_gen,
        patch("studio.HistorialPublicaciones"),
        patch("studio.RotadorProyectos"),
    ):
        mock_cal = mock_cal_cls.return_value
        mock_car = mock_car_cls.return_value
        mock_pub = mock_pub_cls.return_value
        mock_gen.return_value = MagicMock(stub=True)

        # Mock generar_semana
        from datetime import datetime

        from calendario_editorial import SemanaEditorial, SlotEditorial

        slot = SlotEditorial(
            fecha="2025-07-14",
            dia_semana="lunes",
            hora_sugerida="19:00",
            tipo_post="lote_venta",
            tono="emotivo",
            nicho=["general"],
            municipio="Cañuelas",
            proyecto="chacra-5ha",
            post={"caption": "Test", "hashtags": ["#lotes"], "caption_completo": "Test #lotes"},
        )
        semana = SemanaEditorial(
            numero=1,
            fecha_inicio="2025-07-14",
            fecha_fin="2025-07-20",
            proyectos_disponibles=["chacra-5ha"],
            municipio_principal="Cañuelas",
            slots=[slot],
        )
        mock_cal.generar_semana.return_value = semana

        from instagram_publisher import PublicacionResultado

        mock_pub.publicar_carrusel.return_value = PublicacionResultado(
            modo="dry-run",
            exito=True,
            tipo="carrusel",
            caption_length=10,
            n_imagenes=2,
        )
        mock_pub.publicar_foto.return_value = PublicacionResultado(
            modo="dry-run",
            exito=True,
            tipo="foto",
            caption_length=10,
            n_imagenes=1,
        )

        s = Studio()
        return s, mock_cal, mock_car, mock_pub


# ===== PipelineResultado =====


class TestPipelineResultado:
    def test_creacion(self):
        r = PipelineResultado(
            semana_numero=1,
            fecha_inicio="2025-07-14",
            fecha_fin="2025-07-20",
            n_slots=5,
        )
        assert r.semana_numero == 1
        assert r.n_slots == 5
        assert len(r.errores) == 0

    def test_to_dict(self):
        r = PipelineResultado(
            semana_numero=1,
            fecha_inicio="2025-07-14",
            fecha_fin="2025-07-20",
            n_slots=5,
        )
        d = r.to_dict()
        assert d["semana_numero"] == 1
        assert d["resumen"] == ""

    def test_fecha_ejecucion(self):
        r = PipelineResultado(
            semana_numero=1,
            fecha_inicio="",
            fecha_fin="",
            n_slots=0,
        )
        assert r.fecha_ejecucion  # non-empty


# ===== Studio._tipo_carrusel_por_dia =====


class TestTipoCarruselPorDia:
    def test_lunes(self):
        assert Studio._tipo_carrusel_por_dia("lunes") == "lote_premium"

    def test_martes(self):
        assert Studio._tipo_carrusel_por_dia("martes") == "country_etapa"

    def test_domingo(self):
        assert Studio._tipo_carrusel_por_dia("domingo") == "obra_avance"

    def test_desconocido(self):
        assert Studio._tipo_carrusel_por_dia("otro") == "lote_premium"


# ===== Studio._nombre_carrusel_desde_slot =====


class TestNombreCarruselDesdeSlot:
    def test_nombre(self):
        s, _, _, _ = _mock_studio_deps()
        slot = MagicMock()
        slot.tipo_post = "carrusel"
        slot.dia_semana = "lunes"
        slot.proyecto = "chacra-5ha"
        semana = MagicMock()
        semana.numero = 1
        nombre = s._nombre_carrusel_desde_slot(slot, semana)
        assert "chacra-5ha" in nombre
        assert "lote_premium" in nombre
        assert "sem01" in nombre

    def test_servicios(self):
        s, _, _, _ = _mock_studio_deps()
        slot = MagicMock()
        slot.tipo_post = "servicios"
        slot.dia_semana = "jueves"
        slot.proyecto = "empresa-x"
        semana = MagicMock()
        semana.numero = 2
        nombre = s._nombre_carrusel_desde_slot(slot, semana)
        assert "servicios" in nombre


# ===== Studio.pipeline_semana =====


class TestPipelineSemana:
    def test_dry_run_basico(self):
        s, mock_cal, _, _ = _mock_studio_deps()
        resultado = s.pipeline_semana(
            semana_n=1,
            proyectos=["chacra-5ha"],
            posts_por_semana=1,
            modo_publicacion=MagicMock(value="dry-run"),
        )
        assert isinstance(resultado, PipelineResultado)
        assert resultado.n_slots == 1
        mock_cal.generar_semana.assert_called_once()

    def test_sin_proyectos(self):
        s, mock_cal, _, _ = _mock_studio_deps()
        resultado = s.pipeline_semana(posts_por_semana=1)
        assert resultado.n_slots == 1

    def test_con_errores_calendario(self):
        s, mock_cal, _, _ = _mock_studio_deps()
        mock_cal.generar_semana.side_effect = Exception("Error calendario")
        resultado = s.pipeline_semana(posts_por_semana=1)
        assert len(resultado.errores) > 0
        assert "calendario" in resultado.errores[0]

    def test_resumen_formato(self):
        s, _, _, _ = _mock_studio_deps()
        resultado = s.pipeline_semana(posts_por_semana=1)
        assert "Semana" in resultado.resumen
        assert "slots" in resultado.resumen


# ===== Studio._publicar_slot =====


class TestPublicarSlot:
    def test_slot_vacio(self):
        s, _, _, mock_pub = _mock_studio_deps()
        slot = MagicMock()
        slot.post = None
        semana = MagicMock()
        resultado = s._publicar_slot(slot, semana, MagicMock(value="dry-run"))
        assert resultado.exito is False

    def test_slot_sin_caption(self):
        s, _, _, _ = _mock_studio_deps()
        slot = MagicMock()
        slot.post = {"caption": ""}
        semana = MagicMock()
        resultado = s._publicar_slot(slot, semana, MagicMock(value="dry-run"))
        assert resultado.exito is False

    def test_slot_con_post_sin_imagenes(self):
        s, _, _, mock_pub = _mock_studio_deps()
        slot = MagicMock()
        slot.tipo_post = "lote_venta"
        slot.proyecto = "chacra-5ha"
        slot.post = {"caption": "Test", "hashtags": ["#lotes"], "caption_completo": "Test #lotes"}
        semana = MagicMock()
        resultado = s._publicar_slot(slot, semana, MagicMock(value="dry-run"))
        # No images in filesystem → dry-run fallback
        assert resultado.exito is False
        assert "Dry-run" in resultado.error or "Sin imagenes" in resultado.error


# ===== duplicar_proyecto =====


class TestDuplicarProyecto:
    def test_origen_no_existe(self):
        s, _, _, _ = _mock_studio_deps()
        with pytest.raises(FileNotFoundError):
            s.duplicar_proyecto("no-existe", "destino")

    def test_destino_ya_existe(self, tmp_path):
        s, _, _, _ = _mock_studio_deps()
        # Create the expected directory structure
        base = tmp_path / "inmuebles" / "lotes"
        base.mkdir(parents=True)
        (base / "origen").mkdir()
        (base / "destino").mkdir()
        with patch("studio.ROOT", tmp_path):
            with pytest.raises(FileExistsError):
                s.duplicar_proyecto("origen", "destino")

    def test_duplicar_ok(self, tmp_path):
        s, _, _, _ = _mock_studio_deps()
        base = tmp_path / "inmuebles" / "lotes"
        base.mkdir(parents=True)
        origen = base / "origen"
        origen.mkdir()
        (origen / "data.json").write_text("{}")
        with patch("studio.ROOT", tmp_path):
            result = s.duplicar_proyecto("origen", "destino")
            assert result.exists()
            assert (result / "data.json").exists()


# ===== _actualizar_prompts_en_json =====


class TestActualizarPrompts:
    def test_actualizar_hectareas(self, tmp_path):
        s, _, _, _ = _mock_studio_deps()
        data = {
            "slides": [
                {"prompt": "chacra de 5 hectares en Cañuelas"},
                {"prompt": "casa de campo"},
            ]
        }
        json_path = tmp_path / "carrusel.json"
        json_path.write_text(json.dumps(data))
        s._actualizar_prompts_en_json(json_path, {"hectareas": 10})
        result = json.loads(json_path.read_text())
        assert "10 hectares" in result["slides"][0]["prompt"]

    def test_actualizar_municipio(self, tmp_path):
        s, _, _, _ = _mock_studio_deps()
        data = {
            "slides": [
                {"prompt": "chacra en Cañuelas"},
            ]
        }
        json_path = tmp_path / "carrusel.json"
        json_path.write_text(json.dumps(data))
        s._actualizar_prompts_en_json(json_path, {"municipio": "Pilar"})
        result = json.loads(json_path.read_text())
        assert "Pilar" in result["slides"][0]["prompt"]

    def test_json_invalido(self, tmp_path):
        s, _, _, _ = _mock_studio_deps()
        json_path = tmp_path / "bad.json"
        json_path.write_text("not json")
        # Should not raise
        s._actualizar_prompts_en_json(json_path, {})


# ===== _actualizar_resumen =====


class TestActualizarResumen:
    def test_actualizar(self, tmp_path):
        s, _, _, _ = _mock_studio_deps()
        data = {"hectareas": 5, "municipio": "Cañuelas"}
        json_path = tmp_path / "resumen.json"
        json_path.write_text(json.dumps(data))
        s._actualizar_resumen(json_path, {"hectareas": 10})
        result = json.loads(json_path.read_text())
        assert result["hectareas"] == 10

    def test_json_invalido(self, tmp_path):
        s, _, _, _ = _mock_studio_deps()
        json_path = tmp_path / "bad.json"
        json_path.write_text("not json")
        s._actualizar_resumen(json_path, {})


# ===== publicar_carrusel_existente =====


class TestPublicarCarruselExistente:
    def test_no_existe(self):
        s, _, _, _ = _mock_studio_deps()
        resultado = s.publicar_carrusel_existente("/no/existe.json")
        assert resultado.exito is False

    def test_json_invalido(self, tmp_path):
        s, _, _, _ = _mock_studio_deps()
        json_path = tmp_path / "bad.json"
        json_path.write_text("not json")
        resultado = s.publicar_carrusel_existente(str(json_path))
        assert resultado.exito is False
        assert "invalido" in resultado.error.lower()

    def test_sin_imagenes(self, tmp_path):
        s, _, _, _ = _mock_studio_deps()
        data = {"caption_narrativo": "Test", "hashtags": ["#lotes"], "n_slides": 3}
        json_path = tmp_path / "carrusel.json"
        json_path.write_text(json.dumps(data))
        slides_dir = tmp_path / "slides"
        slides_dir.mkdir()
        resultado = s.publicar_carrusel_existente(str(json_path))
        assert resultado.exito is False
        assert "2 imagenes" in resultado.error


# ===== guardar_pipeline =====


class TestGuardarPipeline:
    def test_guardar(self, tmp_path):
        s, _, _, _ = _mock_studio_deps()
        resultado = PipelineResultado(
            semana_numero=1,
            fecha_inicio="2025-07-14",
            fecha_fin="2025-07-20",
            n_slots=5,
        )
        with patch("studio.ROOT", tmp_path):
            ruta = s.guardar_pipeline(resultado, nombre="test_pipeline")
            assert ruta.exists()
            data = json.loads(ruta.read_text())
            assert data["semana_numero"] == 1

    def test_guardar_default_nombre(self, tmp_path):
        s, _, _, _ = _mock_studio_deps()
        resultado = PipelineResultado(
            semana_numero=1,
            fecha_inicio="",
            fecha_fin="",
            n_slots=0,
        )
        with patch("studio.ROOT", tmp_path):
            ruta = s.guardar_pipeline(resultado)
            assert ruta.exists()


# ===== listar_carruseles =====


class TestListarCarruseles:
    def test_vacio(self, tmp_path):
        s, _, _, _ = _mock_studio_deps()
        base = tmp_path / "inmuebles" / "lotes"
        base.mkdir(parents=True)
        with patch("studio.ROOT", tmp_path):
            result = s.listar_carruseles()
            assert result == []

    def test_con_carrusel(self, tmp_path):
        s, _, _, _ = _mock_studio_deps()
        base = tmp_path / "inmuebles" / "lotes" / "mi-proyecto" / "carruseles" / "mi-carrusel"
        base.mkdir(parents=True)
        data = {"tema": "Test", "tipo": "lote_premium", "n_slides": 4, "municipio": "Cañuelas"}
        (base / "carrusel.json").write_text(json.dumps(data))
        with patch("studio.ROOT", tmp_path):
            result = s.listar_carruseles(proyecto="mi-proyecto")
            assert len(result) == 1
            assert result[0]["tema"] == "Test"

    def test_todos_los_carruseles(self, tmp_path):
        s, _, _, _ = _mock_studio_deps()
        for proj in ["p1", "p2"]:
            base = tmp_path / "inmuebles" / "lotes" / proj / "carruseles" / f"car-{proj}"
            base.mkdir(parents=True)
            data = {"tema": f"Test {proj}", "tipo": "lote_premium", "n_slides": 4, "municipio": "M"}
            (base / "carrusel.json").write_text(json.dumps(data))
        with patch("studio.ROOT", tmp_path):
            result = s.listar_carruseles()
            assert len(result) == 2


# ===== _build_batch_items_from_carrusel =====


class TestBuildBatchItems:
    def test_build(self, tmp_path):
        data = {
            "slides": [
                {
                    "numero": 1,
                    "tipo": "foto",
                    "prompt": "prompt1",
                    "aspect_ratio": "896*1152",
                    "styles": ["V2"],
                },
                {"numero": 2, "tipo": "placeholder_foto", "prompt": ""},
                {"numero": 3, "tipo": "dato", "prompt": ""},
            ]
        }
        json_path = tmp_path / "carrusel.json"
        json_path.write_text(json.dumps(data))
        items = _build_batch_items_from_carrusel(json_path)
        assert len(items) == 1  # only foto with prompt

    def test_batch_variants(self, tmp_path):
        data = {
            "slides": [
                {
                    "numero": 1,
                    "tipo": "foto",
                    "prompt": "prompt1",
                    "aspect_ratio": "896*1152",
                    "styles": [],
                },
            ]
        }
        json_path = tmp_path / "carrusel.json"
        json_path.write_text(json.dumps(data))
        items = _build_batch_items_from_carrusel(json_path, batch_variants=3)
        assert len(items) == 3


# ===== preview_carrusel =====


class TestPreviewCarrusel:
    def test_no_existe(self):
        s, _, _, _ = _mock_studio_deps()
        with pytest.raises(FileNotFoundError):
            s.preview_carrusel("/no/existe.json")

    def test_ok(self, tmp_path):
        s, _, _, _ = _mock_studio_deps()
        data = {
            "tema": "Test",
            "tipo": "lote_premium",
            "municipio": "Cañuelas",
            "tono": "emotivo",
            "slides": [
                {"numero": 1, "tipo": "foto", "descripcion": "Test", "prompt": "p"},
            ],
            "caption_narrativo": "Caption",
            "hashtags": ["#lotes"],
        }
        json_path = tmp_path / "carrusel.json"
        json_path.write_text(json.dumps(data))
        with patch("studio.ROOT", tmp_path):
            result = s.preview_carrusel(str(json_path))
            assert result.exists()


# ===== generar_imagenes_carrusel =====


class TestGenerarImagenesCarrusel:
    def test_placeholder_skip(self, tmp_path):
        s, _, _, _ = _mock_studio_deps()
        data = {
            "slides": [
                {
                    "numero": 1,
                    "tipo": "placeholder_foto",
                    "prompt": "",
                    "aspect_ratio": "896*1152",
                    "styles": [],
                },
            ]
        }
        json_path = tmp_path / "carrusel.json"
        json_path.write_text(json.dumps(data))
        slides_dir = tmp_path / "slides"
        slides_dir.mkdir()
        resultados = s.generar_imagenes_carrusel(str(json_path))
        assert len(resultados) == 1
        assert resultados[0]["saltado"] is True

    def test_sin_prompt_skip(self, tmp_path):
        s, _, _, _ = _mock_studio_deps()
        data = {
            "slides": [
                {
                    "numero": 1,
                    "tipo": "dato",
                    "prompt": "",
                    "aspect_ratio": "896*1152",
                    "styles": [],
                },
            ]
        }
        json_path = tmp_path / "carrusel.json"
        json_path.write_text(json.dumps(data))
        slides_dir = tmp_path / "slides"
        slides_dir.mkdir()
        resultados = s.generar_imagenes_carrusel(str(json_path))
        assert len(resultados) == 1
        assert resultados[0]["saltado"] is True

    def test_con_prompt(self, tmp_path):
        s, _, _, _ = _mock_studio_deps()
        data = {
            "slides": [
                {
                    "numero": 1,
                    "tipo": "foto",
                    "prompt": "test prompt",
                    "aspect_ratio": "896*1152",
                    "styles": ["V2"],
                },
            ]
        }
        json_path = tmp_path / "carrusel.json"
        json_path.write_text(json.dumps(data))
        slides_dir = tmp_path / "slides"
        slides_dir.mkdir()
        resultados = s.generar_imagenes_carrusel(str(json_path))
        assert len(resultados) == 1
        assert resultados[0]["saltado"] is False

    def test_error_generacion(self, tmp_path):
        s, _, _, _ = _mock_studio_deps()
        s.image_generator.generar.side_effect = Exception("Fooocus down")
        data = {
            "slides": [
                {
                    "numero": 1,
                    "tipo": "foto",
                    "prompt": "test",
                    "aspect_ratio": "896*1152",
                    "styles": [],
                },
            ]
        }
        json_path = tmp_path / "carrusel.json"
        json_path.write_text(json.dumps(data))
        slides_dir = tmp_path / "slides"
        slides_dir.mkdir()
        resultados = s.generar_imagenes_carrusel(str(json_path))
        assert len(resultados) == 1
        assert "error" in resultados[0]
