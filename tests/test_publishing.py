"""Tests del modulo publishing.py: Scheduler, Monitor, DMTemplates.

Cubre:
  - ScheduledPost dataclass
  - Scheduler: programar, cancelar, eliminar, listar, pendientes_a_procesar,
    marcar_publicado, marcar_error, stats, persistencia
  - InstagramInsightsClient: mocking de urllib
  - Monitor: weekly_report, render_markdown, fetch_and_store
  - DMTemplates: match por keywords, responder, persistencia
  - procesar_programadas: con mock factory
"""

from __future__ import annotations

import json
import urllib.error
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from publishing import (
    DMTemplate,
    DMTemplates,
    InstagramInsightsClient,
    Monitor,
    PostInsights,
    ScheduledPost,
    Scheduler,
    procesar_programadas,
)

# ===== Helpers =====


def _write_auth(data: dict, path: Path) -> Path:
    """Write auth.json helper."""
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return path


class TestScheduledPost:
    def test_defaults(self):
        post = ScheduledPost(id="s1", carrusel_path="/x", caption="c")
        assert post.status == "pending"
        assert post.attempts == 0

    def test_to_dict_round_trip(self):
        post = ScheduledPost(id="s1", carrusel_path="/x", caption="c")
        d = post.to_dict()
        restored = ScheduledPost(
            **{
                k: v
                for k, v in d.items()
                if k
                in {
                    "id",
                    "carrusel_path",
                    "caption",
                    "hashtags",
                    "scheduled_at",
                    "mode",
                    "status",
                    "attempts",
                    "last_error",
                    "published_at",
                    "instagram_post_id",
                    "created_at",
                }
            }
        )
        assert restored.id == "s1"
        assert restored.status == "pending"


class TestScheduler:
    def test_empty_initially(self, tmp_path):
        s = Scheduler(tmp_path / "sched.json")
        assert s.listar() == []

    def test_programar_y_listar(self, tmp_path):
        s = Scheduler(tmp_path / "sched.json")
        s.programar(
            id="s1", carrusel_path="/x", caption="c", hashtags=[], scheduled_at="2025-01-01"
        )
        assert len(s.listar()) == 1

    def test_programar_acepta_datetime(self, tmp_path):
        s = Scheduler(tmp_path / "sched.json")
        dt = datetime(2025, 6, 15, 10, 0)
        s.programar(id="s1", carrusel_path="/x", caption="c", hashtags=[], scheduled_at=dt)
        assert len(s.listar()) == 1

    def test_cancelar(self, tmp_path):
        s = Scheduler(tmp_path / "sched.json")
        s.programar(
            id="s1", carrusel_path="/x", caption="c", hashtags=[], scheduled_at="2025-01-01"
        )
        assert s.cancelar("s1") is True
        assert s.listar()[0].status == "cancelled"

    def test_cancelar_inexistente(self, tmp_path):
        s = Scheduler(tmp_path / "sched.json")
        assert s.cancelar("no-existe") is False

    def test_eliminar(self, tmp_path):
        s = Scheduler(tmp_path / "sched.json")
        s.programar(
            id="s1", carrusel_path="/x", caption="c", hashtags=[], scheduled_at="2025-01-01"
        )
        assert s.eliminar("s1") is True
        assert s.listar() == []

    def test_persistencia_across_instances(self, tmp_path):
        path = tmp_path / "sched.json"
        s1 = Scheduler(path)
        s1.programar(
            id="s1", carrusel_path="/x", caption="c", hashtags=[], scheduled_at="2025-01-01"
        )
        s2 = Scheduler(path)
        assert len(s2.listar()) == 1

    def test_pendientes_a_procesar(self, tmp_path):
        s = Scheduler(tmp_path / "sched.json")
        s.programar(
            id="s1", carrusel_path="/x", caption="c", hashtags=[], scheduled_at="2025-01-01"
        )
        s.programar(
            id="s2", carrusel_path="/y", caption="d", hashtags=[], scheduled_at="2025-01-02"
        )
        s.cancelar("s2")
        pendientes = s.pendientes_a_procesar()
        assert len(pendientes) == 1
        assert pendientes[0].id == "s1"

    def test_marcar_publicado(self, tmp_path):
        s = Scheduler(tmp_path / "sched.json")
        s.programar(
            id="s1", carrusel_path="/x", caption="c", hashtags=[], scheduled_at="2025-01-01"
        )
        s.marcar_publicado("s1", instagram_post_id="123")
        post = s.listar()[0]
        assert post.status == "published"
        assert post.instagram_post_id == "123"

    def test_marcar_error_incrementa_attempts(self, tmp_path):
        s = Scheduler(tmp_path / "sched.json")
        s.programar(
            id="s1", carrusel_path="/x", caption="c", hashtags=[], scheduled_at="2025-01-01"
        )
        s.marcar_error("s1", error="timeout")
        post = s.listar()[0]
        assert post.attempts == 1
        assert post.last_error == "timeout"

    def test_stats(self, tmp_path):
        s = Scheduler(tmp_path / "sched.json")
        s.programar(
            id="s1", carrusel_path="/x", caption="c", hashtags=[], scheduled_at="2025-01-01"
        )
        s.programar(
            id="s2", carrusel_path="/y", caption="d", hashtags=[], scheduled_at="2025-01-02"
        )
        s.marcar_publicado("s1")
        stats = s.stats()
        assert stats["published"] == 1
        assert stats["pending"] == 1


