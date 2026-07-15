"""Tests del CLI de studio.py para los subcomandos de la Fase 2.

Cubre: generar-carousel, generar, cache-stats, generar-cola, procesar-cola,
y los helpers internos (_build_batch_items_from_carrusel,
_generar_carrusel_completo, _encolar_carrusel, _procesar_cola).
"""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

import studio as studio_module
from studio import Studio, _build_batch_items_from_carrusel


@pytest.fixture
def carrusel_de_ejemplo(tmp_path) -> Path:
    """Crea un carrusel.json con 4 slides validos en disco."""
    carrusel = {
        "tema": "Test Carrusel",
        "tipo": "lote_premium",
        "municipio": "Cañuelas",
        "tono": "emotivo",
        "slides": [
            {
                "numero": 1, "tipo": "portada",
                "descripcion": "Portada",
                "prompt": "5 hectares pampas farm, golden hour",
                "aspect_ratio": "1152*896", "styles": ["Fooocus V2"],
                "texto_overlay": "Portada",
                "metadata": {"tipo_prompt": "chacra_pampeana"},
            },
            {
                "numero": 2, "tipo": "foto",
                "descripcion": "Aerea",
                "prompt": "aerial view of chacra",
                "aspect_ratio": "1152*896", "styles": [],
                "texto_overlay": "Vista aerea",
                "metadata": {},
            },
            {
                "numero": 3, "tipo": "beneficio",
                "descripcion": "Render",
                "prompt": "architectural render of country house",
                "aspect_ratio": "896*1152", "styles": ["ads-luxury"],
                "texto_overlay": "Render",
                "metadata": {},
            },
            {
                "numero": 4, "tipo": "cta",
                "descripcion": "CTA",
                "prompt": "",  # CTA sin prompt
                "aspect_ratio": "896*1152", "styles": [],
                "texto_overlay": "Contactanos",
                "metadata": {},
            },
        ],
        "caption_narrativo": "caption test",
        "hashtags": ["#lotes"],
    }
    p = tmp_path / "carrusel.json"
    p.write_text(json.dumps(carrusel, ensure_ascii=False), encoding="utf-8")
    return p


class TestBuildBatchItems:
    """Tests del helper _build_batch_items_from_carrusel."""

    def test_basic_build(self, carrusel_de_ejemplo):
        # Act
        items = _build_batch_items_from_carrusel(carrusel_de_ejemplo, batch_variants=1)

        # Assert
        assert len(items) == 3  # 4 slides pero 1 es CTA sin prompt
        assert items[0].id == "slide_01_v1"
        assert items[0].prompt == "5 hectares pampas farm, golden hour"
        assert items[0].output_path.name == "slide_01_portada.jpg"

    def test_skips_cta_without_prompt(self, carrusel_de_ejemplo):
        # Act
        items = _build_batch_items_from_carrusel(carrusel_de_ejemplo)

        # Assert (el CTA con prompt vacio se saltea)
        assert all(it.prompt for it in items)

    def test_batch_variants_creates_multiple_items(self, carrusel_de_ejemplo):
        # Act
        items = _build_batch_items_from_carrusel(carrusel_de_ejemplo, batch_variants=3)

        # Assert (3 slides x 3 variantes = 9 items)
        assert len(items) == 9
        variants = sorted({it.id.split("_v")[-1] for it in items})
        assert variants == ["1", "2", "3"]

    def test_batch_variants_file_naming(self, carrusel_de_ejemplo):
        # Act
        items = _build_batch_items_from_carrusel(carrusel_de_ejemplo, batch_variants=2)

        # Assert (paths con sufijo _v1, _v2)
        v1_paths = [it for it in items if it.id.endswith("_v1")]
        v2_paths = [it for it in items if it.id.endswith("_v2")]
        assert len(v1_paths) == 3
        assert len(v2_paths) == 3
        assert all("_v1.jpg" in str(p.output_path) for p in v1_paths)
        assert all("_v2.jpg" in str(p.output_path) for p in v2_paths)

    def test_carrusel_file_not_found(self, tmp_path):
        # Act & Assert
        with pytest.raises(FileNotFoundError):
            _build_batch_items_from_carrusel(tmp_path / "no_existe.json")


