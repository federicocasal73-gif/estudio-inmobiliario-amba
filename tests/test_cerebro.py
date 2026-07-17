"""Tests para el módulo cerebro - Prompt Database."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from cerebro.prompt_database import PromptDatabase, PromptEntry, CATEGORIAS, ESTILOS


class TestPromptEntry:
    def test_creation(self):
        entry = PromptEntry(prompt="test prompt")
        assert entry.prompt == "test prompt"
        assert entry.id
        assert entry.aprobado is False
        assert entry.rating == 0

    def test_to_dict(self):
        entry = PromptEntry(prompt="test")
        d = entry.to_dict()
        assert isinstance(d, dict)
        assert d["prompt"] == "test"
        assert "id" in d

    def test_from_dict(self):
        d = {
            "id": "abc123",
            "prompt": "test prompt",
            "negative_prompt": "bad",
            "aspect_ratio": "896*1152",
            "aprobado": True,
            "rating": 4,
        }
        entry = PromptEntry.from_dict(d)
        assert entry.id == "abc123"
        assert entry.aprobado is True
        assert entry.rating == 4

    def test_properties(self):
        entry = PromptEntry(
            prompt="test",
            metadata={"categoria": "terreno", "estilo": "campestre"},
        )
        assert entry.categoria == "terreno"
        assert entry.estilo == "campestre"


class TestPromptDatabase:
    def test_empty_initially(self, tmp_path):
        db = PromptDatabase(tmp_path / "test.json")
        assert len(db.listar()) == 0

    def test_agregar(self, tmp_path):
        db = PromptDatabase(tmp_path / "test.json")
        entry = db.agregar(prompt="test prompt", metadata={"categoria": "terreno"})
        assert entry.prompt == "test prompt"
        assert len(db.listar()) == 1

    def test_agregar_con_tags(self, tmp_path):
        db = PromptDatabase(tmp_path / "test.json")
        entry = db.agregar(prompt="test", tags=["pampas", "rural"])
        assert "pampas" in entry.tags

    def test_obtener(self, tmp_path):
        db = PromptDatabase(tmp_path / "test.json")
        entry = db.agregar(prompt="test")
        found = db.obtener(entry.id)
        assert found is not None
        assert found.prompt == "test"

    def test_obtener_inexistente(self, tmp_path):
        db = PromptDatabase(tmp_path / "test.json")
        assert db.obtener("no-existe") is None

    def test_actualizar(self, tmp_path):
        db = PromptDatabase(tmp_path / "test.json")
        entry = db.agregar(prompt="original")
        updated = db.actualizar(entry.id, prompt="modificado", rating=5)
        assert updated.prompt == "modificado"
        assert updated.rating == 5

    def test_actualizar_inexistente(self, tmp_path):
        db = PromptDatabase(tmp_path / "test.json")
        assert db.actualizar("no-existe", prompt="x") is None

    def test_eliminar(self, tmp_path):
        db = PromptDatabase(tmp_path / "test.json")
        entry = db.agregar(prompt="test")
        assert db.eliminar(entry.id) is True
        assert db.obtener(entry.id) is None

    def test_eliminar_inexistente(self, tmp_path):
        db = PromptDatabase(tmp_path / "test.json")
        assert db.eliminar("no-existe") is False

    def test_persistencia(self, tmp_path):
        path = tmp_path / "test.json"
        db1 = PromptDatabase(path)
        db1.agregar(prompt="persist me")

        db2 = PromptDatabase(path)
        assert len(db2.listar()) == 1
        assert db2.listar()[0].prompt == "persist me"

    def test_buscar_por_categoria(self, tmp_path):
        db = PromptDatabase(tmp_path / "test.json")
        db.agregar(prompt="terreno 1", metadata={"categoria": "terreno"})
        db.agregar(prompt="casa 1", metadata={"categoria": "casa_terminada"})

        results = db.buscar(categoria="terreno")
        assert len(results) == 1
        assert "terreno" in results[0].prompt

    def test_buscar_por_estilo(self, tmp_path):
        db = PromptDatabase(tmp_path / "test.json")
        db.agregar(prompt="campestre", metadata={"estilo": "campestre"})
        db.agregar(prompt="moderno", metadata={"estilo": "moderno"})

        results = db.buscar(estilo="campestre")
        assert len(results) == 1

    def test_buscar_por_aprobado(self, tmp_path):
        db = PromptDatabase(tmp_path / "test.json")
        e1 = db.agregar(prompt="approved")
        db.agregar(prompt="pending")
        db.actualizar(e1.id, aprobado=True, rating=4)

        results = db.buscar(aprobado=True)
        assert len(results) == 1
        assert results[0].prompt == "approved"

    def test_buscar_por_rating(self, tmp_path):
        db = PromptDatabase(tmp_path / "test.json")
        e1 = db.agregar(prompt="high rating")
        e2 = db.agregar(prompt="low rating")
        db.actualizar(e1.id, aprobado=True, rating=5)
        db.actualizar(e2.id, aprobado=True, rating=2)

        results = db.buscar(min_rating=4)
        assert len(results) == 1
        assert results[0].prompt == "high rating"

    def test_buscar_por_texto(self, tmp_path):
        db = PromptDatabase(tmp_path / "test.json")
        db.agregar(prompt="pampas landscape")
        db.agregar(prompt="city view")

        results = db.buscar(texto="pampas")
        assert len(results) == 1

    def test_buscar_por_tags(self, tmp_path):
        db = PromptDatabase(tmp_path / "test.json")
        db.agregar(prompt="rural", tags=["rural", "campo"])
        db.agregar(prompt="urban", tags=["city", "urban"])

        results = db.buscar(tags=["rural"])
        assert len(results) == 1

    def test_estadisticas(self, tmp_path):
        db = PromptDatabase(tmp_path / "test.json")
        db.agregar(prompt="p1", metadata={"categoria": "terreno"})
        db.agregar(prompt="p2", metadata={"categoria": "terreno"})
        db.agregar(prompt="p3", metadata={"categoria": "casa_terminada"})

        stats = db.estadisticas()
        assert stats["total"] == 3
        assert stats["por_categoria"]["terreno"] == 2

    def test_exportar_aprobados(self, tmp_path):
        db = PromptDatabase(tmp_path / "test.json")
        e1 = db.agregar(prompt="good")
        e2 = db.agregar(prompt="bad")
        db.actualizar(e1.id, aprobado=True, rating=4)

        exported = db.exportar_aprobados(min_rating=3)
        assert len(exported) == 1
        assert exported[0]["prompt"] == "good"

    def test_importar_desde_json(self, tmp_path):
        db = PromptDatabase(tmp_path / "test.json")
        import_data = {
            "prompts": [
                {"prompt": "imported prompt", "metadata": {"categoria": "lote"}}
            ]
        }
        import_file = tmp_path / "import.json"
        import_file.write_text(json.dumps(import_data), encoding="utf-8")

        count = db.importar_desde_json(import_file)
        assert count == 1
        assert len(db.listar()) == 1

    def test_no_duplicar_al_importar(self, tmp_path):
        db = PromptDatabase(tmp_path / "test.json")
        db.agregar(prompt="existing")

        import_data = {"prompts": [{"prompt": "existing"}]}
        import_file = tmp_path / "import.json"
        import_file.write_text(json.dumps(import_data), encoding="utf-8")

        count = db.importar_desde_json(import_file)
        assert count == 0


class TestConstants:
    def test_categorias(self):
        assert "terreno" in CATEGORIAS
        assert "lote" in CATEGORIAS
        assert "construccion" in CATEGORIAS
        assert "casa_terminada" in CATEGORIAS

    def test_estilos(self):
        assert "campestre" in ESTILOS
        assert "moderno" in ESTILOS
        assert "premium" in ESTILOS
