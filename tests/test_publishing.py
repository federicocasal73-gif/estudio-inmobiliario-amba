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


class TestScheduledPost:
    """Tests del dataclass ScheduledPost."""

    def test_defaults(self):
        # Act
        post = ScheduledPost(
            id="test",
            carrusel_path="/x.json",
            caption="hola",
            hashtags=["#a"],
            scheduled_at="2026-07-20T19:00:00",
        )

        # Assert
        assert post.id == "test"
        assert post.status == "pending"
        assert post.attempts == 0
        assert post.last_error is None
        assert post.instagram_post_id is None

    def test_to_dict_round_trip(self):
        # Arrange
        post = ScheduledPost(
            id="test",
            carrusel_path="/x.json",
            caption="hola",
            hashtags=["#a"],
            scheduled_at="2026-07-20T19:00:00",
        )

        # Act
        d = post.to_dict()
        post2 = ScheduledPost(**d)

        # Assert
        assert post.id == post2.id
        assert post.caption == post2.caption
        assert post.hashtags == post2.hashtags


class TestScheduler:
    """Tests del Scheduler (cola persistente)."""

    def test_empty_initially(self, tmp_path):
        # Act
        scheduler = Scheduler(tmp_path / "sched.json")

        # Assert
        assert scheduler.listar() == []
        assert scheduler.stats() == {"pending": 0, "published": 0, "error": 0, "cancelled": 0}

    def test_programar_y_listar(self, tmp_path):
        # Arrange
        scheduler = Scheduler(tmp_path / "sched.json")

        # Act
        scheduler.programar(
            id="post1",
            carrusel_path="/x.json",
            caption="hola",
            hashtags=["#a"],
            scheduled_at="2026-07-20T19:00:00",
        )

        # Assert
        items = scheduler.listar()
        assert len(items) == 1
        assert items[0].id == "post1"

    def test_programar_acepta_datetime(self, tmp_path):
        # Arrange
        scheduler = Scheduler(tmp_path / "sched.json")
        fecha = datetime(2026, 7, 20, 19, 0, 0)

        # Act
        scheduler.programar(
            id="p",
            carrusel_path="/x",
            caption="c",
            hashtags=[],
            scheduled_at=fecha,
        )

        # Assert
        items = scheduler.listar()
        assert items[0].scheduled_at == fecha.isoformat()

    def test_cancelar(self, tmp_path):
        # Arrange
        scheduler = Scheduler(tmp_path / "sched.json")
        scheduler.programar(
            id="x",
            carrusel_path="/x",
            caption="c",
            hashtags=[],
            scheduled_at="2026-07-20",
        )

        # Act
        result = scheduler.cancelar("x")

        # Assert
        assert result is True
        assert scheduler.listar()[0].status == "cancelled"

    def test_cancelar_inexistente(self, tmp_path):
        # Arrange
        scheduler = Scheduler(tmp_path / "sched.json")

        # Act
        result = scheduler.cancelar("no_existe")

        # Assert
        assert result is False

    def test_eliminar(self, tmp_path):
        # Arrange
        scheduler = Scheduler(tmp_path / "sched.json")
        scheduler.programar(
            id="x",
            carrusel_path="/x",
            caption="c",
            hashtags=[],
            scheduled_at="2026-07-20",
        )

        # Act
        result = scheduler.eliminar("x")

        # Assert
        assert result is True
        assert scheduler.listar() == []

    def test_persistencia_across_instances(self, tmp_path):
        # Arrange
        path = tmp_path / "sched.json"

        # Act
        s1 = Scheduler(path)
        s1.programar(
            id="p",
            carrusel_path="/x",
            caption="c",
            hashtags=[],
            scheduled_at="2026-07-20",
        )
        s2 = Scheduler(path)

        # Assert
        assert len(s2.listar()) == 1

    def test_pendientes_a_procesar(self, tmp_path):
        # Arrange
        scheduler = Scheduler(tmp_path / "sched.json")
        # Pasada: deberia procesarse
        scheduler.programar(
            id="pasada",
            carrusel_path="/x",
            caption="c",
            hashtags=[],
            scheduled_at="2020-01-01",
        )
        # Futura: no
        scheduler.programar(
            id="futura",
            carrusel_path="/x",
            caption="c",
            hashtags=[],
            scheduled_at="2099-01-01",
        )

        # Act
        pendientes = scheduler.pendientes_a_procesar()

        # Assert
        assert len(pendientes) == 1
        assert pendientes[0].id == "pasada"

    def test_marcar_publicado(self, tmp_path):
        # Arrange
        scheduler = Scheduler(tmp_path / "sched.json")
        scheduler.programar(
            id="p",
            carrusel_path="/x",
            caption="c",
            hashtags=[],
            scheduled_at="2020-01-01",
        )

        # Act
        scheduler.marcar_publicado("p", instagram_post_id="IG_123")

        # Assert
        item = scheduler.listar()[0]
        assert item.status == "published"
        assert item.instagram_post_id == "IG_123"
        assert item.published_at is not None

    def test_marcar_error_incrementa_attempts(self, tmp_path):
        # Arrange
        scheduler = Scheduler(tmp_path / "sched.json")
        scheduler.programar(
            id="p",
            carrusel_path="/x",
            caption="c",
            hashtags=[],
            scheduled_at="2020-01-01",
        )

        # Act
        scheduler.marcar_error("p", "boom 1")
        scheduler.marcar_error("p", "boom 2")
        scheduler.marcar_error("p", "boom 3")

        # Assert
        item = scheduler.listar()[0]
        assert item.attempts == 3
        assert item.status == "error"

    def test_stats(self, tmp_path):
        # Arrange
        scheduler = Scheduler(tmp_path / "sched.json")
        scheduler.programar(
            id="s1",
            carrusel_path="/x",
            caption="c",
            hashtags=[],
            scheduled_at="2020-01-01",
        )
        scheduler.programar(
            id="s2",
            carrusel_path="/x",
            caption="c",
            hashtags=[],
            scheduled_at="2099-01-01",
        )

        # Act
        stats = scheduler.stats()

        # Assert
        assert stats["pending"] == 2
        scheduler.marcar_publicado("s1", "X")
        assert scheduler.stats()["published"] == 1


