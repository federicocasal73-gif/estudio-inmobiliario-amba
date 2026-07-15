"""Tests del modulo historial_publicaciones.py.

Cubre:
  - Publicacion dataclass: to_dict
  - HistorialPublicaciones: registrar, cargar, guardar, publicaciones_de_proyecto,
    ultima_publicacion_proyecto, dias_desde_ultima, limpiar, todas
  - RotadorProyectos: ordenar_por_antiguedad, proyectos_disponibles_esta_semana,
    sugerir_proyecto_para_slot, resumen_rotacion
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

import pytest

from historial_publicaciones import (
    HistorialPublicaciones,
    Publicacion,
    RotadorProyectos,
)


# ===== Publicacion =====


class TestPublicacion:
    def test_defaults(self):
        p = Publicacion(
            fecha="2025-01-01T10:00:00",
            tipo="lote_venta",
            municipio="Cañuelas",
            proyecto="proj",
        )
        assert p.instagram_post_id is None
        assert p.permalink is None
        assert p.metadata == {}

    def test_to_dict(self):
        p = Publicacion(
            fecha="2025-01-01T10:00:00",
            tipo="lote_venta",
            municipio="Cañuelas",
            proyecto="proj",
        )
        d = p.to_dict()
        assert d["tipo"] == "lote_venta"
        assert isinstance(d, dict)


# ===== HistorialPublicaciones =====


class TestHistorialPublicaciones:
    def test_empty_initially(self, tmp_path):
        h = HistorialPublicaciones(tmp_path / "hist.json")
        assert h.todas() == []

    def test_registrar(self, tmp_path):
        h = HistorialPublicaciones(tmp_path / "hist.json")
        pub = h.registrar(tipo="lote_venta", municipio="Cañuelas", proyecto="p")
        assert pub.tipo == "lote_venta"
        assert len(h.todas()) == 1

    def test_persistencia(self, tmp_path):
        ruta = tmp_path / "hist.json"
        h = HistorialPublicaciones(ruta)
        h.registrar(tipo="lote_venta", municipio="C", proyecto="p")

        h2 = HistorialPublicaciones(ruta)
        assert len(h2.todas()) == 1

    def test_json_malformado(self, tmp_path):
        ruta = tmp_path / "hist.json"
        ruta.write_text("not json {{{")
        h = HistorialPublicaciones(ruta)
        assert h.todas() == []

    def test_json_vacio(self, tmp_path):
        ruta = tmp_path / "hist.json"
        ruta.write_text("{}")
        h = HistorialPublicaciones(ruta)
        assert h.todas() == []

    def test_publicaciones_de_proyecto(self, tmp_path):
        h = HistorialPublicaciones(tmp_path / "hist.json")
        h.registrar(tipo="lote_venta", municipio="C", proyecto="p1")
        h.registrar(tipo="lote_venta", municipio="C", proyecto="p2")
        h.registrar(tipo="country", municipio="P", proyecto="p1")

        pubs = h.publicaciones_de_proyecto("p1", limite_dias=30)
        assert len(pubs) == 2

    def test_publicaciones_de_proyecto_fuera_de_rango(self, tmp_path):
        h = HistorialPublicaciones(tmp_path / "hist.json")
        # Publicar y modificar fecha a hace 60 días
        pub = h.registrar(tipo="lote_venta", municipio="C", proyecto="p")
        pub.fecha = (datetime.now() - timedelta(days=60)).isoformat()
        h._guardar()

        pubs = h.publicaciones_de_proyecto("p", limite_dias=30)
        assert len(pubs) == 0

    def test_ultima_publicacion_proyecto(self, tmp_path):
        h = HistorialPublicaciones(tmp_path / "hist.json")
        h.registrar(tipo="lote_venta", municipio="C", proyecto="p")
        h.registrar(tipo="country", municipio="P", proyecto="p")

        ultima = h.ultima_publicacion_proyecto("p")
        assert ultima is not None

    def test_ultima_publicacion_proyecto_no_existe(self, tmp_path):
        h = HistorialPublicaciones(tmp_path / "hist.json")
        assert h.ultima_publicacion_proyecto("inexistente") is None

    def test_dias_desde_ultima(self, tmp_path):
        h = HistorialPublicaciones(tmp_path / "hist.json")
        h.registrar(tipo="lote_venta", municipio="C", proyecto="p")

        dias = h.dias_desde_ultima("p")
        assert dias is not None
        assert dias == 0

    def test_dias_desde_ultima_no_existe(self, tmp_path):
        h = HistorialPublicaciones(tmp_path / "hist.json")
        assert h.dias_desde_ultima("inexistente") is None

    def test_dias_desde_ultima_fecha_invalida(self, tmp_path):
        h = HistorialPublicaciones(tmp_path / "hist.json")
        pub = h.registrar(tipo="lote_venta", municipio="C", proyecto="p")
        pub.fecha = "fecha_invalida"
        h._guardar()

        dias = h.dias_desde_ultima("p")
        assert dias is None

    def test_limpiar(self, tmp_path):
        h = HistorialPublicaciones(tmp_path / "hist.json")
        h.registrar(tipo="lote_venta", municipio="C", proyecto="p")
        assert len(h.todas()) == 1
        h.limpiar()
        assert len(h.todas()) == 0

    def test_todas(self, tmp_path):
        h = HistorialPublicaciones(tmp_path / "hist.json")
        h.registrar(tipo="a", municipio="C", proyecto="p")
        h.registrar(tipo="b", municipio="P", proyecto="q")
        assert len(h.todas()) == 2

    def test_registrar_con_metadata(self, tmp_path):
        h = HistorialPublicaciones(tmp_path / "hist.json")
        pub = h.registrar(
            tipo="lote_venta",
            municipio="C",
            proyecto="p",
            instagram_post_id="ig123",
            permalink="https://instagram.com/p/abc",
            metadata={"extra": "data"},
        )
        assert pub.instagram_post_id == "ig123"
        assert pub.permalink == "https://instagram.com/p/abc"
        assert pub.metadata["extra"] == "data"


# ===== RotadorProyectos =====


class TestRotadorProyectos:
    def _make_historial(self, tmp_path):
        h = HistorialPublicaciones(tmp_path / "hist.json")
        return h

    def test_ordenar_por_antiguedad_vacio(self, tmp_path):
        h = self._make_historial(tmp_path)
        r = RotadorProyectos(h)
        assert r.ordenar_por_antiguedad([]) == []

    def test_ordenar_por_antiguedad_nunca_publicado(self, tmp_path):
        h = self._make_historial(tmp_path)
        r = RotadorProyectos(h)
        orden = r.ordenar_por_antiguedad(["p1", "p2", "p3"])
        assert orden == ["p1", "p2", "p3"]

    def test_ordenar_por_antiguedad_con_historial(self, tmp_path):
        h = self._make_historial(tmp_path)
        h.registrar(tipo="lote_venta", municipio="C", proyecto="p2")
        h.registrar(tipo="lote_venta", municipio="C", proyecto="p1")
        r = RotadorProyectos(h)
        orden = r.ordenar_por_antiguedad(["p1", "p2", "p3"])
        assert orden[0] == "p3"
        assert orden[-1] == "p2"

    def test_proyectos_disponibles_esta_semana(self, tmp_path):
        h = self._make_historial(tmp_path)
        h.registrar(tipo="lote_venta", municipio="C", proyecto="p1")
        r = RotadorProyectos(h)
        disponibles = r.proyectos_disponibles_esta_semana(
            ["p1", "p2"], dias_minimos_entre_posts=3
        )
        assert "p1" not in disponibles
        assert "p2" in disponibles

    def test_proyectos_disponibles_nunca_publicado(self, tmp_path):
        h = self._make_historial(tmp_path)
        r = RotadorProyectos(h)
        disponibles = r.proyectos_disponibles_esta_semana(["p1"], dias_minimos_entre_posts=3)
        assert "p1" in disponibles

    def test_sugerir_proyecto_para_slot_vacio(self, tmp_path):
        h = self._make_historial(tmp_path)
        r = RotadorProyectos(h)
        assert r.sugerir_proyecto_para_slot([]) is None

    def test_sugerir_proyecto_country(self, tmp_path):
        h = self._make_historial(tmp_path)
        r = RotadorProyectos(h)
        sugerido = r.sugerir_proyecto_para_slot(
            ["lote-abc", "country-xyz"], tipo_post="country"
        )
        assert sugerido == "country-xyz"

    def test_sugerir_proyecto_country_sin_match(self, tmp_path):
        h = self._make_historial(tmp_path)
        r = RotadorProyectos(h)
        sugerido = r.sugerir_proyecto_para_slot(
            ["lote-abc", "campo-xyz"], tipo_post="country"
        )
        assert sugerido in ["lote-abc", "campo-xyz"]

    def test_sugerir_proyecto_campo(self, tmp_path):
        h = self._make_historial(tmp_path)
        r = RotadorProyectos(h)
        sugerido = r.sugerir_proyecto_para_slot(
            ["lote-abc", "campo-xyz"], tipo_post="campo"
        )
        assert sugerido == "campo-xyz"

    def test_resumen_rotacion(self, tmp_path):
        h = self._make_historial(tmp_path)
        h.registrar(tipo="lote_venta", municipio="C", proyecto="p1")
        r = RotadorProyectos(h)
        resumen = r.resumen_rotacion(["p1", "p2"])
        assert "p1" in resumen
        assert "p2" in resumen
        assert resumen["p1"]["dias_desde_ultima"] == 0
        assert resumen["p1"]["publicaciones_ultimo_mes"] == 1
        assert resumen["p2"]["dias_desde_ultima"] is None
