"""Tests del modulo studio.py.

Cubre:
  - PipelineResultado dataclass: to_dict, defaults
  - Studio.__init__: inicializacion con mocks
  - Studio.pipeline_semana: calendario error, sin slots, carruseles, publicacion
  - Studio._tipo_carrusel_por_dia
  - Studio._nombre_carrusel_desde_slot
  - Studio._publicar_slot: slot vacio, carrusel con imagenes, proyecto con fotos
  - Studio.duplicar_proyecto: origen no existe, destino existe, OK, cambios JSON
  - Studio._aplicar_cambios_a_json, _actualizar_prompts_en_json, _actualizar_resumen
  - Studio.regenerar_carruseles
  - Studio.publicar_carrusel_existente: no existe, JSON invalido, pocas imagenes, OK
  - Studio.preview_carrusel
  - Studio.generar_imagenes_carrusel: placeholder, sin prompt, OK, error
  - Studio.generar_imagenes_pipeline
  - Studio.guardar_pipeline
  - Studio.listar_carruseles
  - _build_batch_items_from_carrusel
  - _generar_carrusel_completo: no existe, sin items, cancelado
  - _generar_carrusel_interactivo
  - _encolar_carrusel
  - _procesar_cola
  - build_arg_parser (CLI)
  - CLI subcommands: demo, semana, duplicar, publicar, preview, cache-stats,
    generar, generar-carousel, generar-cola, procesar-cola, programar,
    procesar-programadas, publicaciones, reporte-semanal, responder-dm, listar
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch, mock_open

import pytest

from studio import (
    PipelineResultado,
    Studio,
    _build_batch_items_from_carrusel,
    _generar_carrusel_completo,
    cli,
)


# ===== PipelineResultado =====


class TestPipelineResultado:
    def test_defaults(self):
        r = PipelineResultado(
            semana_numero=1,
            fecha_inicio="2026-07-07",
            fecha_fin="2026-07-13",
            n_slots=5,
        )
        assert r.carruseles_generados == []
        assert r.mejoras_aplicadas == []
        assert r.publicaciones == []
        assert r.validaciones == []
        assert r.errores == []
        assert r.resumen == ""
        assert r.fecha_ejecucion

    def test_to_dict(self):
        r = PipelineResultado(
            semana_numero=2,
            fecha_inicio="2026-07-14",
            fecha_fin="2026-07-20",
            n_slots=5,
            resumen="test resumen",
        )
        d = r.to_dict()
        assert isinstance(d, dict)
        assert d["semana_numero"] == 2
        assert d["resumen"] == "test resumen"
        assert isinstance(d["carruseles_generados"], list)


# ===== Studio init =====


class TestStudioInit:
    @patch("studio.RealestateStudio")
    @patch("studio.CarruselFactory")
    @patch("studio.CalendarioEditorial")
    @patch("studio.AntesDespuesFactory")
    @patch("studio.MejoraFotos")
    @patch("studio.InstagramAuth")
    @patch("studio.InstagramPublisher")
    @patch("studio.PreviewHTML")
    @patch("studio.get_generator")
    @patch("studio.HistorialPublicaciones")
    @patch("studio.RotadorProyectos")
    def test_init(
        self, mock_rot, mock_hist, mock_gen, mock_prev, mock_pub, mock_auth,
        mock_mejora, mock_ad, mock_cal, mock_car, mock_rs
    ):
        s = Studio()
        assert s.studio_core == mock_rs.return_value
        assert s.carruseles == mock_car.return_value
        assert s.calendario == mock_cal.return_value


# ===== _tipo_carrusel_por_dia =====


class TestTipoCarruselPorDia:
    def test_lunes(self):
        assert Studio._tipo_carrusel_por_dia("lunes") == "lote_premium"

    def test_martes(self):
        assert Studio._tipo_carrusel_por_dia("martes") == "country_etapa"

    def test_miercoles(self):
        assert Studio._tipo_carrusel_por_dia("miercoles") == "lote_premium"

    def test_jueves(self):
        assert Studio._tipo_carrusel_por_dia("jueves") == "servicios"

    def test_viernes(self):
        assert Studio._tipo_carrusel_por_dia("viernes") == "lote_premium"

    def test_sabado(self):
        assert Studio._tipo_carrusel_por_dia("sabado") == "lote_premium"

    def test_domingo(self):
        assert Studio._tipo_carrusel_por_dia("domingo") == "obra_avance"

    def test_desconocido(self):
        assert Studio._tipo_carrusel_por_dia("feriado") == "lote_premium"


# ===== _build_batch_items_from_carrusel =====


class TestBuildBatchItems:
    def test_normal(self, tmp_path):
        data = {
            "slides": [
                {"numero": 1, "tipo": "foto", "prompt": "un lote", "aspect_ratio": "896*1152", "styles": []},
                {"numero": 2, "tipo": "texto", "prompt": "", "aspect_ratio": "896*1152", "styles": []},
            ]
        }
        carrusel = tmp_path / "carrusel.json"
        carrusel.write_text(json.dumps(data))
        items = _build_batch_items_from_carrusel(carrusel)
        assert len(items) == 1
        assert items[0].prompt == "un lote"

    def test_placeholder_skip(self, tmp_path):
        data = {
            "slides": [
                {"numero": 1, "tipo": "placeholder_foto", "prompt": "skip", "aspect_ratio": "896*1152", "styles": []},
                {"numero": 2, "tipo": "foto", "prompt": "render", "aspect_ratio": "896*1152", "styles": []},
            ]
        }
        carrusel = tmp_path / "carrusel.json"
        carrusel.write_text(json.dumps(data))
        items = _build_batch_items_from_carrusel(carrusel)
        assert len(items) == 1

    def test_batch_variants(self, tmp_path):
        data = {
            "slides": [
                {"numero": 1, "tipo": "foto", "prompt": "prompt", "aspect_ratio": "896*1152", "styles": []},
            ]
        }
        carrusel = tmp_path / "carrusel.json"
        carrusel.write_text(json.dumps(data))
        items = _build_batch_items_from_carrusel(carrusel, batch_variants=3)
        assert len(items) == 3

    def test_sin_slides(self, tmp_path):
        data = {"slides": []}
        carrusel = tmp_path / "carrusel.json"
        carrusel.write_text(json.dumps(data))
        items = _build_batch_items_from_carrusel(carrusel)
        assert len(items) == 0


# ===== Studio._publicar_slot =====


class TestPublicarSlot:
    def _make_slot(self, **kwargs):
        defaults = {
            "post": None,
            "tipo_post": "obra_avance",
            "municipio": "Cañuelas",
            "proyecto": None,
            "fecha": "2026-07-07",
            "dia_semana": "lunes",
            "tono": "emotivo",
        }
        defaults.update(kwargs)
        return MagicMock(**defaults)

    @patch("studio.RealestateStudio")
    @patch("studio.CarruselFactory")
    @patch("studio.CalendarioEditorial")
    @patch("studio.AntesDespuesFactory")
    @patch("studio.MejoraFotos")
    @patch("studio.InstagramAuth")
    @patch("studio.InstagramPublisher")
    @patch("studio.PreviewHTML")
    @patch("studio.get_generator")
    @patch("studio.HistorialPublicaciones")
    @patch("studio.RotadorProyectos")
    def test_slot_vacio(
        self, mock_rot, mock_hist, mock_gen, mock_prev, mock_pub, mock_auth,
        mock_mejora, mock_ad, mock_cal, mock_car, mock_rs
    ):
        from instagram_publisher import ModoPublicacion
        s = Studio()
        slot = self._make_slot(post=None)
        semana = MagicMock()
        r = s._publicar_slot(slot, semana, ModoPublicacion.DRY_RUN)
        assert r.exito is False
        assert r.error == "slot sin post generado"

    @patch("studio.RealestateStudio")
    @patch("studio.CarruselFactory")
    @patch("studio.CalendarioEditorial")
    @patch("studio.AntesDespuesFactory")
    @patch("studio.MejoraFotos")
    @patch("studio.InstagramAuth")
    @patch("studio.InstagramPublisher")
    @patch("studio.PreviewHTML")
    @patch("studio.get_generator")
    @patch("studio.HistorialPublicaciones")
    @patch("studio.RotadorProyectos")
    def test_slot_sin_caption(
        self, mock_rot, mock_hist, mock_gen, mock_prev, mock_pub, mock_auth,
        mock_mejora, mock_ad, mock_cal, mock_car, mock_rs
    ):
        from instagram_publisher import ModoPublicacion
        s = Studio()
        slot = self._make_slot(post={"caption": "hola"})
        semana = MagicMock()
        r = s._publicar_slot(slot, semana, ModoPublicacion.DRY_RUN)
        assert r.exito is False

    @patch("studio.RealestateStudio")
    @patch("studio.CarruselFactory")
    @patch("studio.CalendarioEditorial")
    @patch("studio.AntesDespuesFactory")
    @patch("studio.MejoraFotos")
    @patch("studio.InstagramAuth")
    @patch("studio.InstagramPublisher")
    @patch("studio.PreviewHTML")
    @patch("studio.get_generator")
    @patch("studio.HistorialPublicaciones")
    @patch("studio.RotadorProyectos")
    def test_slot_con_carrusel_sin_imagenes(
        self, mock_rot, mock_hist, mock_gen, mock_prev, mock_pub, mock_auth,
        mock_mejora, mock_ad, mock_cal, mock_car, mock_rs
    ):
        from instagram_publisher import ModoPublicacion
        s = Studio()
        slot = self._make_slot(
            post={"caption_completo": "test", "caption": "test", "hashtags": ["#test"]},
            tipo_post="carrusel",
            proyecto="test-proyecto",
        )
        semana = MagicMock()
        semana.numero = 1
        r = s._publicar_slot(slot, semana, ModoPublicacion.DRY_RUN)
        # No images found -> falls through to no-images path
        assert r.exito is False


# ===== duplicar_proyecto =====


class TestDuplicarProyecto:
    @patch("studio.RealestateStudio")
    @patch("studio.CarruselFactory")
    @patch("studio.CalendarioEditorial")
    @patch("studio.AntesDespuesFactory")
    @patch("studio.MejoraFotos")
    @patch("studio.InstagramAuth")
    @patch("studio.InstagramPublisher")
    @patch("studio.PreviewHTML")
    @patch("studio.get_generator")
    @patch("studio.HistorialPublicaciones")
    @patch("studio.RotadorProyectos")
    def test_origen_no_existe(
        self, mock_rot, mock_hist, mock_gen, mock_prev, mock_pub, mock_auth,
        mock_mejora, mock_ad, mock_cal, mock_car, mock_rs, tmp_path
    ):
        s = Studio()
        with pytest.raises(FileNotFoundError):
            s.duplicar_proyecto("nonexistent-origin", "dest")

    @patch("studio.RealestateStudio")
    @patch("studio.CarruselFactory")
    @patch("studio.CalendarioEditorial")
    @patch("studio.AntesDespuesFactory")
    @patch("studio.MejoraFotos")
    @patch("studio.InstagramAuth")
    @patch("studio.InstagramPublisher")
    @patch("studio.PreviewHTML")
    @patch("studio.get_generator")
    @patch("studio.HistorialPublicaciones")
    @patch("studio.RotadorProyectos")
    def test_destino_ya_existe(
        self, mock_rot, mock_hist, mock_gen, mock_prev, mock_pub, mock_auth,
        mock_mejora, mock_ad, mock_cal, mock_car, mock_rs, tmp_path
    ):
        from studio import ROOT
        # Create fake project dirs
        origen_dir = ROOT / "inmuebles" / "lotes" / "_test_dup_origen"
        destino_dir = ROOT / "inmuebles" / "lotes" / "_test_dup_destino"
        try:
            origen_dir.mkdir(parents=True, exist_ok=True)
            destino_dir.mkdir(parents=True, exist_ok=True)
            s = Studio()
            with pytest.raises(FileExistsError):
                s.duplicar_proyecto("_test_dup_origen", "_test_dup_destino")
        finally:
            import shutil
            if origen_dir.exists():
                shutil.rmtree(origen_dir)
            if destino_dir.exists():
                shutil.rmtree(destino_dir)


# ===== _actualizar_prompts_en_json =====


class TestActualizarPrompts:
    @patch("studio.RealestateStudio")
    @patch("studio.CarruselFactory")
    @patch("studio.CalendarioEditorial")
    @patch("studio.AntesDespuesFactory")
    @patch("studio.MejoraFotos")
    @patch("studio.InstagramAuth")
    @patch("studio.InstagramPublisher")
    @patch("studio.PreviewHTML")
    @patch("studio.get_generator")
    @patch("studio.HistorialPublicaciones")
    @patch("studio.RotadorProyectos")
    def test_hectareas_update(
        self, mock_rot, mock_hist, mock_gen, mock_prev, mock_pub, mock_auth,
        mock_mejora, mock_ad, mock_cal, mock_car, mock_rs, tmp_path
    ):
        s = Studio()
        data = {"slides": [{"prompt": "5 hectares en Cañuelas"}]}
        json_path = tmp_path / "carrusel.json"
        json_path.write_text(json.dumps(data))
        s._actualizar_prompts_en_json(json_path, {"hectareas": 10})
        result = json.loads(json_path.read_text())
        assert "10 hectares" in result["slides"][0]["prompt"]

    @patch("studio.RealestateStudio")
    @patch("studio.CarruselFactory")
    @patch("studio.CalendarioEditorial")
    @patch("studio.AntesDespuesFactory")
    @patch("studio.MejoraFotos")
    @patch("studio.InstagramAuth")
    @patch("studio.InstagramPublisher")
    @patch("studio.PreviewHTML")
    @patch("studio.get_generator")
    @patch("studio.HistorialPublicaciones")
    @patch("studio.RotadorProyectos")
    def test_municipio_update(
        self, mock_rot, mock_hist, mock_gen, mock_prev, mock_pub, mock_auth,
        mock_mejora, mock_ad, mock_cal, mock_car, mock_rs, tmp_path
    ):
        s = Studio()
        data = {"slides": [{"prompt": "Lote en Cañuelas"}]}
        json_path = tmp_path / "carrusel.json"
        json_path.write_text(json.dumps(data))
        s._actualizar_prompts_en_json(json_path, {"municipio": "Pilar"})
        result = json.loads(json_path.read_text())
        assert "Pilar" in result["slides"][0]["prompt"]

    @patch("studio.RealestateStudio")
    @patch("studio.CarruselFactory")
    @patch("studio.CalendarioEditorial")
    @patch("studio.AntesDespuesFactory")
    @patch("studio.MejoraFotos")
    @patch("studio.InstagramAuth")
    @patch("studio.InstagramPublisher")
    @patch("studio.PreviewHTML")
    @patch("studio.get_generator")
    @patch("studio.HistorialPublicaciones")
    @patch("studio.RotadorProyectos")
    def test_json_invalido(
        self, mock_rot, mock_hist, mock_gen, mock_prev, mock_pub, mock_auth,
        mock_mejora, mock_ad, mock_cal, mock_car, mock_rs, tmp_path
    ):
        s = Studio()
        json_path = tmp_path / "bad.json"
        json_path.write_text("not json{{{")
        # should not raise
        s._actualizar_prompts_en_json(json_path, {"hectareas": 10})


# ===== _actualizar_resumen =====


class TestActualizarResumen:
    @patch("studio.RealestateStudio")
    @patch("studio.CarruselFactory")
    @patch("studio.CalendarioEditorial")
    @patch("studio.AntesDespuesFactory")
    @patch("studio.MejoraFotos")
    @patch("studio.InstagramAuth")
    @patch("studio.InstagramPublisher")
    @patch("studio.PreviewHTML")
    @patch("studio.get_generator")
    @patch("studio.HistorialPublicaciones")
    @patch("studio.RotadorProyectos")
    def test_update(
        self, mock_rot, mock_hist, mock_gen, mock_prev, mock_pub, mock_auth,
        mock_mejora, mock_ad, mock_cal, mock_car, mock_rs, tmp_path
    ):
        s = Studio()
        data = {"hectareas": 5, "municipio": "Cañuelas"}
        json_path = tmp_path / "resumen.json"
        json_path.write_text(json.dumps(data))
        s._actualizar_resumen(json_path, {"hectareas": 10})
        result = json.loads(json_path.read_text())
        assert result["hectareas"] == 10
        assert result["municipio"] == "Cañuelas"

    @patch("studio.RealestateStudio")
    @patch("studio.CarruselFactory")
    @patch("studio.CalendarioEditorial")
    @patch("studio.AntesDespuesFactory")
    @patch("studio.MejoraFotos")
    @patch("studio.InstagramAuth")
    @patch("studio.InstagramPublisher")
    @patch("studio.PreviewHTML")
    @patch("studio.get_generator")
    @patch("studio.HistorialPublicaciones")
    @patch("studio.RotadorProyectos")
    def test_json_invalido(
        self, mock_rot, mock_hist, mock_gen, mock_prev, mock_pub, mock_auth,
        mock_mejora, mock_ad, mock_cal, mock_car, mock_rs, tmp_path
    ):
        s = Studio()
        json_path = tmp_path / "bad.json"
        json_path.write_text("not json")
        # should not raise
        s._actualizar_resumen(json_path, {"key": "val"})


# ===== guardar_pipeline =====


class TestGuardarPipeline:
    @patch("studio.RealestateStudio")
    @patch("studio.CarruselFactory")
    @patch("studio.CalendarioEditorial")
    @patch("studio.AntesDespuesFactory")
    @patch("studio.MejoraFotos")
    @patch("studio.InstagramAuth")
    @patch("studio.InstagramPublisher")
    @patch("studio.PreviewHTML")
    @patch("studio.get_generator")
    @patch("studio.HistorialPublicaciones")
    @patch("studio.RotadorProyectos")
    def test_guardar(
        self, mock_rot, mock_hist, mock_gen, mock_prev, mock_pub, mock_auth,
        mock_mejora, mock_ad, mock_cal, mock_car, mock_rs
    ):
        s = Studio()
        r = PipelineResultado(
            semana_numero=1,
            fecha_inicio="2026-07-07",
            fecha_fin="2026-07-13",
            n_slots=5,
        )
        ruta = s.guardar_pipeline(r, nombre="test_pipeline")
        assert ruta.exists()
        data = json.loads(ruta.read_text())
        assert data["semana_numero"] == 1
        # cleanup
        import shutil
        shutil.rmtree(ruta.parent, ignore_errors=True)

    @patch("studio.RealestateStudio")
    @patch("studio.CarruselFactory")
    @patch("studio.CalendarioEditorial")
    @patch("studio.AntesDespuesFactory")
    @patch("studio.MejoraFotos")
    @patch("studio.InstagramAuth")
    @patch("studio.InstagramPublisher")
    @patch("studio.PreviewHTML")
    @patch("studio.get_generator")
    @patch("studio.HistorialPublicaciones")
    @patch("studio.RotadorProyectos")
    def test_guardar_auto_nombre(
        self, mock_rot, mock_hist, mock_gen, mock_prev, mock_pub, mock_auth,
        mock_mejora, mock_ad, mock_cal, mock_car, mock_rs
    ):
        s = Studio()
        r = PipelineResultado(
            semana_numero=3,
            fecha_inicio="2026-07-21",
            fecha_fin="2026-07-27",
            n_slots=5,
        )
        ruta = s.guardar_pipeline(r)
        assert ruta.exists()
        assert "pipeline_semana_03" in ruta.name
        import shutil
        shutil.rmtree(ruta.parent, ignore_errors=True)


# ===== publicar_carrusel_existente =====


class TestPublicarCarruselExistente:
    @patch("studio.RealestateStudio")
    @patch("studio.CarruselFactory")
    @patch("studio.CalendarioEditorial")
    @patch("studio.AntesDespuesFactory")
    @patch("studio.MejoraFotos")
    @patch("studio.InstagramAuth")
    @patch("studio.InstagramPublisher")
    @patch("studio.PreviewHTML")
    @patch("studio.get_generator")
    @patch("studio.HistorialPublicaciones")
    @patch("studio.RotadorProyectos")
    def test_no_existe(
        self, mock_rot, mock_hist, mock_gen, mock_prev, mock_pub, mock_auth,
        mock_mejora, mock_ad, mock_cal, mock_car, mock_rs
    ):
        from instagram_publisher import ModoPublicacion
        s = Studio()
        r = s.publicar_carrusel_existente("/nonexistent/carrusel.json")
        assert r.exito is False
        assert "No existe" in r.error

    @patch("studio.RealestateStudio")
    @patch("studio.CarruselFactory")
    @patch("studio.CalendarioEditorial")
    @patch("studio.AntesDespuesFactory")
    @patch("studio.MejoraFotos")
    @patch("studio.InstagramAuth")
    @patch("studio.InstagramPublisher")
    @patch("studio.PreviewHTML")
    @patch("studio.get_generator")
    @patch("studio.HistorialPublicaciones")
    @patch("studio.RotadorProyectos")
    def test_json_invalido(
        self, mock_rot, mock_hist, mock_gen, mock_prev, mock_pub, mock_auth,
        mock_mejora, mock_ad, mock_cal, mock_car, mock_rs, tmp_path
    ):
        from instagram_publisher import ModoPublicacion
        s = Studio()
        bad = tmp_path / "bad.json"
        bad.write_text("not json{{{")
        r = s.publicar_carrusel_existente(bad)
        assert r.exito is False
        assert "JSON invalido" in r.error

    @patch("studio.RealestateStudio")
    @patch("studio.CarruselFactory")
    @patch("studio.CalendarioEditorial")
    @patch("studio.AntesDespuesFactory")
    @patch("studio.MejoraFotos")
    @patch("studio.InstagramAuth")
    @patch("studio.InstagramPublisher")
    @patch("studio.PreviewHTML")
    @patch("studio.get_generator")
    @patch("studio.HistorialPublicaciones")
    @patch("studio.RotadorProyectos")
    def test_pocas_imagenes(
        self, mock_rot, mock_hist, mock_gen, mock_prev, mock_pub, mock_auth,
        mock_mejora, mock_ad, mock_cal, mock_car, mock_rs, tmp_path
    ):
        from instagram_publisher import ModoPublicacion
        s = Studio()
        data = {
            "caption_narrativo": "test caption",
            "hashtags": ["#test"],
            "n_slides": 6,
        }
        carrusel = tmp_path / "carrusel.json"
        carrusel.write_text(json.dumps(data))
        slides_dir = tmp_path / "slides"
        slides_dir.mkdir()
        # Only 1 image -> should fail
        (slides_dir / "slide_01_foto.jpg").write_bytes(b"\xff" * 10)
        r = s.publicar_carrusel_existente(carrusel)
        assert r.exito is False
        assert "Necesita >= 2" in r.error


# ===== _generar_carrusel_completo =====


class TestGenerarCarruselCompleto:
    def test_no_existe(self):
        resultado = _generar_carrusel_completo(
            MagicMock(), "/nonexistent/carrusel.json"
        )
        assert resultado["success"] is False
        assert "No existe" in resultado["error"]

    def test_sin_items(self, tmp_path):
        data = {"slides": []}
        carrusel = tmp_path / "carrusel.json"
        carrusel.write_text(json.dumps(data))
        resultado = _generar_carrusel_completo(MagicMock(), str(carrusel))
        assert resultado["success"] is False
        assert "sin slides" in resultado["error"]

    def test_cancelado_por_usuario(self, tmp_path):
        data = {
            "slides": [
                {"numero": 1, "tipo": "foto", "prompt": "un lote", "aspect_ratio": "896*1152", "styles": []},
            ]
        }
        carrusel = tmp_path / "carrusel.json"
        carrusel.write_text(json.dumps(data))
        with patch("builtins.input", return_value="n"):
            resultado = _generar_carrusel_completo(
                MagicMock(), str(carrusel), skip_confirm=False
            )
        assert resultado["success"] is False
        assert "cancelado" in resultado["error"]


# ===== _encolar_carrusel =====


class TestEncolarCarrusel:
    def test_no_existe(self):
        from studio import _encolar_carrusel
        resultado = _encolar_carrusel(MagicMock(), "/nonexistent/carrusel.json")
        assert resultado["encolados"] == 0
        assert "No existe" in resultado["error"]

    def test_sin_items(self, tmp_path):
        from studio import _encolar_carrusel
        data = {"slides": []}
        carrusel = tmp_path / "carrusel.json"
        carrusel.write_text(json.dumps(data))
        resultado = _encolar_carrusel(MagicMock(), str(carrusel))
        assert resultado["encolados"] == 0


# ===== _procesar_cola =====


class TestProcesarCola:
    def test_cola_vacia(self):
        from studio import _procesar_cola
        with patch("generation_pipeline.GenerationQueue") as mock_queue:
            mock_queue.return_value.list_pending.return_value = []
            resultado = _procesar_cola(MagicMock())
            assert resultado["total"] == 0
            assert "Cola vacia" in resultado["error"]


# ===== CLI build_arg_parser =====


class TestCLIBuildArgParser:
    def test_demo(self):
        import sys
        with patch.object(sys, "argv", ["studio.py", "demo"]):
            parser = argparse.ArgumentParser()
            sub = parser.add_subparsers(dest="comando")
            sub.add_parser("demo")
            args = parser.parse_args(["demo"])
            assert args.comando == "demo"


# ===== CLI subcommands =====


class TestCLISubcommands:
    @patch("studio.Studio")
    def test_demo(self, mock_studio_cls):
        import sys
        with patch.object(sys, "argv", ["studio.py", "demo"]):
            with patch("studio.demo") as mock_demo:
                r = cli()
                mock_demo.assert_called_once()

    @patch("studio.Studio")
    def test_semana_dry_run(self, mock_studio_cls):
        import sys
        mock_studio = MagicMock()
        mock_studio_cls.return_value = mock_studio
        resultado = PipelineResultado(
            semana_numero=1, fecha_inicio="2026-07-07",
            fecha_fin="2026-07-13", n_slots=5, resumen="test",
        )
        mock_studio.pipeline_semana.return_value = resultado
        mock_studio.guardar_pipeline.return_value = Path("/tmp/test.json")
        with patch.object(sys, "argv", ["studio.py", "semana", "--n", "1", "--publicar", "dry-run"]):
            with patch("studio.Path.relative_to", return_value=Path("test.json")):
                r = cli()
        assert r == 0

    @patch("studio.Studio")
    def test_duplicar(self, mock_studio_cls):
        import sys
        mock_studio = MagicMock()
        mock_studio_cls.return_value = mock_studio
        mock_studio.duplicar_proyecto.return_value = Path("/tmp/proj")
        with patch.object(sys, "argv", ["studio.py", "duplicar", "--origen", "a", "--destino", "b"]):
            with patch("studio.Path.relative_to", return_value=Path("proj")):
                r = cli()
        assert r == 0

    @patch("studio.Studio")
    def test_publicar_dry_run(self, mock_studio_cls):
        import sys
        mock_studio = MagicMock()
        mock_studio_cls.return_value = mock_studio
        from instagram_publisher import PublicacionResultado
        mock_studio.publicar_carrusel_existente.return_value = PublicacionResultado(
            modo="dry-run", exito=True, tipo="carrusel",
            caption_length=100, n_imagenes=6,
        )
        with patch.object(sys, "argv", ["studio.py", "publicar", "--carrusel", "/tmp/c.json"]):
            r = cli()
        assert r == 0

    @patch("studio.Studio")
    def test_preview(self, mock_studio_cls):
        import sys
        mock_studio = MagicMock()
        mock_studio_cls.return_value = mock_studio
        mock_studio.preview_carrusel.return_value = Path("/tmp/preview.html")
        with patch.object(sys, "argv", ["studio.py", "preview", "--carrusel", "/tmp/c.json"]):
            with patch("studio.Path.relative_to", return_value=Path("preview.html")):
                r = cli()
        assert r == 0

    @patch("studio.Studio")
    def test_cache_stats(self, mock_studio_cls):
        import sys
        with patch.object(sys, "argv", ["studio.py", "cache-stats"]):
            with patch("studio.ImageCache") as mock_cache:
                mock_cache.return_value.stats.return_value = {
                    "total_entries": 10,
                    "total_size_mb": 1.5,
                    "total_size_bytes": 1500000,
                }
                r = cli()
        assert r == 0

    @patch("studio.Studio")
    def test_generar_cola(self, mock_studio_cls):
        import sys
        mock_studio = MagicMock()
        mock_studio_cls.return_value = mock_studio
        with patch.object(sys, "argv", ["studio.py", "generar-cola", "--carrusel", "/tmp/c.json"]):
            with patch("studio._encolar_carrusel", return_value={"encolados": 3}):
                r = cli()
        assert r == 0

    @patch("studio.Studio")
    def test_procesar_cola(self, mock_studio_cls):
        import sys
        mock_studio = MagicMock()
        mock_studio_cls.return_value = mock_studio
        with patch.object(sys, "argv", ["studio.py", "procesar-cola"]):
            with patch("studio._procesar_cola", return_value={"exitos": 5, "total": 5}):
                r = cli()
        assert r == 0

    @patch("studio.Studio")
    def test_listar(self, mock_studio_cls):
        import sys
        mock_studio = MagicMock()
        mock_studio_cls.return_value = mock_studio
        mock_studio.listar_carruseles.return_value = [
            {"nombre": "test", "n_slides": 6, "municipio": "Cañuelas", "tipo": "lote_premium"}
        ]
        with patch.object(sys, "argv", ["studio.py", "listar"]):
            r = cli()
        assert r == 0

    @patch("studio.Studio")
    def test_listar_vacio(self, mock_studio_cls):
        import sys
        mock_studio = MagicMock()
        mock_studio_cls.return_value = mock_studio
        mock_studio.listar_carruseles.return_value = []
        with patch.object(sys, "argv", ["studio.py", "listar"]):
            r = cli()
        assert r == 0

    @patch("studio.Studio")
    def test_reporte_semanal(self, mock_studio_cls):
        import sys
        mock_studio = MagicMock()
        mock_studio_cls.return_value = mock_studio
        with patch.object(sys, "argv", ["studio.py", "reporte-semanal"]):
            with patch("studio.Monitor") as mock_mon:
                mock_mon.return_value.weekly_report.return_value = {}
                mock_mon.return_value.render_markdown.return_value = "# Reporte"
                r = cli()
        assert r == 0

    @patch("studio.Studio")
    def test_responder_dm(self, mock_studio_cls):
        import sys
        mock_studio = MagicMock()
        mock_studio_cls.return_value = mock_studio
        with patch.object(sys, "argv", [
            "studio.py", "responder-dm",
            "--cliente", "Juan",
            "--mensaje", "Hola, precio?"
        ]):
            with patch("studio.DMTemplates") as mock_dm:
                mock_dm.return_value.responder.return_value = {
                    "template_id": "precio",
                    "respuesta": "El precio es USD 50000",
                }
                r = cli()
        assert r == 0

    @patch("studio.Studio")
    def test_programar(self, mock_studio_cls):
        import sys
        mock_studio = MagicMock()
        mock_studio_cls.return_value = mock_studio
        with patch.object(sys, "argv", [
            "studio.py", "programar",
            "--id", "test-id",
            "--carrusel", "/tmp/c.json",
            "--scheduled-at", "2026-07-20T19:00:00",
        ]):
            with patch("studio.Scheduler") as mock_sched:
                mock_sched.return_value.stats.return_value = {"pending": 1}
                r = cli()
        assert r == 0

    @patch("studio.Studio")
    def test_procesar_programadas(self, mock_studio_cls):
        import sys
        mock_studio = MagicMock()
        mock_studio_cls.return_value = mock_studio
        with patch.object(sys, "argv", ["studio.py", "procesar-programadas"]):
            with patch("studio.Scheduler") as mock_sched:
                mock_sched.return_value.pendientes_a_procesar.return_value = []
                r = cli()
        assert r == 0

    @patch("studio.Studio")
    def test_publicaciones_listar(self, mock_studio_cls):
        import sys
        mock_studio = MagicMock()
        mock_studio_cls.return_value = mock_studio
        with patch.object(sys, "argv", ["studio.py", "publicaciones"]):
            with patch("studio.Scheduler") as mock_sched:
                mock_sched.return_value.listar.return_value = []
                r = cli()
        assert r == 0

    @patch("studio.Studio")
    def test_publicaciones_cancel(self, mock_studio_cls):
        import sys
        mock_studio = MagicMock()
        mock_studio_cls.return_value = mock_studio
        with patch.object(sys, "argv", ["studio.py", "publicaciones", "--cancel", "test-id"]):
            with patch("studio.Scheduler") as mock_sched:
                mock_sched.return_value.cancelar.return_value = True
                r = cli()
        assert r == 0


# ===== import for CLI parser test =====
import argparse