class TestInstagramInsightsClient:
    """Tests del cliente de Graph API."""

    def test_get_account_info(self):
        # Arrange
        client = InstagramInsightsClient("token_xxx", "ig_id_xxx")
        fake_response = {"id": "ig_id_xxx", "username": "test_user"}

        with patch.object(client, "_request", return_value=fake_response):
            # Act
            info = client.get_account_info()

        # Assert
        assert info["username"] == "test_user"

    def test_get_media_list(self):
        # Arrange
        client = InstagramInsightsClient("token", "ig_id")
        fake_response = {
            "data": [
                {"id": "m1", "caption": "post 1", "like_count": 10},
                {"id": "m2", "caption": "post 2", "like_count": 5},
            ]
        }

        with patch.object(client, "_request", return_value=fake_response):
            # Act
            media = client.get_media_list()

        # Assert
        assert len(media) == 2

    def test_request_network_error(self):
        # Arrange
        client = InstagramInsightsClient("token", "ig_id")

        with patch.object(client, "_request", side_effect=RuntimeError("Graph API error: 401")):
            # Act & Assert
            with pytest.raises(RuntimeError, match="Graph API error"):
                client.get_account_info()


class TestPostInsights:
    """Tests del dataclass PostInsights."""

    def test_defaults(self):
        # Act
        ins = PostInsights(
            post_id="p1",
            permalink="https://x",
            timestamp=datetime.now().isoformat(),
        )

        # Assert
        assert ins.impressions == 0
        assert ins.engagement_rate == 0.0

    def test_from_dict(self):
        # Act
        ins = PostInsights.from_dict(
            {
                "post_id": "p1",
                "permalink": "u",
                "timestamp": "t",
                "impressions": 100,
                "reach": 80,
                "likes": 5,
                "comments": 2,
                "saves": 1,
                "shares": 0,
                "engagement_rate": 8.0,
            }
        )

        # Assert
        assert ins.impressions == 100
        assert ins.engagement_rate == 8.0


