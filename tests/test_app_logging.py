"""Tests del modulo de logging estructurado.

Patron: AAA, captura de logs con caplog (fixture de pytest).
"""
from __future__ import annotations

import json
import logging

from app_logging import (
    JSONFormatter,
    get_logger,
    log_timing,
    reset_for_tests,
    setup_logging,
)


class TestJSONFormatter:
    """Tests del formateador JSON."""

    def test_formats_basic_record(self):
        # Arrange
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="hello %s",
            args=("world",),
            exc_info=None,
        )

        # Act
        result = formatter.format(record)

        # Assert
        parsed = json.loads(result)
        assert parsed["level"] == "INFO"
        assert parsed["logger"] == "test"
        assert parsed["message"] == "hello world"

    def test_includes_extra_fields(self):
        # Arrange
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="event occurred",
            args=(),
            exc_info=None,
        )
        record.proyecto = "chacra-canuelas-5ha"
        record.municipio = "Cañuelas"

        # Act
        result = formatter.format(record)

        # Assert
        parsed = json.loads(result)
        assert parsed["proyecto"] == "chacra-canuelas-5ha"
        assert parsed["municipio"] == "Cañuelas"

    def test_excludes_internal_fields(self):
        # Arrange
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="msg",
            args=(),
            exc_info=None,
        )

        # Act
        result = formatter.format(record)

        # Assert
        parsed = json.loads(result)
        # Los siguientes campos NO deben aparecer
        assert "args" not in parsed
        assert "msecs" not in parsed
        assert "threadName" not in parsed
        # Pero los utiles SI
        assert "timestamp" in parsed
        assert "level" in parsed
        assert "message" in parsed


class TestSetupLogging:
    """Tests del setup del sistema de logging."""

    def teardown_method(self):
        reset_for_tests()

    def test_setup_is_idempotent(self):
        # Arrange
        setup_logging("INFO", "text")
        handlers_first = list(logging.getLogger().handlers)

        # Act
        setup_logging("DEBUG", "json")
        handlers_second = list(logging.getLogger().handlers)

        # Assert (no debe duplicar handlers)
        assert len(handlers_first) == len(handlers_second)

    def test_setup_respects_log_level(self):
        # Arrange
        setup_logging("WARNING", "text")

        # Act
        root_level = logging.getLogger().level

        # Assert
        assert root_level == logging.WARNING


class TestGetLogger:
    """Tests de get_logger."""

    def teardown_method(self):
        reset_for_tests()

    def test_get_logger_returns_named_logger(self):
        # Act
        log = get_logger("test.module")

        # Assert
        assert log.name == "test.module"
        assert isinstance(log, logging.Logger)


class TestLogTiming:
    """Tests del decorador log_timing."""

    def teardown_method(self):
        reset_for_tests()

    def test_log_timing_logs_duration(self):
        # Arrange
        setup_logging("INFO", "text")
        log = get_logger("test.timing")
        captured = []

        class CaptureHandler(logging.Handler):
            def emit(self, record):
                captured.append(record)

        handler = CaptureHandler()
        log.addHandler(handler)

        # Act
        @log_timing("test.timing")
        def funcion_rapida():
            return "ok"

        result = funcion_rapida()

        # Assert
        assert result == "ok"
        assert len(captured) >= 1
        # Verificar que alguno tenga duration_ms
        durations = [getattr(r, "duration_ms", None) for r in captured]
        assert any(d is not None for d in durations)