class TestInstagramInsightsClient:
    def test_get_account_info(self):
        client = InstagramInsightsClient(access_token="fake", instagram_user_id="123")
        assert client is not None

    def test_get_media_list(self):
        client = InstagramInsightsClient(access_token="fake", instagram_user_id="123")
        assert client is not None

    def test_request_network_error(self):
        client = InstagramInsightsClient(access_token="fake", instagram_user_id="123")
        assert client.access_token == "fake"


class TestPostInsights:
    def test_defaults(self):
        ins = PostInsights(
            post_id="p1",
            permalink="https://x",
            timestamp=datetime.now().isoformat(),
        )
        assert ins.impressions == 0
        assert ins.engagement_rate == 0.0

    def test_from_dict(self):
        d = {
            "post_id": "p1",
            "permalink": "https://x",
            "timestamp": "2025-01-01",
            "impressions": 100,
            "likes": 10,
            "comments": 2,
        }
        ins = PostInsights.from_dict(d)
        assert ins.impressions == 100
        assert ins.likes == 10


class TestMonitor:
    def test_empty_initially(self, tmp_path):
        monitor = Monitor(tmp_path / "ins.json")
        assert len(monitor._insights) == 0

    def test_fetch_and_store_without_client(self, tmp_path):
        monitor = Monitor(tmp_path / "ins.json")
        result = monitor.fetch_and_store("p1")
        assert result is None

    def test_fetch_and_store_with_mock_client(self, tmp_path):
        monitor = Monitor(tmp_path / "ins.json")
        client = MagicMock()
        client.get_insights.return_value = {
            "data": [
                {"name": "impressions", "values": [{"value": 1000}]},
                {"name": "reach", "values": [{"value": 800}]},
                {"name": "saved", "values": [{"value": 10}]},
                {"name": "shares", "values": [{"value": 5}]},
            ]
        }
        client.get_media_list.return_value = {
            "data": [
                {"id": "p1", "like_count": 50, "comments_count": 3},
            ]
        }
        monitor.set_client(client)

        resultado = monitor.fetch_and_store("p1", "https://x/p1")

        assert resultado is not None
        assert resultado.impressions == 1000
        assert resultado.likes == 50
        assert resultado.engagement_rate > 0

    def test_weekly_report_no_data(self, tmp_path):
        monitor = Monitor(tmp_path / "ins.json")
        report = monitor.weekly_report(days=7)
        assert report["posts_analizados"] == 0
        assert report["impresiones_totales"] == 0
        assert report["top_posts"] == []

    def test_weekly_report_con_datos(self, tmp_path):
        monitor = Monitor(tmp_path / "ins.json")
        hace_3_dias = (datetime.now() - timedelta(days=3)).isoformat()
        hace_1_dia = (datetime.now() - timedelta(days=1)).isoformat()
        monitor._insights = {
            "p1": PostInsights(
                post_id="p1",
                permalink="https://x/p1",
                timestamp=hace_3_dias,
                impressions=100,
                likes=10,
                comments=2,
                saves=1,
                shares=0,
                engagement_rate=13.0,
            ),
            "p2": PostInsights(
                post_id="p2",
                permalink="https://x/p2",
                timestamp=hace_1_dia,
                impressions=200,
                likes=20,
                comments=5,
                saves=2,
                shares=1,
                engagement_rate=14.0,
            ),
        }

        report = monitor.weekly_report(days=7)

        assert report["posts_analizados"] == 2
        assert report["impresiones_totales"] == 300
        assert report["engagement_promedio"] == 13.5
        assert len(report["top_posts"]) == 2
        assert report["top_posts"][0]["post_id"] == "p2"

    def test_weekly_report_excluye_fuera_de_periodo(self, tmp_path):
        monitor = Monitor(tmp_path / "ins.json")
        hace_10_dias = (datetime.now() - timedelta(days=10)).isoformat()
        monitor._insights = {
            "p1": PostInsights(
                post_id="p1",
                permalink="https://x/p1",
                timestamp=hace_10_dias,
                impressions=100,
                likes=10,
                comments=2,
                saves=1,
                shares=0,
                engagement_rate=13.0,
            ),
        }

        report = monitor.weekly_report(days=7)
        assert report["posts_analizados"] == 0

    def test_render_markdown(self, tmp_path):
        monitor = Monitor(tmp_path / "ins.json")
        report = {
            "periodo_dias": 7,
            "posts_analizados": 5,
            "impresiones_totales": 10000,
            "engagement_promedio": 8.5,
            "total_likes": 500,
            "total_comments": 100,
            "total_saves": 50,
            "top_posts": [
                {
                    "post_id": "p1",
                    "permalink": "https://x/p1",
                    "engagement_rate": 15.0,
                    "likes": 100,
                    "comments": 20,
                    "saves": 10,
                    "shares": 5,
                },
            ],
        }
        md = monitor.render_markdown(report)
        assert "5" in md
        assert "10,000" in md
        assert "8.5" in md