class TestMonitor:
    """Tests del Monitor de insights."""

    def test_empty_initially(self, tmp_path):
        # Act
        monitor = Monitor(tmp_path / "ins.json")
        report = monitor.weekly_report()

        # Assert
        assert report["posts_analizados"] == 0

    def test_fetch_and_store_without_client(self, tmp_path):
        # Arrange
        monitor = Monitor(tmp_path / "ins.json")

        # Act
        resultado = monitor.fetch_and_store("p1")

        # Assert (sin cliente, retorna None)
        assert resultado is None

    def test_fetch_and_store_with_mock_client(self, tmp_path):
        # Arrange
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

        # Act
        resultado = monitor.fetch_and_store("p1", "https://x/p1")

        # Assert
        assert resultado is not None
        assert resultado.impressions == 1000
        assert resultado.likes == 50
        assert resultado.engagement_rate > 0

    def test_weekly_report_no_data(self, tmp_path):
        # Act
        monitor = Monitor(tmp_path / "ins.json")
        report = monitor.weekly_report(days=7)

        # Assert
        assert report["posts_analizados"] == 0
        assert report["impresiones_totales"] == 0
        assert report["top_posts"] == []

    def test_weekly_report_con_datos(self, tmp_path):
        # Arrange
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

        # Act
        report = monitor.weekly_report(days=7)

        # Assert
        assert report["posts_analizados"] == 2
        assert report["impresiones_totales"] == 300
        assert report["engagement_promedio"] == 13.5
        assert len(report["top_posts"]) == 2
        # El top post es el de mayor engagement (p2)
        assert report["top_posts"][0]["post_id"] == "p2"

    def test_weekly_report_excluye_fuera_de_periodo(self, tmp_path):
        # Arrange
        monitor = Monitor(tmp_path / "ins.json")
        hace_30_dias = (datetime.now() - timedelta(days=30)).isoformat()
        monitor._insights = {
            "p1": PostInsights(
                post_id="p1",
                permalink="u",
                timestamp=hace_30_dias,
                impressions=100,
            ),
        }

        # Act
        report = monitor.weekly_report(days=7)

        # Assert
        assert report["posts_analizados"] == 0

    def test_render_markdown(self, tmp_path):
        # Act
        monitor = Monitor(tmp_path / "ins.json")
        report = {
            "periodo_dias": 7,
            "posts_analizados": 2,
            "impresiones_totales": 300,
            "alcance_total": 250,
            "engagement_promedio": 13.5,
            "total_likes": 30,
            "total_comments": 7,
            "total_saves": 3,
            "top_posts": [
                {
                    "post_id": "p1",
                    "permalink": "https://x/p1",
                    "engagement_rate": 14.0,
                    "likes": 20,
                    "comments": 5,
                    "saves": 2,
                    "shares": 1,
                },
            ],
        }
        md = monitor.render_markdown(report)

        # Assert
        assert "Reporte semanal" in md
        assert "Posts analizados:** 2" in md
        assert "p1" in md


class TestDMTemplate:
    """Tests del dataclass DMTemplate."""

    def test_matches_keyword(self):
        # Arrange
        template = DMTemplate(
            id="precio",
            keywords=["precio", "cuanto"],
            title="Precio",
            body="cuesta {precio}",
        )

        # Act & Assert
        assert template.matches("Cuanto sale?") is True
        assert template.matches("Hola") is False

    def test_matches_case_insensitive(self):
        # Arrange
        template = DMTemplate(
            id="x",
            keywords=["PRECIO"],
            title="x",
            body="x",
        )

        # Assert
        assert template.matches("precio") is True

    def test_render_with_data(self):
        # Arrange
        template = DMTemplate(
            id="x",
            keywords=["k"],
            title="x",
            body="Hola {nombre}, el precio es {precio}",
        )

        # Act
        result = template.render({"nombre": "Juan", "precio": "USD 50000"})

        # Assert
        assert result == "Hola Juan, el precio es USD 50000"

    def test_render_missing_data_marks_variable(self):
        # Arrange
        template = DMTemplate(
            id="x",
            keywords=["k"],
            title="x",
            body="Hola {nombre}, precio {precio}",
        )

        # Act
        result = template.render({"nombre": "Juan", "precio": "USD 100"})  # OK

        # Assert (ambos provistos, no hay faltante)
        assert result == "Hola Juan, precio USD 100"

        # Ahora probamos con faltante
        template2 = DMTemplate(
            id="x",
            keywords=["k"],
            title="x",
            body="Hola {nombre}, precio {precio}",
        )
        result2 = template2.render({"nombre": "Juan"})  # falta precio
        assert "{precio}" in result2  # placeholder queda
        assert "Falta variable" in result2