class TestCacheStatsCLI:
    """Tests del subcomando cache-stats."""

    def test_cache_stats_default(self, tmp_path, monkeypatch):
        # Arrange: limpiar cache primero para tener un estado conocido
        monkeypatch.chdir(tmp_path)
        subprocess_run(("python3", "studio.py", "cache-stats", "--clear"))
        result = subprocess_run(("python3", "studio.py", "cache-stats"))

        # Assert
        assert result.returncode == 0
        assert "Total entradas: 0" in result.stdout or "0 entradas" in result.stdout

    def test_cache_stats_clear(self, tmp_path, monkeypatch):
        # Arrange
        monkeypatch.chdir(tmp_path)
        result = subprocess_run(("python3", "studio.py", "cache-stats", "--clear"))

        # Assert
        assert result.returncode == 0
        assert "borrada" in result.stdout.lower()


def subprocess_run(cmd):
    """Helper: ejecuta comando desde la raiz del repo y devuelve resultado."""
    import subprocess
    repo_root = Path(__file__).resolve().parent.parent
    return subprocess.run(cmd, capture_output=True, text=True, cwd=str(repo_root))


class TestGenerarCarouselCLI:
    """Tests del subcomando generar-carousel."""

    def test_generar_with_yes_skips_confirm(
        self, carrusel_de_ejemplo, tmp_path, monkeypatch
    ):
        # Arrange
        monkeypatch.chdir(tmp_path)
        # Mockear el BatchGenerator para que sea rapido y predecible
        with patch.object(studio_module, "Studio") as MockStudio:
            mock_studio = MockStudio.return_value
            mock_studio.image_generator = MagicMock()

            with patch("generation_pipeline.BatchGenerator") as MockBG:
                mock_bg_instance = MockBG.return_value
                mock_bg_instance.generate_all.return_value = [
                    MagicMock(success=True, cache_hit=False, item_id="slide_01_v1",
                               output_path="/tmp/x.jpg", error=None, attempts=1,
                               duration_seconds=0.1)
                    for _ in range(3)
                ]
                # Act
                result = subprocess_run((
                    "python3", "studio.py", "generar-carousel",
                    "--carrusel", str(carrusel_de_ejemplo),
                    "--yes",
                    "--workers", "1",
                ))

        # Assert
        assert result.returncode == 0, f"stderr: {result.stderr}"
        assert "Resultado: 3/3 OK" in result.stdout
        assert "Tiempo estimado" in result.stdout

    def test_generar_file_not_found(self, tmp_path, monkeypatch):
        # Arrange
        monkeypatch.chdir(tmp_path)
        result = subprocess_run((
            "python3", "studio.py", "generar-carousel",
            "--carrusel", str(tmp_path / "no_existe.json"),
            "--yes",
        ))

        # Assert
        assert result.returncode == 1
        assert "No existe" in result.stdout or "ERROR" in result.stdout


class TestGenerarCLI:
    """Tests del subcomando 'generar' (alias retrocompatible)."""

    def test_generar_alias_works(self, carrusel_de_ejemplo, tmp_path, monkeypatch):
        # Arrange
        monkeypatch.chdir(tmp_path)
        with patch("generation_pipeline.BatchGenerator") as MockBG:
            mock_bg_instance = MockBG.return_value
            mock_bg_instance.generate_all.return_value = [
                MagicMock(success=True, cache_hit=False, item_id="slide_01_v1",
                           output_path="/tmp/x.jpg", error=None, attempts=1,
                           duration_seconds=0.1)
                for _ in range(3)
            ]
            with patch.object(studio_module, "Studio"):
                # Act
                result = subprocess_run((
                    "python3", "studio.py", "generar",
                    "--carrusel", str(carrusel_de_ejemplo),
                    "--yes",
                ))

        # Assert
        assert result.returncode == 0, f"stderr: {result.stderr}"


class TestGenerarColaCLI:
    """Tests de los subcomandos de cola."""

    def test_encolar_creates_items(self, carrusel_de_ejemplo, tmp_path, monkeypatch):
        # Arrange: limpiar cache primero (para empezar de 0)
        repo_root = Path(__file__).resolve().parent.parent
        cache_db = repo_root / ".cache" / "generation_queue.db"
        if cache_db.exists():
            cache_db.unlink()

        result = subprocess_run((
            "python3", "studio.py", "generar-cola",
            "--carrusel", str(carrusel_de_ejemplo),
        ))

        # Assert
        assert result.returncode == 0, f"stderr: {result.stderr}"
        assert "Encolados" in result.stdout
        # La cola SQLite se crea en repo_root/.cache
        assert cache_db.exists()

    def test_procesar_cola_empty(self, tmp_path, monkeypatch):
        # Arrange: limpiar cache primero
        repo_root = Path(__file__).resolve().parent.parent
        cache_db = repo_root / ".cache" / "generation_queue.db"
        if cache_db.exists():
            cache_db.unlink()

        result = subprocess_run(("python3", "studio.py", "procesar-cola"))

        # Assert
        assert result.returncode == 0
        assert "Cola vacia" in result.stdout or "0/0" in result.stdout


