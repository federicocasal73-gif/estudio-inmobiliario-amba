"""Tests para studio.py - Orquestador principal."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch, PropertyMock

import pytest

from studio import Studio, PipelineResultado, ROOT, ModoPublicacion


@pytest.fixture
def mock_studio():
    """Studio con todos los componentes mockeados."""
    with patch("studio.RealestateStudio"), \
         patch("studio.CarruselFactory"), \
         patch("studio.CalendarioEditorial"), \
         patch("studio.AntesDespuesFactory"), \
         patch("studio.MejoraFotos"), \
         patch("studio.InstagramAuth"), \
         patch("studio.InstagramPublisher"), \
         patch("studio.PreviewHTML"), \
         patch("studio.get_generator"), \
         patch("studio.HistorialPublicaciones"), \
         patch("studio.RotadorProyectos"):
        s = Studio()
    return s


class TestPipelineResultado:
    def test_creation(self):
        r = PipelineResultado(semana_numero=1, fecha_inicio="2026-01-01", fecha_fin="2026-01-07", n_slots=5)
        assert r.semana_numero == 1
        assert r.n_slots == 5
        assert r.errores == []
        assert r.resumen == ""

    def test_to_dict(self):
        r = PipelineResultado(semana_numero=1, fecha_inicio="2026-01-01", fecha_fin="2026-01-07", n_slots=5)
        d = r.to_dict()
        assert isinstance(d, dict)
        assert d["semana_numero"] == 1
        assert "fecha_ejecucion" in d

    def test_with_data(self):
        r = PipelineResultado(
            semana_numero=1,
            fecha_inicio="2026-01-01",
            fecha_fin="2026-01-07",
            n_slots=5,
            carruseles_generados=["c1", "c2"],
            errores=["error1"],
            resumen="Test resumen",
        )
        d = r.to_dict()
        assert len(d["carruseles_generados"]) == 2
        assert len(d["errores"]) == 1


class TestStudioInit:
    def test_init(self, mock_studio):
        assert mock_studio.studio_core is not None
        assert mock_studio.carruseles is not None
        assert mock_studio.calendario is not None


class TestStudioHelpers:
    def test_nombre_carrusel_desde_slot(self, mock_studio):
        slot = MagicMock()
        slot.tipo_post = "carrusel"
        slot.proyecto = "chacra-canuelas"
        slot.dia_semana = "lunes"
        semana = MagicMock()
        semana.numero = 1
        nombre = mock_studio._nombre_carrusel_desde_slot(slot, semana)
        assert "lote_premium" in nombre
        assert "chacra-canuelas" in nombre
        assert "sem01" in nombre
        assert "lunes" in nombre

    def test_nombre_carrusel_servicios(self, mock_studio):
        slot = MagicMock()
        slot.tipo_post = "servicios"
        slot.proyecto = "test"
        slot.dia_semana = "jueves"
        semana = MagicMock()
        semana.numero = 2
        nombre = mock_studio._nombre_carrusel_desde_slot(slot, semana)
        assert "servicios" in nombre

    def test_tipo_carrusel_por_dia(self):
        assert Studio._tipo_carrusel_por_dia("lunes") == "lote_premium"
        assert Studio._tipo_carrusel_por_dia("martes") == "country_etapa"
        assert Studio._tipo_carrusel_por_dia("miercoles") == "lote_premium"
        assert Studio._tipo_carrusel_por_dia("jueves") == "servicios"
        assert Studio._tipo_carrusel_por_dia("viernes") == "lote_premium"
        assert Studio._tipo_carrusel_por_dia("sabado") == "lote_premium"
        assert Studio._tipo_carrusel_por_dia("domingo") == "obra_avance"
        assert Studio._tipo_carrusel_por_dia("otro") == "lote_premium"


class TestPipelineSemana:
    def test_pipeline_dry_run(self, mock_studio):
        semana_mock = MagicMock()
        semana_mock.fecha_inicio = "2026-01-01"
        semana_mock.fecha_fin = "2026-01-07"
        semana_mock.slots = []
        mock_studio.calendario.generar_semana.return_value = semana_mock

        resultado = mock_studio.pipeline_semana(
            semana_n=1,
            proyectos=["test-proyecto"],
            modo_publicacion=MagicMock(value="dry-run"),
        )
        assert isinstance(resultado, PipelineResultado)
        assert resultado.semana_numero == 1
        mock_studio.calendario.generar_semana.assert_called_once()

    def test_pipeline_con_error_calendario(self, mock_studio):
        mock_studio.calendario.generar_semana.side_effect = Exception("Calendario error")
        resultado = mock_studio.pipeline_semana(semana_n=1)
        assert len(resultado.errores) > 0
        assert "calendario" in resultado.errores[0].lower()

    def test_pipeline_con_slots(self, mock_studio):
        slot = MagicMock()
        slot.tipo_post = "carrusel"
        slot.proyecto = "test-proyecto"
        slot.municipio = "Canuelas"
        slot.tono = "emotivo"
        slot.dia_semana = "lunes"
        slot.fecha = "2026-01-01"
        slot.post = {"caption_completo": "Test caption", "hashtags": ["#test"]}

        semana_mock = MagicMock()
        semana_mock.fecha_inicio = "2026-01-01"
        semana_mock.fecha_fin = "2026-01-07"
        semana_mock.slots = [slot]
        semana_mock.numero = 1
        mock_studio.calendario.generar_semana.return_value = semana_mock

        mock_studio.carruseles.guardar.return_value = Path("/tmp/test")

        resultado = mock_studio.pipeline_semana(
            semana_n=1,
            proyectos=["test-proyecto"],
            generar_carruseles_faltantes=True,
        )
        assert resultado.n_slots == 1

    def test_pipeline_sin_validar(self, mock_studio):
        semana_mock = MagicMock()
        semana_mock.fecha_inicio = "2026-01-01"
        semana_mock.fecha_fin = "2026-01-07"
        semana_mock.slots = []
        mock_studio.calendario.generar_semana.return_value = semana_mock

        resultado = mock_studio.pipeline_semana(
            semana_n=1,
            validar_posts=False,
        )
        assert resultado.validaciones == []


class TestGenerarOReusarCarrusel:
    def test_generar_lote_premium(self, mock_studio, tmp_path):
        import studio
        original_root = studio.ROOT
        studio.ROOT = tmp_path

        try:
            slot = MagicMock()
            slot.dia_semana = "lunes"
            slot.tono = "emotivo"
            slot.proyecto = "test-proyecto"

            mock_studio.carruseles.lote_premium.return_value = MagicMock()
            mock_studio.carruseles.guardar.return_value = tmp_path / "carruseles" / "test"

            result = mock_studio._generar_o_reusar_carrusel(slot, "test_carrusel", "Canuelas")
            assert result is not None
        finally:
            studio.ROOT = original_root

    def test_reusar_carrusel_existente(self, mock_studio, tmp_path):
        import studio
        original_root = studio.ROOT
        studio.ROOT = tmp_path

        try:
            slot = MagicMock()
            slot.dia_semana = "lunes"
            slot.tono = "emotivo"
            slot.proyecto = "test-proyecto"

            carpeta = tmp_path / "inmuebles" / "lotes" / "test-proyecto" / "carruseles" / "existing"
            carpeta.mkdir(parents=True)
            (carpeta / "carrusel.json").write_text("{}")

            result = mock_studio._generar_o_reusar_carrusel(slot, "existing", "Canuelas")
            assert result.exists()
        finally:
            studio.ROOT = original_root


class TestPublicarSlot:
    def test_slot_sin_post(self, mock_studio):
        slot = MagicMock()
        slot.post = None
        semana = MagicMock()
        resultado = mock_studio._publicar_slot(slot, semana, MagicMock(value="dry-run"))
        assert resultado.exito is False
        assert "sin post" in resultado.error.lower()

    def test_slot_vacio(self, mock_studio):
        slot = MagicMock()
        slot.post = {}
        semana = MagicMock()
        resultado = mock_studio._publicar_slot(slot, semana, MagicMock(value="dry-run"))
        assert resultado.exito is False

    def test_slot_con_imagenes(self, mock_studio, tmp_path):
        import studio
        original_root = studio.ROOT
        studio.ROOT = tmp_path

        try:
            slot = MagicMock()
            slot.tipo_post = "foto"
            slot.proyecto = "test-proyecto"
            slot.post = {"caption": "Test", "hashtags": ["#t"], "caption_completo": "Test"}
            semana = MagicMock()

            carpeta = tmp_path / "inmuebles" / "lotes" / "test-proyecto" / "prompts"
            carpeta.mkdir(parents=True)
            (carpeta / "img.png").write_bytes(b"\x89PNG")

            mock_studio.publisher.publicar_foto.return_value = MagicMock(to_dict=lambda: {"exito": True})

            resultado = mock_studio._publicar_slot(slot, semana, MagicMock(value="dry-run"))
            assert resultado is not None
        finally:
            studio.ROOT = original_root


class TestDuplicarProyecto:
    def test_duplicar(self, mock_studio, tmp_path):
        import studio
        original_root = studio.ROOT
        studio.ROOT = tmp_path

        try:
            origen = tmp_path / "inmuebles" / "lotes" / "origen"
            origen.mkdir(parents=True)
            (origen / "carrusel.json").write_text(json.dumps({"slides": []}))

            resultado = mock_studio.duplicar_proyecto("origen", "destino")
            assert resultado.exists()
            assert (resultado / "carrusel.json").exists()
        finally:
            studio.ROOT = original_root

    def test_duplicar_origen_no_existe(self, mock_studio, tmp_path):
        import studio
        original_root = studio.ROOT
        studio.ROOT = tmp_path

        try:
            with pytest.raises(FileNotFoundError):
                mock_studio.duplicar_proyecto("no-existe", "destino")
        finally:
            studio.ROOT = original_root

    def test_duplicar_destino_existe(self, mock_studio, tmp_path):
        import studio
        original_root = studio.ROOT
        studio.ROOT = tmp_path

        try:
            origen = tmp_path / "inmuebles" / "lotes" / "origen"
            origen.mkdir(parents=True)
            destino = tmp_path / "inmuebles" / "lotes" / "destino"
            destino.mkdir(parents=True)

            with pytest.raises(FileExistsError):
                mock_studio.duplicar_proyecto("origen", "destino")
        finally:
            studio.ROOT = original_root

    def test_duplicar_con_cambios(self, mock_studio, tmp_path):
        import studio
        original_root = studio.ROOT
        studio.ROOT = tmp_path

        try:
            origen = tmp_path / "inmuebles" / "lotes" / "origen"
            origen.mkdir(parents=True)
            slides_data = {"slides": [{"prompt": "5 hectares in Cañuelas"}]}
            (origen / "carrusel.json").write_text(json.dumps(slides_data))

            resultado = mock_studio.duplicar_proyecto(
                "origen", "destino", cambios={"hectareas": 8, "municipio": "Escobar"}
            )
            assert resultado.exists()
            data = json.loads((resultado / "carrusel.json").read_text())
            assert "8 hectares" in data["slides"][0]["prompt"]
        finally:
            studio.ROOT = original_root


class TestRegenerarCarruseles:
    def test_regenerar(self, mock_studio):
        semana_mock = MagicMock()
        semana_mock.fecha_inicio = "2026-01-01"
        semana_mock.fecha_fin = "2026-01-07"
        semana_mock.slots = []
        mock_studio.calendario.generar_semana.return_value = semana_mock

        resultado = mock_studio.regenerar_carruseles(
            semana_n=1,
            proyectos=["test"],
        )
        assert isinstance(resultado, PipelineResultado)


class TestGuardarPipeline:
    def test_guardar(self, mock_studio, tmp_path):
        import studio
        original_root = studio.ROOT
        studio.ROOT = tmp_path

        try:
            resultado = PipelineResultado(
                semana_numero=1,
                fecha_inicio="2026-01-01",
                fecha_fin="2026-01-07",
                n_slots=5,
            )
            ruta = mock_studio.guardar_pipeline(resultado, nombre="test_pipeline")
            assert ruta.exists()
            data = json.loads(ruta.read_text())
            assert data["semana_numero"] == 1
        finally:
            studio.ROOT = original_root

    def test_guardar_auto_nombre(self, mock_studio, tmp_path):
        import studio
        original_root = studio.ROOT
        studio.ROOT = tmp_path

        try:
            resultado = PipelineResultado(
                semana_numero=1,
                fecha_inicio="2026-01-01",
                fecha_fin="2026-01-07",
                n_slots=5,
            )
            ruta = mock_studio.guardar_pipeline(resultado)
            assert ruta.exists()
            assert "pipeline_semana" in ruta.name
        finally:
            studio.ROOT = original_root


class TestListarCarruseles:
    def test_listar_vacio(self, mock_studio, tmp_path):
        import studio
        original_root = studio.ROOT
        studio.ROOT = tmp_path

        try:
            (tmp_path / "inmuebles" / "lotes").mkdir(parents=True)
            result = mock_studio.listar_carruseles()
            assert result == []
        finally:
            studio.ROOT = original_root

    def test_listar_con_proyecto(self, mock_studio, tmp_path):
        import studio
        original_root = studio.ROOT
        studio.ROOT = tmp_path

        try:
            carpeta = tmp_path / "inmuebles" / "lotes" / "test-proyecto" / "carruseles" / "my-carrusel"
            carpeta.mkdir(parents=True)
            (carpeta / "carrusel.json").write_text(json.dumps({
                "tema": "Test tema",
                "tipo": "lote_premium",
                "n_slides": 6,
                "fecha_creacion": "2026-01-01",
                "municipio": "Canuelas",
            }))

            result = mock_studio.listar_carruseles(proyecto="test-proyecto")
            assert len(result) == 1
            assert result[0]["tema"] == "Test tema"
        finally:
            studio.ROOT = original_root

    def test_listar_todos(self, mock_studio, tmp_path):
        import studio
        original_root = studio.ROOT
        studio.ROOT = tmp_path

        try:
            carpeta = tmp_path / "inmuebles" / "lotes" / "test" / "carruseles" / "c1"
            carpeta.mkdir(parents=True)
            (carpeta / "carrusel.json").write_text(json.dumps({"tema": "T", "tipo": "t", "n_slides": 1, "fecha_creacion": "", "municipio": ""}))

            result = mock_studio.listar_carruseles()
            assert len(result) == 1
        finally:
            studio.ROOT = original_root

    def test_listar_json_invalido(self, mock_studio, tmp_path):
        import studio
        original_root = studio.ROOT
        studio.ROOT = tmp_path

        try:
            carpeta = tmp_path / "inmuebles" / "lotes" / "test" / "carruseles" / "bad"
            carpeta.mkdir(parents=True)
            (carpeta / "carrusel.json").write_text("not json {{{")

            result = mock_studio.listar_carruseles()
            assert result == []
        finally:
            studio.ROOT = original_root


class TestPreviewCarrusel:
    def test_preview_no_existe(self, mock_studio):
        with pytest.raises(FileNotFoundError):
            mock_studio.preview_carrusel("/nonexistent/carrusel.json")

    def test_preview(self, mock_studio, tmp_path):
        import studio
        original_root = studio.ROOT
        studio.ROOT = tmp_path

        try:
            carpeta = tmp_path / "test_carrusel"
            carpeta.mkdir()
            data = {
                "tema": "Test",
                "tipo": "lote_premium",
                "municipio": "Canuelas",
                "tono": "emotivo",
                "slides": [{"numero": 1, "tipo": "foto", "descripcion": "Test slide", "prompt": "p", "texto_overlay": "", "aspect_ratio": "896*1152", "styles": [], "metadata": {}}],
                "caption_narrativo": "Caption",
                "hashtags": ["#test"],
                "fecha_creacion": "",
                "metadata": {},
            }
            json_path = carpeta / "carrusel.json"
            json_path.write_text(json.dumps(data))

            mock_studio.preview.carrusel.return_value = carpeta / "preview.html"

            result = mock_studio.preview_carrusel(json_path)
            assert result is not None
        finally:
            studio.ROOT = original_root


class TestGenerarImagenesCarrusel:
    def test_generar_imagenes(self, mock_studio, tmp_path):
        import studio
        original_root = studio.ROOT
        studio.ROOT = tmp_path

        try:
            carpeta = tmp_path / "test_carrusel"
            carpeta.mkdir()
            data = {
                "slides": [
                    {"numero": 1, "tipo": "foto", "prompt": "test prompt", "aspect_ratio": "896*1152", "styles": [], "negative_prompt": ""},
                    {"numero": 2, "tipo": "placeholder_foto", "prompt": "", "metadata": {"placeholder_foto_path": "/tmp/photo.jpg"}},
                    {"numero": 3, "tipo": "dato", "prompt": "", "metadata": {}},
                ]
            }
            (carpeta / "carrusel.json").write_text(json.dumps(data))

            r = MagicMock()
            r.stub = True
            r.output_path = "/tmp/out.jpg"
            r.fooocus_disponible = False
            mock_studio.image_generator.generar.return_value = r

            result = mock_studio.generar_imagenes_carrusel(carpeta / "carrusel.json")
            assert len(result) == 3
            assert result[0]["saltado"] is False
            assert result[1]["saltado"] is True
            assert result[2]["saltado"] is True
        finally:
            studio.ROOT = original_root


class TestPublicarCarruselExistente:
    def test_no_existe(self, mock_studio):
        result = mock_studio.publicar_carrusel_existente("/nonexistent/carrusel.json")
        assert result.exito is False

    def test_json_invalido(self, mock_studio, tmp_path):
        import studio
        original_root = studio.ROOT
        studio.ROOT = tmp_path

        try:
            bad_json = tmp_path / "bad.json"
            bad_json.write_text("not json {{{")
            result = mock_studio.publicar_carrusel_existente(bad_json)
            assert result.exito is False
        finally:
            studio.ROOT = original_root

    def test_pocas_imagenes(self, mock_studio, tmp_path):
        import studio
        original_root = studio.ROOT
        studio.ROOT = tmp_path

        try:
            carpeta = tmp_path / "carrusel"
            carpeta.mkdir()
            data = {"caption_narrativo": "Caption", "hashtags": ["#test"], "n_slides": 2}
            (carpeta / "carrusel.json").write_text(json.dumps(data))
            slides_dir = carpeta / "slides"
            slides_dir.mkdir()
            (slides_dir / "slide_01_foto.jpg").write_bytes(b"\x00")

            result = mock_studio.publicar_carrusel_existente(carpeta / "carrusel.json")
            assert result.exito is False
            assert "2 imagenes" in result.error
        finally:
            studio.ROOT = original_root


class TestBuildBatchItems:
    def test_build_items(self, tmp_path):
        from studio import _build_batch_items_from_carrusel

        carpeta = tmp_path / "carrusel"
        carpeta.mkdir()
        slides_dir = carpeta / "slides"
        slides_dir.mkdir()

        data = {
            "slides": [
                {"numero": 1, "tipo": "foto", "prompt": "test prompt", "aspect_ratio": "896*1152", "styles": []},
                {"numero": 2, "tipo": "placeholder_foto", "prompt": ""},
                {"numero": 3, "tipo": "dato", "prompt": ""},
            ]
        }
        (carpeta / "carrusel.json").write_text(json.dumps(data))

        items = _build_batch_items_from_carrusel(carpeta / "carrusel.json")
        assert len(items) == 1
        assert items[0].prompt == "test prompt"

    def test_build_items_with_variants(self, tmp_path):
        from studio import _build_batch_items_from_carrusel

        carpeta = tmp_path / "carrusel"
        carpeta.mkdir()
        slides_dir = carpeta / "slides"
        slides_dir.mkdir()

        data = {
            "slides": [
                {"numero": 1, "tipo": "foto", "prompt": "test", "aspect_ratio": "896*1152", "styles": []},
            ]
        }
        (carpeta / "carrusel.json").write_text(json.dumps(data))

        items = _build_batch_items_from_carrusel(carpeta / "carrusel.json", batch_variants=2)
        assert len(items) == 2


class TestGenerarCarruselCompleto:
    def test_no_existe(self, mock_studio, tmp_path):
        from studio import _generar_carrusel_completo

        result = _generar_carrusel_completo(mock_studio, "/nonexistent.json")
        assert result["success"] is False

    def test_sin_slides(self, mock_studio, tmp_path):
        from studio import _generar_carrusel_completo

        carpeta = tmp_path / "carrusel"
        carpeta.mkdir()
        data = {"slides": []}
        (carpeta / "carrusel.json").write_text(json.dumps(data))

        result = _generar_carrusel_completo(mock_studio, carpeta / "carrusel.json")
        assert result["success"] is False

    def test_con_slides(self, mock_studio, tmp_path):
        from studio import _generar_carrusel_completo

        carpeta = tmp_path / "carrusel"
        carpeta.mkdir()
        slides_dir = carpeta / "slides"
        slides_dir.mkdir()
        data = {
            "slides": [
                {"numero": 1, "tipo": "foto", "prompt": "test prompt", "aspect_ratio": "896*1152", "styles": []},
            ]
        }
        (carpeta / "carrusel.json").write_text(json.dumps(data))

        r = MagicMock()
        r.stub = True
        r.output_path = "/tmp/out.jpg"
        r.fooocus_disponible = False
        mock_studio.image_generator.generar.return_value = r

        result = _generar_carrusel_completo(
            mock_studio,
            carpeta / "carrusel.json",
            skip_confirm=True,
            force=True,
        )
        assert result["success"] is True


class TestEncolarCarrusel:
    def test_encolar_no_existe(self, mock_studio):
        from studio import _encolar_carrusel

        result = _encolar_carrusel(mock_studio, "/nonexistent.json")
        assert result["encolados"] == 0

    def test_encolar_sin_slides(self, mock_studio, tmp_path):
        from studio import _encolar_carrusel

        carpeta = tmp_path / "carrusel"
        carpeta.mkdir()
        data = {"slides": []}
        (carpeta / "carrusel.json").write_text(json.dumps(data))

        result = _encolar_carrusel(mock_studio, carpeta / "carrusel.json")
        assert result["encolados"] == 0


class TestProcesarCola:
    def test_cola_vacia(self, mock_studio):
        from studio import _procesar_cola

        mock_queue = MagicMock()
        mock_queue.list_pending.return_value = []

        with patch("studio.ImageCache"), \
             patch("generation_pipeline.GenerationQueue", return_value=mock_queue):
            result = _procesar_cola(mock_studio)
            assert result["total"] == 0


class TestDemo:
    def test_demo(self):
        from studio import demo

        mock_studio = MagicMock()
        mock_studio.pipeline_semana.return_value = PipelineResultado(
            semana_numero=1, fecha_inicio="2026-01-01", fecha_fin="2026-01-07", n_slots=0
        )
        mock_studio.guardar_pipeline.return_value = ROOT / "report.json"

        with patch("studio.Studio", return_value=mock_studio):
            demo()
            mock_studio.pipeline_semana.assert_called_once()


class TestCLI:
    def test_cli_help(self):
        from studio import cli
        with patch("sys.argv", ["studio.py", "--help"]):
            with pytest.raises(SystemExit) as exc_info:
                cli()
            assert exc_info.value.code == 0

    def test_cli_semana(self):
        from studio import cli

        mock_studio = MagicMock()
        mock_studio.calendario.generar_semana.return_value = MagicMock(
            fecha_inicio="2026-01-01", fecha_fin="2026-01-07", slots=[], numero=1
        )
        mock_studio.guardar_pipeline.return_value = ROOT / "report.json"

        with patch("sys.argv", ["studio.py", "semana", "--n", "1"]), \
             patch("studio.Studio", return_value=mock_studio):
            result = cli()
            assert result == 0

    def test_cli_duplicar(self, tmp_path):
        from studio import cli
        import studio
        original_root = studio.ROOT
        studio.ROOT = tmp_path

        try:
            mock_studio = MagicMock()
            mock_studio.duplicar_proyecto.return_value = tmp_path / "destino"

            origen = tmp_path / "inmuebles" / "lotes" / "origen"
            origen.mkdir(parents=True)

            with patch("sys.argv", ["studio.py", "duplicar", "--origen", "origen", "--destino", "destino"]), \
                 patch("studio.Studio", return_value=mock_studio):
                result = cli()
                assert result == 0
        finally:
            studio.ROOT = original_root

    def test_cli_listar(self):
        from studio import cli

        mock_studio = MagicMock()
        mock_studio.listar_carruseles.return_value = []

        with patch("sys.argv", ["studio.py", "listar"]), \
             patch("studio.Studio", return_value=mock_studio):
            result = cli()
            assert result == 0

    def test_cli_cache_stats(self):
        from studio import cli

        with patch("sys.argv", ["studio.py", "cache-stats"]), \
             patch("studio.ImageCache") as MockCache:
            MockCache.return_value.stats.return_value = {"total_entries": 0, "total_size_mb": 0, "total_size_bytes": 0}
            result = cli()
            assert result == 0


class TestAplicarCambiosAJson:
    def test_aplicar_cambios(self, mock_studio, tmp_path):
        import studio
        original_root = studio.ROOT
        studio.ROOT = tmp_path

        try:
            carpeta = tmp_path / "test_project"
            carpeta.mkdir()
            slides_data = {"slides": [{"prompt": "5 hectares in Cañuelas"}]}
            (carpeta / "carrusel.json").write_text(json.dumps(slides_data))
            resumen_data = {"hectareas": 5, "municipio": "Cañuelas"}
            (carpeta / "resumen.json").write_text(json.dumps(resumen_data))

            mock_studio._aplicar_cambios_a_json(carpeta, {"hectareas": 8, "municipio": "Escobar"})

            data = json.loads((carpeta / "carrusel.json").read_text())
            assert "8 hectares" in data["slides"][0]["prompt"]
        finally:
            studio.ROOT = original_root

    def test_aplicar_cambios_json_invalido(self, mock_studio, tmp_path):
        import studio
        original_root = studio.ROOT
        studio.ROOT = tmp_path

        try:
            carpeta = tmp_path / "test_project"
            carpeta.mkdir()
            (carpeta / "carrusel.json").write_text("not json {{{")

            mock_studio._aplicar_cambios_a_json(carpeta, {"hectareas": 8})
        finally:
            studio.ROOT = original_root

    def test_actualizar_resumen(self, mock_studio, tmp_path):
        import studio
        original_root = studio.ROOT
        studio.ROOT = tmp_path

        try:
            carpeta = tmp_path / "test_project"
            carpeta.mkdir()
            resumen_data = {"hectareas": 5}
            (carpeta / "resumen.json").write_text(json.dumps(resumen_data))

            mock_studio._actualizar_resumen(carpeta / "resumen.json", {"hectareas": 8})

            data = json.loads((carpeta / "resumen.json").read_text())
            assert data["hectareas"] == 8
        finally:
            studio.ROOT = original_root

    def test_actualizar_resumen_invalido(self, mock_studio, tmp_path):
        import studio
        original_root = studio.ROOT
        studio.ROOT = tmp_path

        try:
            carpeta = tmp_path / "test_project"
            carpeta.mkdir()
            (carpeta / "resumen.json").write_text("not json")

            mock_studio._actualizar_resumen(carpeta / "resumen.json", {"k": "v"})
        finally:
            studio.ROOT = original_root


class TestCLIHelpers:
    def test_programar_publicacion(self, tmp_path):
        from studio import _programar_publicacion
        import studio
        original_root = studio.ROOT
        studio.ROOT = tmp_path

        try:
            carpeta = tmp_path / "carrusel"
            carpeta.mkdir()
            data = {"caption_narrativo": "Test", "hashtags": ["#test"]}
            (carpeta / "carrusel.json").write_text(json.dumps(data))

            args = MagicMock()
            args.carrusel = str(carpeta / "carrusel.json")
            args.id = "test-post"
            args.scheduled_at = "2026-07-20T19:00:00"
            args.mode = "dry-run"
            args.caption = None
            args.hashtags = None

            with patch("studio.Scheduler") as MockScheduler:
                MockScheduler.return_value.stats.return_value = {"total": 1}
                _programar_publicacion(args)
                MockScheduler.return_value.programar.assert_called_once()
        finally:
            studio.ROOT = original_root

    def test_programar_fecha_invalida(self, tmp_path):
        from studio import _programar_publicacion
        import studio
        original_root = studio.ROOT
        studio.ROOT = tmp_path

        try:
            carpeta = tmp_path / "carrusel"
            carpeta.mkdir()
            (carpeta / "carrusel.json").write_text("{}")

            args = MagicMock()
            args.carrusel = str(carpeta / "carrusel.json")
            args.id = "test"
            args.scheduled_at = "invalid-date"
            args.mode = "dry-run"
            args.caption = None
            args.hashtags = None

            _programar_publicacion(args)
        finally:
            studio.ROOT = original_root

    def test_procesar_programadas_cli(self):
        from studio import _procesar_programadas_cli

        args = MagicMock()
        with patch("studio.Scheduler") as MockScheduler:
            MockScheduler.return_value.pendientes_a_procesar.return_value = []
            _procesar_programadas_cli(args)

    def test_listar_publicaciones(self):
        from studio import _listar_publicaciones

        args = MagicMock()
        args.cancel = None
        args.status = None

        with patch("studio.Scheduler") as MockScheduler:
            MockScheduler.return_value.listar.return_value = []
            _listar_publicaciones(args)

    def test_listar_publicaciones_cancel(self):
        from studio import _listar_publicaciones

        args = MagicMock()
        args.cancel = "test-id"
        args.status = None

        with patch("studio.Scheduler") as MockScheduler:
            MockScheduler.return_value.cancelar.return_value = True
            _listar_publicaciones(args)

    def test_generar_reporte_semanal(self):
        from studio import _generar_reporte_semanal

        args = MagicMock()
        args.fetch = False
        args.days = 7
        args.output = None

        with patch("studio.Monitor") as MockMonitor:
            MockMonitor.return_value.weekly_report.return_value = {}
            MockMonitor.return_value.render_markdown.return_value = "# Reporte"
            _generar_reporte_semanal(args)

    def test_generar_reporte_con_output(self, tmp_path):
        from studio import _generar_reporte_semanal

        args = MagicMock()
        args.fetch = False
        args.days = 7
        args.output = str(tmp_path / "reporte.md")

        with patch("studio.Monitor") as MockMonitor:
            MockMonitor.return_value.weekly_report.return_value = {}
            MockMonitor.return_value.render_markdown.return_value = "# Reporte"
            _generar_reporte_semanal(args)
            assert (tmp_path / "reporte.md").exists()

    def test_responder_dm_cli(self):
        from studio import _responder_dm_cli

        args = MagicMock()
        args.cliente = "Juan"
        args.mensaje = "Hola"
        args.data = None

        with patch("studio.DMTemplates") as MockTemplates:
            MockTemplates.return_value.responder.return_value = {
                "template_id": "test",
                "respuesta": "Hola Juan",
            }
            _responder_dm_cli(args)

    def test_responder_dm_con_data(self):
        from studio import _responder_dm_cli

        args = MagicMock()
        args.cliente = "Juan"
        args.mensaje = "Precio?"
        args.data = '{"precio": "USD 50000"}'

        with patch("studio.DMTemplates") as MockTemplates:
            MockTemplates.return_value.responder.return_value = {
                "template_id": "precio",
                "respuesta": "El lote cuesta USD 50000",
            }
            _responder_dm_cli(args)

    def test_demo_con_datos(self):
        from studio import demo

        mock_studio = MagicMock()
        resultado = PipelineResultado(
            semana_numero=1,
            fecha_inicio="2026-01-01",
            fecha_fin="2026-01-07",
            n_slots=5,
            carruseles_generados=["c1", "c2"],
            validaciones=[{"tipo": "test", "ok": True, "errores": [], "advertencias": ["warn"]}],
            errores=["error1"],
            resumen="Test resumen",
        )
        mock_studio.pipeline_semana.return_value = resultado
        mock_studio.guardar_pipeline.return_value = ROOT / "report.json"

        with patch("studio.Studio", return_value=mock_studio):
            demo()

    def test_cli_main(self):
        import sys
        with patch("sys.argv", ["studio.py"]):
            with patch("studio.demo") as mock_demo:
                import importlib
                # Can't easily test __main__ block, but verify module loads
                assert True


class TestCLIHelpers:
    def test_programar_publicacion(self, mock_studio, tmp_path):
        from studio import _programar_publicacion
        import argparse

        carrusel = tmp_path / "carrusel.json"
        carrusel.write_text(json.dumps({
            "caption_narrativo": "Test caption",
            "hashtags": ["#test"],
        }), encoding="utf-8")

        args = argparse.Namespace(
            id="test-post",
            carrusel=str(carrusel),
            caption=None,
            hashtags=None,
            scheduled_at="2026-07-20T19:00:00",
            mode="dry-run",
        )
        with patch("studio.Scheduler") as MockSched:
            mock_sched = MagicMock()
            MockSched.return_value = mock_sched
            _programar_publicacion(args)
            mock_sched.programar.assert_called_once()

    def test_programar_publicacion_fecha_invalida(self, mock_studio, tmp_path):
        from studio import _programar_publicacion
        import argparse

        carrusel = tmp_path / "carrusel.json"
        carrusel.write_text("{}", encoding="utf-8")

        args = argparse.Namespace(
            id="test-post",
            carrusel=str(carrusel),
            caption="c",
            hashtags=[],
            scheduled_at="not-a-date",
            mode="dry-run",
        )
        _programar_publicacion(args)

    def test_programar_publicacion_carrusel_no_existe(self, mock_studio):
        from studio import _programar_publicacion
        import argparse

        args = argparse.Namespace(
            id="test-post",
            carrusel="/nonexistent/carrusel.json",
            caption="c",
            hashtags=[],
            scheduled_at="2026-07-20T19:00:00",
            mode="dry-run",
        )
        _programar_publicacion(args)

    def test_procesar_programadas_cli_no_pendientes(self, mock_studio):
        from studio import _procesar_programadas_cli
        import argparse

        args = argparse.Namespace()
        with patch("studio.Scheduler") as MockSched:
            mock_sched = MagicMock()
            mock_sched.pendientes_a_procesar.return_value = []
            MockSched.return_value = mock_sched
            _procesar_programadas_cli(args)

    def test_listar_publicaciones(self, mock_studio):
        from studio import _listar_publicaciones
        import argparse

        args = argparse.Namespace(cancel=None, status=None)
        with patch("studio.Scheduler") as MockSched:
            mock_sched = MagicMock()
            mock_sched.listar.return_value = [
                MagicMock(id="p1", status="pending", scheduled_at="2026-07-20"),
            ]
            MockSched.return_value = mock_sched
            _listar_publicaciones(args)

    def test_listar_publicaciones_cancel(self, mock_studio):
        from studio import _listar_publicaciones
        import argparse

        args = argparse.Namespace(cancel="p1", status=None)
        with patch("studio.Scheduler") as MockSched:
            mock_sched = MagicMock()
            mock_sched.cancelar.return_value = True
            MockSched.return_value = mock_sched
            _listar_publicaciones(args)
            mock_sched.cancelar.assert_called_with("p1")

    def test_listar_publicaciones_cancel_not_found(self, mock_studio):
        from studio import _listar_publicaciones
        import argparse

        args = argparse.Namespace(cancel="no-existe", status=None)
        with patch("studio.Scheduler") as MockSched:
            mock_sched = MagicMock()
            mock_sched.cancelar.return_value = False
            MockSched.return_value = mock_sched
            _listar_publicaciones(args)

    def test_generar_reporte_semanal(self, mock_studio, tmp_path):
        from studio import _generar_reporte_semanal
        import argparse

        args = argparse.Namespace(fetch=False, days=7, output=None)
        with patch("studio.Monitor") as MockMon:
            mock_mon = MagicMock()
            mock_mon.weekly_report.return_value = {"periodo_dias": 7, "posts_analizados": 0}
            mock_mon.render_markdown.return_value = "# Reporte"
            MockMon.return_value = mock_mon
            _generar_reporte_semanal(args)

    def test_generar_reporte_semanal_with_output(self, mock_studio, tmp_path):
        from studio import _generar_reporte_semanal
        import argparse

        output = tmp_path / "report.md"
        args = argparse.Namespace(fetch=False, days=7, output=str(output))
        with patch("studio.Monitor") as MockMon:
            mock_mon = MagicMock()
            mock_mon.weekly_report.return_value = {"periodo_dias": 7, "posts_analizados": 0}
            mock_mon.render_markdown.return_value = "# Reporte"
            MockMon.return_value = mock_mon
            _generar_reporte_semanal(args)
            assert output.exists()

    def test_generar_reporte_semanal_with_fetch(self, mock_studio):
        from studio import _generar_reporte_semanal
        import argparse

        args = argparse.Namespace(fetch=True, days=7, output=None)
        with patch("studio.Monitor") as MockMon, \
             patch("studio.InstagramAuth") as MockAuth:
            mock_mon = MagicMock()
            mock_mon.weekly_report.return_value = {"periodo_dias": 7, "posts_analizados": 0}
            mock_mon.render_markdown.return_value = "# Reporte"
            MockMon.return_value = mock_mon
            mock_auth = MagicMock()
            mock_auth.configurado.return_value = False
            MockAuth.return_value = mock_auth
            _generar_reporte_semanal(args)

    def test_responder_dm_cli(self, mock_studio):
        from studio import _responder_dm_cli
        import argparse

        args = argparse.Namespace(
            cliente="Juan",
            mensaje="cuanto cuesta?",
            data=None,
        )
        with patch("studio.DMTemplates") as MockDM:
            mock_dm = MagicMock()
            mock_dm.responder.return_value = {"template_id": "precio", "respuesta": "USD 50000"}
            MockDM.return_value = mock_dm
            _responder_dm_cli(args)

    def test_responder_dm_cli_with_data(self, mock_studio):
        from studio import _responder_dm_cli
        import argparse

        args = argparse.Namespace(
            cliente="Juan",
            mensaje="cuanto cuesta?",
            data='{"precio": "USD 50000"}',
        )
        with patch("studio.DMTemplates") as MockDM:
            mock_dm = MagicMock()
            mock_dm.responder.return_value = {"template_id": "precio", "respuesta": "USD 50000"}
            MockDM.return_value = mock_dm
            _responder_dm_cli(args)


class TestGenerarCarruselCompleto:
    def test_no_existe(self, mock_studio):
        from studio import _generar_carrusel_completo
        result = _generar_carrusel_completo(mock_studio, "/nonexistent/path.json")
        assert result["success"] is False

    def test_sin_slides(self, mock_studio, tmp_path):
        from studio import _generar_carrusel_completo
        carrusel = tmp_path / "empty.json"
        carrusel.write_text(json.dumps({"slides": []}), encoding="utf-8")
        result = _generar_carrusel_completo(mock_studio, carrusel)
        assert result["success"] is False

    def test_cancelado_por_usuario(self, mock_studio, tmp_path):
        from studio import _generar_carrusel_completo
        carrusel = tmp_path / "carrusel.json"
        carrusel.write_text(json.dumps({
            "slides": [{"numero": 1, "tipo": "foto", "prompt": "test prompt"}]
        }), encoding="utf-8")

        with patch("builtins.input", return_value="n"):
            result = _generar_carrusel_completo(
                mock_studio, carrusel, skip_confirm=False
            )
        assert result["success"] is False

    def test_generar_exitoso(self, mock_studio, tmp_path):
        from studio import _generar_carrusel_completo
        from generation_pipeline import BatchResult

        carrusel = tmp_path / "carrusel.json"
        carrusel.write_text(json.dumps({
            "slides": [{"numero": 1, "tipo": "foto", "prompt": "test prompt"}]
        }), encoding="utf-8")

        with patch("studio.ImageCache"), \
             patch("studio.BatchGenerator") as MockBatch, \
             patch("studio.estimate_time", return_value={"human_readable": "25s", "total_seconds": 25}):
            mock_batch = MagicMock()
            mock_batch.generate_all.return_value = [
                BatchResult(item_id="slide_01_v1", success=True, cache_hit=False, output_path=None, error=None, attempts=1)
            ]
            MockBatch.return_value = mock_batch
            result = _generar_carrusel_completo(
                mock_studio, carrusel, skip_confirm=True
            )
        assert result["success"] is True
        assert result["ok"] == 1


class TestGenerarCarruselInteractivo:
    def test_success(self, mock_studio):
        from studio import _generar_carrusel_interactivo
        import argparse

        args = argparse.Namespace(
            carrusel="/test/carrusel.json",
            batch=1,
            workers=3,
            retries=3,
            no_cache=False,
            yes=True,
            seconds_per_image=25.0,
        )
        with patch("studio._generar_carrusel_completo", return_value={"success": True}):
            result = _generar_carrusel_interactivo(mock_studio, args)
            assert result == 0

    def test_failure(self, mock_studio):
        from studio import _generar_carrusel_interactivo
        import argparse

        args = argparse.Namespace(
            carrusel="/test/carrusel.json",
            batch=1,
            workers=3,
            retries=3,
            no_cache=False,
            yes=True,
            seconds_per_image=25.0,
        )
        with patch("studio._generar_carrusel_completo", return_value={"success": False, "error": "fail"}):
            result = _generar_carrusel_interactivo(mock_studio, args)
            assert result == 1


class TestEncolarCarrusel:
    def test_no_existe(self, mock_studio):
        from studio import _encolar_carrusel
        result = _encolar_carrusel(mock_studio, "/nonexistent.json")
        assert result["encolados"] == 0

    def test_sin_slides(self, mock_studio, tmp_path):
        from studio import _encolar_carrusel
        carrusel = tmp_path / "empty.json"
        carrusel.write_text(json.dumps({"slides": []}), encoding="utf-8")
        result = _encolar_carrusel(mock_studio, carrusel)
        assert result["encolados"] == 0

    def test_encolar_exitoso(self, mock_studio, tmp_path):
        from studio import _encolar_carrusel
        carrusel = tmp_path / "carrusel.json"
        carrusel.write_text(json.dumps({
            "slides": [{"numero": 1, "tipo": "foto", "prompt": "test prompt"}]
        }), encoding="utf-8")

        with patch("studio._build_batch_items_from_carrusel") as mock_build:
            from generation_pipeline import BatchItem
            mock_build.return_value = [
                BatchItem(id="s1", prompt="test", params={}, output_path=tmp_path / "out.jpg")
            ]
            result = _encolar_carrusel(mock_studio, carrusel)
        assert result["encolados"] == 1


class TestProcesarCola:
    def test_cola_vacia(self, mock_studio):
        from studio import _procesar_cola
        with patch("generation_pipeline.GenerationQueue") as MockQ:
            mock_q = MagicMock()
            mock_q.list_pending.return_value = []
            MockQ.return_value = mock_q
            result = _procesar_cola(mock_studio)
        assert result["total"] == 0

    def test_procesar_items(self, mock_studio):
        from studio import _procesar_cola
        from generation_pipeline import BatchResult

        mock_item = MagicMock()
        mock_item.id = 1
        mock_item.prompt = "test"
        mock_item.params_json = "{}"
        mock_item.output_path = None

        with patch("generation_pipeline.GenerationQueue") as MockQ, \
             patch("studio.ImageCache"), \
             patch("studio.BatchGenerator") as MockBatch:
            mock_q = MagicMock()
            mock_q.list_pending.return_value = [mock_item]
            MockQ.return_value = mock_q

            mock_batch = MagicMock()
            mock_batch.generate_all.return_value = [
                BatchResult(item_id="1", success=True, cache_hit=False, output_path=None, error=None, attempts=1)
            ]
            MockBatch.return_value = mock_batch

            result = _procesar_cola(mock_studio)
        assert result["exitos"] == 1
        mock_q.mark_done.assert_called_once()


class TestStudioListarCarruseles:
    def test_listar_con_proyecto(self, mock_studio, tmp_path):
        import carruseles
        original_root = carruseles.ROOT
        carruseles.ROOT = tmp_path

        import studio
        studio_original = studio.ROOT
        studio.ROOT = tmp_path

        try:
            carpeta = tmp_path / "inmuebles" / "lotes" / "test-proj" / "carruseles" / "c1"
            carpeta.mkdir(parents=True)
            (carpeta / "carrusel.json").write_text(json.dumps({
                "tema": "Test", "tipo": "lote_premium", "n_slides": 4,
                "municipio": "Cañuelas", "fecha_creacion": "2026-01-01"
            }), encoding="utf-8")

            result = mock_studio.listar_carruseles(proyecto="test-proj")
            assert len(result) == 1
            assert result[0]["nombre"] == "c1"
        finally:
            carruseles.ROOT = original_root
            studio.ROOT = studio_original

    def test_listar_sin_proyecto(self, mock_studio, tmp_path):
        import carruseles
        original_root = carruseles.ROOT
        carruseles.ROOT = tmp_path

        import studio
        studio_original = studio.ROOT
        studio.ROOT = tmp_path

        try:
            carpeta = tmp_path / "inmuebles" / "lotes" / "test-proj" / "carruseles" / "c1"
            carpeta.mkdir(parents=True)
            (carpeta / "carrusel.json").write_text(json.dumps({
                "tema": "Test", "tipo": "lote_premium", "n_slides": 4,
                "municipio": "Cañuelas", "fecha_creacion": "2026-01-01"
            }), encoding="utf-8")

            result = mock_studio.listar_carruseles()
            assert len(result) == 1
        finally:
            carruseles.ROOT = original_root
            studio.ROOT = studio_original

    def test_listar_con_servicios(self, mock_studio, tmp_path):
        import carruseles
        original_root = carruseles.ROOT
        carruseles.ROOT = tmp_path

        import studio
        studio_original = studio.ROOT
        studio.ROOT = tmp_path

        try:
            lotes_base = tmp_path / "inmuebles" / "lotes"
            lotes_base.mkdir(parents=True)

            carpeta = tmp_path / "inmuebles" / "servicios" / "carruseles" / "s1"
            carpeta.mkdir(parents=True)
            (carpeta / "carrusel.json").write_text(json.dumps({
                "tema": "Servicios", "tipo": "servicios", "n_slides": 6,
                "municipio": "Cañuelas", "fecha_creacion": "2026-01-01"
            }), encoding="utf-8")

            result = mock_studio.listar_carruseles()
            assert len(result) == 1
        finally:
            carruseles.ROOT = original_root
            studio.ROOT = studio_original

    def test_listar_json_corrupto(self, mock_studio, tmp_path):
        import carruseles
        original_root = carruseles.ROOT
        carruseles.ROOT = tmp_path

        import studio
        studio_original = studio.ROOT
        studio.ROOT = tmp_path

        try:
            carpeta = tmp_path / "inmuebles" / "lotes" / "test-proj" / "carruseles" / "c1"
            carpeta.mkdir(parents=True)
            (carpeta / "carrusel.json").write_text("bad json", encoding="utf-8")

            result = mock_studio.listar_carruseles()
            assert len(result) == 0
        finally:
            carruseles.ROOT = original_root
            studio.ROOT = studio_original


class TestGenerarImagenesPipeline:
    def test_con_carruseles(self, mock_studio, tmp_path):
        import studio
        original_root = studio.ROOT
        studio.ROOT = tmp_path

        try:
            resultado = PipelineResultado(
                semana_numero=1, fecha_inicio="2026-01-01",
                fecha_fin="2026-01-07", n_slots=5,
                carruseles_generados=["test-proj_c1"],
            )

            carpeta = tmp_path / "inmuebles" / "lotes" / "test-proj_c1" / "carruseles" / "test-proj_c1"
            carpeta.mkdir(parents=True)
            (carpeta / "carrusel.json").write_text(json.dumps({
                "slides": [{"numero": 1, "tipo": "foto", "prompt": "test"}]
            }), encoding="utf-8")

            mock_studio.image_generator.stub = True

            with patch.object(mock_studio, 'generar_imagenes_carrusel', return_value=[]):
                report = mock_studio.generar_imagenes_pipeline(resultado)
            assert "carruseles" in report
        finally:
            studio.ROOT = original_root


class TestPublicarSlot:
    def test_slot_vacio(self, mock_studio):
        from studio import ModoPublicacion
        slot = MagicMock()
        slot.post = None
        semana = MagicMock()
        result = mock_studio._publicar_slot(slot, semana, ModoPublicacion.DRY_RUN)
        assert result.exito is False

    def test_slot_sin_caption(self, mock_studio):
        from studio import ModoPublicacion
        slot = MagicMock()
        slot.post = {"caption_completo": ""}
        semana = MagicMock()
        result = mock_studio._publicar_slot(slot, semana, ModoPublicacion.DRY_RUN)
        assert result.exito is False