class TestDMTemplates:
    """Tests del matcher de DMTemplates."""

    def test_match_por_keyword(self, tmp_path):
        # Arrange
        templates = DMTemplates(tmp_path / "dm.db")

        # Act
        template = templates.match("Cuanto cuesta el lote?")

        # Assert
        assert template is not None
        assert template.id == "precio"

    def test_match_sin_match_retorna_none(self, tmp_path):
        # Arrange
        templates = DMTemplates(tmp_path / "dm.db")

        # Act
        template = templates.match("Hola buen dia")  # sin keywords

        # Assert
        assert template is None

    def test_match_prioriza_menor_priority(self, tmp_path):
        # Arrange
        templates = DMTemplates(tmp_path / "dm.db")

        # "gracias" tiene priority=8, "precio" tiene priority=2
        # Mensaje con ambas keywords
        template = templates.match("gracias, cuanto cuesta?")

        # Assert
        assert template.id == "precio"  # priority menor gana

    def test_responder_persiste(self, tmp_path):
        # Arrange
        templates = DMTemplates(tmp_path / "dm.db")

        # Act
        resultado = templates.responder(
            cliente="Juan",
            mensaje="Cuanto cuesta?",
            data={
                "lote_nombre": "Chacra 5 ha Cañuelas",
                "precio": "USD 50000",
                "cuotas": "24",
            },
        )

        # Assert
        assert "USD 50000" in resultado["respuesta"]
        assert resultado["template_id"] == "precio"

        # Verificar historial
        history = templates.history()
        assert len(history) == 1
        assert history[0]["cliente"] == "Juan"

    def test_responder_sin_match_usa_fallback(self, tmp_path):
        # Arrange
        templates = DMTemplates(tmp_path / "dm.db")

        # Act
        resultado = templates.responder(cliente="X", mensaje="hola")

        # Assert
        assert resultado["template_id"] is None
        assert "respondemos" in resultado["respuesta"]

    def test_listar_templates_ordenado_por_priority(self, tmp_path):
        # Arrange
        templates = DMTemplates(tmp_path / "dm.db")

        # Act
        lista = templates.listar_templates()

        # Assert
        assert lista[0].priority <= lista[-1].priority
        # El primero deberia ser precio (priority=2)
        assert lista[0].id == "precio"


class TestProcesarProgramadas:
    """Tests de la funcion procesar_programadas."""

    def test_sin_items_pendientes(self, tmp_path):
        # Arrange
        scheduler = Scheduler(tmp_path / "sched.json")

        # Act
        resultado = procesar_programadas(scheduler)

        # Assert
        assert resultado["procesados"] == 0
        assert resultado["publicados"] == 0

    def test_factory_retorna_none(self, tmp_path):
        # Arrange
        scheduler = Scheduler(tmp_path / "sched.json")
        scheduler.programar(
            id="p1",
            carrusel_path="/x",
            caption="c",
            hashtags=[],
            scheduled_at="2020-01-01",  # pasada
        )

        # Act
        resultado = procesar_programadas(
            scheduler,
            publisher_factory=lambda *_: None,
        )

        # Assert
        assert resultado["procesados"] == 1
        assert resultado["publicados"] == 0
        assert resultado["errores"] == 1

    def test_factory_exitoso(self, tmp_path):
        # Arrange
        scheduler = Scheduler(tmp_path / "sched.json")
        scheduler.programar(
            id="p1",
            carrusel_path="/x",
            caption="c",
            hashtags=[],
            scheduled_at="2020-01-01",
        )

        # Mock factory que retorna resultado exitoso
        mock_resultado = MagicMock()
        mock_resultado.exito = True
        mock_resultado.instagram_post_id = "IG_999"

        # Act
        resultado = procesar_programadas(
            scheduler,
            publisher_factory=lambda *_: mock_resultado,
        )

        # Assert
        assert resultado["publicados"] == 1
        item = scheduler.listar()[0]
        assert item.status == "published"
        assert item.instagram_post_id == "IG_999"