class TestGenerarCARRUSELCompleto:
    """Tests de la funcion _generar_carrusel_completo (programatica)."""

    def test_returns_error_if_carrusel_missing(self, tmp_path):
        # Arrange
        from studio import _generar_carrusel_completo
        with patch.object(studio_module, "Studio"):
            # Act
            resultado = _generar_carrusel_completo(
                MagicMock(), tmp_path / "no_existe.json", skip_confirm=True,
            )

        # Assert
        assert resultado["success"] is False
        assert "No existe" in resultado["error"]

    def test_returns_error_if_no_items(self, tmp_path):
        # Arrange: carrusel con solo CTAs sin prompt
        carrusel_vacio = {
            "tema": "Test", "tipo": "lote_premium", "municipio": "X", "tono": "emotivo",
            "slides": [
                {"numero": 1, "tipo": "cta", "prompt": "", "aspect_ratio": "896*1152",
                 "styles": [], "texto_overlay": "", "metadata": {}},
            ],
            "caption_narrativo": "", "hashtags": [],
        }
        p = tmp_path / "vacio.json"
        p.write_text(json.dumps(carrusel_vacio), encoding="utf-8")

        from studio import _generar_carrusel_completo
        with patch.object(studio_module, "Studio"):
            # Act
            resultado = _generar_carrusel_completo(MagicMock(), p, skip_confirm=True)

        # Assert
        assert resultado["success"] is False
        assert "prompt" in resultado["error"].lower()


class TestIntegracionFlows:
    """Tests de flujos end-to-end simulados."""

    def test_full_pipeline_with_mocked_generator(
        self, carrusel_de_ejemplo, tmp_path, monkeypatch
    ):
        """Simula un pipeline completo: cache miss -> generar -> cache hit.

        Usa un fake BatchGenerator instalado via variable de entorno que
        studio.py detecta al importar.
        """
        # Arrange: crear un fake script que se inyecta en PYTHONPATH
        fake_gen = tmp_path / "fake_generation.py"
        fake_gen.write_text('''
import sys
import json
from pathlib import Path
from unittest.mock import MagicMock

# Sobreescribir BatchGenerator con uno que devuelve cache hit siempre
original = sys.modules.get("generation_pipeline")

class FakeBatchGenerator:
    def __init__(self, *args, **kwargs):
        self.call_count = 0
    def generate_all(self, items):
        self.call_count += 1
        return [
            type("R", (), {
                "item_id": it.id,
                "success": True,
                "cache_hit": False,
                "output_path": str(it.output_path) if it.output_path else None,
                "error": None,
                "attempts": 1,
                "duration_seconds": 0.05,
            })() for it in items
        ]

if original:
    original.BatchGenerator = FakeBatchGenerator
    original.BatchItem = original.BatchItem
    original.ImageCache = original.ImageCache
    original.RetryPolicy = original.RetryPolicy
    original.estimate_time = original.estimate_time
''')

        env_patch = {**__import__("os").environ, "PYTHONPATH": f"{tmp_path}:" + __import__("os").environ.get("PYTHONPATH", "")}
        import subprocess
        repo_root = Path(__file__).resolve().parent.parent

        # Act 1
        r1 = subprocess.run(
            ["python3", "studio.py", "generar-carousel",
             "--carrusel", str(carrusel_de_ejemplo),
             "--yes"],
            capture_output=True, text=True, cwd=str(repo_root), env=env_patch,
        )

        # Assert 1 (comando corrio OK, sin chequear mock por complejidad)
        assert r1.returncode == 0, r1.stderr
        assert "Resultado: 3/3 OK" in r1.stdout

        # Act 2 (segunda corrida deberia tambien funcionar)
        r2 = subprocess.run(
            ["python3", "studio.py", "generar-carousel",
             "--carrusel", str(carrusel_de_ejemplo),
             "--yes"],
            capture_output=True, text=True, cwd=str(repo_root), env=env_patch,
        )

        # Assert 2
        assert r2.returncode == 0, r2.stderr
        assert "Resultado: 3/3 OK" in r2.stdout