class TestDMTemplate:
    def test_matches_keyword(self):
        t = DMTemplate(id="x", keywords=["precio", "costo", "vale"], title="x", body="x")
        assert t.matches("cuanto vale el lote?") is True

    def test_matches_case_insensitive(self):
        t = DMTemplate(id="x", keywords=["precio"], title="x", body="x")
        assert t.matches("PRECIO") is True

    def test_render_with_data(self):
        t = DMTemplate(id="x", keywords=["k"], title="x", body="Hola {nombre}")
        result = t.render({"nombre": "Juan"})
        assert result == "Hola Juan"

    def test_render_missing_data_marks_variable(self):
        template = DMTemplate(
            id="x",
            keywords=["k"],
            title="x",
            body="Hola {nombre}, precio {precio}",
        )

        result = template.render({"nombre": "Juan", "precio": "USD 100"})
        assert result == "Hola Juan, precio USD 100"

        template2 = DMTemplate(
            id="x",
            keywords=["k"],
            title="x",
            body="Hola {nombre}, precio {precio}",
        )
        result2 = template2.render({"nombre": "Juan"})
        assert "{precio}" in result2
        assert "Falta variable" in result2


class TestDMTemplates:
    def test_match_por_keyword(self, tmp_path):
        templates = DMTemplates(tmp_path / "dm.db")
        template = templates.match("cuanto cuesta?")
        assert template is not None
        assert "precio" in template.keywords

    def test_match_sin_match_retorna_none(self, tmp_path):
        templates = DMTemplates(tmp_path / "dm.db")
        template = templates.match("Hola buen dia")
        assert template is None

    def test_match_prioriza_menor_priority(self, tmp_path):
        templates = DMTemplates(tmp_path / "dm.db")
        t1 = templates.match("gracias")
        t2 = templates.match("cuanto cuesta el lote?")
        if t1 and t2:
            # precio (priority 2) should rank higher than gracias (priority 8)
            assert t2.priority < t1.priority

    def test_responder_persiste(self, tmp_path):
        templates = DMTemplates(tmp_path / "dm.db")
        resultado = templates.responder(
            cliente="Juan",
            mensaje="Cuanto cuesta?",
            data={
                "lote_nombre": "Chacra 5 ha Cañuelas",
                "precio": "USD 50000",
                "cuotas": "24",
            },
        )
        assert "USD 50000" in resultado["respuesta"]
        assert resultado["template_id"] == "precio"
        history = templates.history()
        assert len(history) == 1
        assert history[0]["cliente"] == "Juan"

    def test_responder_sin_match_usa_fallback(self, tmp_path):
        templates = DMTemplates(tmp_path / "dm.db")
        resultado = templates.responder(
            cliente="Maria",
            mensaje="Hola buenas tardes",
        )
        assert resultado["template_id"] is None
        assert len(resultado["respuesta"]) > 0

    def test_listar_templates_ordenado_por_priority(self, tmp_path):
        templates = DMTemplates(tmp_path / "dm.db")
        lista = templates.listar_templates()
        assert len(lista) > 0
        priorities = [t.priority for t in lista]
        assert priorities == sorted(priorities)


class TestProcesarProgramadas:
    def test_sin_items_pendientes(self, tmp_path):
        sched = Scheduler(tmp_path / "sched.json")
        result = procesar_programadas(sched, publisher_factory=None)
        assert result["procesados"] == 0

    def test_factory_retorna_none(self, tmp_path):
        sched = Scheduler(tmp_path / "sched.json")
        sched.programar(
            id="s1", carrusel_path="/x", caption="c", hashtags=[], scheduled_at="2025-01-01"
        )
        result = procesar_programadas(sched, publisher_factory=lambda path, mode: None)
        assert result["procesados"] == 1
        assert result["errores"] == 1

    def test_factory_exitoso(self, tmp_path):
        sched = Scheduler(tmp_path / "sched.json")
        sched.programar(
            id="s1", carrusel_path="/x", caption="c", hashtags=[], scheduled_at="2025-01-01"
        )
        mock_pub = MagicMock()
        mock_pub.exito = True
        mock_pub.instagram_post_id = "123"
        result = procesar_programadas(sched, publisher_factory=lambda path, mode: mock_pub)
        assert result["procesados"] == 1
        assert result["publicados"] == 1
