"""Logging estructurado del estudio.

Usa solo stdlib (logging + json) para no agregar dependencias.
El formateador JSON esta implementado a mano (sin python-json-logger).

Uso:
    from app_logging import get_logger, setup_logging

    # Configurar una vez al inicio (idempotente)
    from app_config import get_config
    setup_logging(get_config().logging)

    log = get_logger(__name__)
    log.info("Mensaje", extra={"proyecto": "X", "municipio": "Cañuelas"})
"""

from __future__ import annotations

import json
import logging
import logging.handlers
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, ClassVar

DEFAULT_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"


class JSONFormatter(logging.Formatter):
    """Formatea logs como JSON para parseo automatico por herramientas externas."""

    SKIP_KEYS: ClassVar[set[str]] = {
        "args",
        "asctime",
        "created",
        "exc_info",
        "exc_text",
        "filename",
        "funcName",
        "levelname",
        "levelno",
        "lineno",
        "message",
        "module",
        "msecs",
        "msg",
        "name",
        "pathname",
        "process",
        "processName",
        "relativeCreated",
        "stack_info",
        "thread",
        "threadName",
        "taskName",
    }

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        for key, value in record.__dict__.items():
            if key not in self.SKIP_KEYS and not key.startswith("_"):
                payload[key] = value
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False, default=str)


_CONFIGURED = False


def setup_logging(
    log_level: str = "INFO",
    log_format: str = "text",
    log_file: str | None = None,
    log_dir: Path | None = None,
    backup_count: int = 5,
) -> None:
    """Configura el sistema de logging del estudio (idempotente)."""
    global _CONFIGURED
    if _CONFIGURED:
        return

    root = logging.getLogger()
    root.handlers.clear()

    level = getattr(logging, log_level.upper(), logging.INFO)
    root.setLevel(level)

    if log_format == "json":
        formatter: logging.Formatter = JSONFormatter()
    else:
        formatter = logging.Formatter(DEFAULT_FORMAT)

    stderr_handler = logging.StreamHandler(sys.stderr)
    stderr_handler.setFormatter(formatter)
    root.addHandler(stderr_handler)

    if log_file:
        log_path = log_dir or Path("logs")
        log_path.mkdir(parents=True, exist_ok=True)
        file_handler = logging.handlers.RotatingFileHandler(
            log_path / log_file,
            maxBytes=10 * 1024 * 1024,
            backupCount=backup_count,
        )
        file_handler.setFormatter(formatter)
        root.addHandler(file_handler)

    _CONFIGURED = True


def get_logger(name: str) -> logging.Logger:
    """Devuelve un logger con el nombre dado."""
    return logging.getLogger(name)


def reset_for_tests() -> None:
    """Resetea el estado de logging (para usar en tests)."""
    global _CONFIGURED
    root = logging.getLogger()
    root.handlers.clear()
    _CONFIGURED = False


def log_timing(logger_name: str = "estudio.timing"):
    """Decorador que loggea el tiempo de ejecucion de una funcion."""
    import functools
    import time

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            logger = logging.getLogger(logger_name)
            start = time.time()
            try:
                result = func(*args, **kwargs)
                logger.info(
                    f"{func.__name__} completado",
                    extra={"duration_ms": round((time.time() - start) * 1000, 2)},
                )
                return result
            except Exception:
                logger.exception(f"Error en {func.__name__}")
                raise

        return wrapper

    return decorator
