"""Pipeline de generacion de imagenes con cache + retry + batch.

Componentes principales:
  - ImageCache:     hash(prompt) -> path. Persistente en disco (.cache/).
  - RetryPolicy:    backoff exponencial + jitter para reintentos.
  - GenerationQueue: cola SQLite para ejecutar en background (futuro).
  - BatchGenerator:  genera N imagenes en paralelo.
  - estimate_time(): cuanto va a tardar.

Es robusto a:
  - Fooocus caido (retry + fallback a stub)
  - Mismo prompt pedido dos veces (cache hit)
  - Crash a mitad de generacion (estado persistente)
  - Concurrencia (locks por archivo)
"""
from __future__ import annotations

import hashlib
import json
import logging
import random
import sqlite3
import threading
import time
import unicodedata
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

from app_config import ImageGeneratorSection, get_config
from app_logging import get_logger, log_timing
from image_generator import ImageGenerator, ImageResult, get_generator

log = get_logger("studio.generation")

CACHE_FILE_NAME = "generation_cache.json"
QUEUE_DB_FILE_NAME = "generation_queue.db"

DEFAULT_SECONDS_PER_IMAGE_FAST = 8    # SDXL en GPU buena
DEFAULT_SECONDS_PER_IMAGE_MEDIUM = 25  # SDXL en CPU / Apple Silicon
DEFAULT_SECONDS_PER_IMAGE_SLOW = 60   # en CPU puro


# ============== CACHE ==============

class ImageCache:
    """Cache de imagenes: hash(prompt + params) -> path.

    Persistente en disco via JSON. Thread-safe.
    """

    def __init__(self, cache_path: Path):
        self.cache_path = cache_path
        self._cache: dict[str, dict[str, Any]] = {}
        self._lock = threading.Lock()
        self._load()

    def _hash_key(self, prompt: str, params: dict[str, Any]) -> str:
        """Genera key unica para el (prompt, params) tuple."""
        # Normalizar prompt (quitar acentos/espacios extra)
        normalized = unicodedata.normalize("NFC", prompt.strip())
        blob = json.dumps(
            {"prompt": normalized, "params": self._normalize(params)},
            sort_keys=True, ensure_ascii=False,
        )
        return hashlib.sha256(blob.encode("utf-8")).hexdigest()

    @staticmethod
    def _normalize(d: dict[str, Any]) -> dict[str, Any]:
        """Normaliza valores para hashing estable."""
        out = {}
        for k, v in sorted(d.items()):
            if isinstance(v, (list, tuple)):
                out[k] = [str(x) for x in v]
            elif isinstance(v, Path):
                out[k] = str(v)
            else:
                out[k] = v
        return out

    def _load(self) -> None:
        """Carga cache desde disco si existe."""
        if self.cache_path.exists():
            try:
                data = json.loads(self.cache_path.read_text(encoding="utf-8"))
                self._cache = data.get("entries", {})
                log.info(f"Cache cargada: {len(self._cache)} entradas",
                         extra={"path": str(self.cache_path)})
            except (json.JSONDecodeError, OSError) as e:
                log.warning(f"No pude cargar cache, empezando vacia: {e}")
                self._cache = {}
        else:
            log.debug(f"Cache no existe, empezando vacia: {self.cache_path}")

    def _save(self) -> None:
        """Persiste cache a disco."""
        try:
            self.cache_path.parent.mkdir(parents=True, exist_ok=True)
            data = {
                "version": 1,
                "saved_at": datetime.now().isoformat(),
                "entries": self._cache,
            }
            tmp = self.cache_path.with_suffix(".tmp")
            tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False),
                           encoding="utf-8")
            tmp.replace(self.cache_path)  # atomic write
        except OSError as e:
            log.warning(f"No pude guardar cache: {e}")

    def get(self, prompt: str, params: dict[str, Any]) -> str | None:
        """Devuelve el path a la imagen cacheada, o None si no esta."""
        key = self._hash_key(prompt, params)
        with self._lock:
            entry = self._cache.get(key)
        if entry is None:
            return None
        path = Path(entry["path"])
        if not path.exists():
            log.info(f"Cache hit stale, archivo borrado: {path}")
            with self._lock:
                self._cache.pop(key, None)
            return None
        return str(path)

    def put(self, prompt: str, params: dict[str, Any], path: str) -> None:
        """Guarda una imagen en cache."""
        key = self._hash_key(prompt, params)
        with self._lock:
            self._cache[key] = {
                "path": path,
                "prompt_preview": prompt[:80],
                "created_at": datetime.now().isoformat(),
            }
            self._save()

    def clear(self) -> None:
        """Limpia toda la cache."""
        with self._lock:
            self._cache = {}
            if self.cache_path.exists():
                self.cache_path.unlink()

    def stats(self) -> dict[str, Any]:
        """Devuelve estadisticas de la cache."""
        with self._lock:
            total = len(self._cache)
            sizes = [
                Path(e["path"]).stat().st_size
                for e in self._cache.values()
                if Path(e["path"]).exists()
            ]
            return {
                "total_entries": total,
                "total_size_bytes": sum(sizes),
                "total_size_mb": round(sum(sizes) / (1024 * 1024), 2),
            }


# ============== RETRY POLICY ==============

@dataclass
class RetryPolicy:
    """Politica de reintentos con backoff exponencial + jitter."""

    max_attempts: int = 3
    initial_delay_seconds: float = 5.0
    max_delay_seconds: float = 60.0
    backoff_factor: float = 2.0
    jitter: bool = True

    def delay_for_attempt(self, attempt: int) -> float:
        """Calcula cuanto esperar antes del reintento numero `attempt` (1-indexed)."""
        if attempt < 1:
            return 0.0
        delay = self.initial_delay_seconds * (self.backoff_factor ** (attempt - 1))
        delay = min(delay, self.max_delay_seconds)
        if self.jitter:
            delay = delay * (0.5 + random.random())
        return delay


def with_retry(func: Callable[..., Any], policy: RetryPolicy,
               logger_name: str = "studio.generation.retry",
               exceptions: tuple[type[Exception], ...] = (Exception,),
               ) -> Any:
    """Ejecuta func() con reintentos segun policy.

    Levanta la ultima excepcion si todos los reintentos fallan.
    """
    log = get_logger(logger_name)
    last_exception: Exception | None = None
    for attempt in range(1, policy.max_attempts + 1):
        try:
            return func()
        except exceptions as e:
            last_exception = e
            if attempt >= policy.max_attempts:
                log.error(f"Agotados {policy.max_attempts} intentos: {e}")
                raise
            wait = policy.delay_for_attempt(attempt)
            log.warning(
                f"Intento {attempt}/{policy.max_attempts} fallo: {e}. "
                f"Reintento en {wait:.1f}s",
                extra={"attempt": attempt, "wait_seconds": wait},
            )
            time.sleep(wait)
    # No deberia llegar aca, pero por las dudas
    if last_exception:
        raise last_exception
    raise RuntimeError("with_retry: estado inesperado")


# ============== BATCH GENERATOR ==============

@dataclass
class BatchItem:
    """Item a generar en batch."""
    id: str                  # id unico para tracking
    prompt: str
    params: dict[str, Any] = field(default_factory=dict)
    output_path: Path | None = None
    use_cache: bool = True
    max_retries: int = 3

    def hash_key_params(self) -> dict[str, Any]:
        """Params que afectan el output (para hash de cache)."""
        return {
            "aspect_ratio": self.params.get("aspect_ratio", "1152*896"),
            "styles": self.params.get("styles", []),
            "negative_prompt": self.params.get("negative_prompt", ""),
            "steps": self.params.get("steps", 30),
            "cfg_scale": self.params.get("cfg_scale", 4.0),
        }


@dataclass
class BatchResult:
    """Resultado de un item del batch."""
    item_id: str
    success: bool
    output_path: str | None = None
    cache_hit: bool = False
    attempts: int = 0
    duration_seconds: float = 0.0
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class BatchGenerator:
    """Genera N imagenes en paralelo con cache + retry.

    Uso:
        gen = BatchGenerator(generator=get_generator(), max_workers=3)
        items = [
            BatchItem(id="1", prompt="...", output_path=Path("a.jpg")),
            BatchItem(id="2", prompt="...", output_path=Path("b.jpg")),
        ]
        results = gen.generate_all(items)
    """

    def __init__(self,
                 generator: ImageGenerator | None = None,
                 cache: ImageCache | None = None,
                 max_workers: int = 3,
                 retry_policy: RetryPolicy | None = None,
                 on_progress: Callable[[int, int, BatchResult], None] | None = None):
        self.generator = generator or get_generator()
        self.cache = cache or ImageCache(
            Path(".cache") / CACHE_FILE_NAME)
        self.max_workers = max_workers
        self.retry_policy = retry_policy or RetryPolicy()
        self.on_progress = on_progress

    def generate_one(self, item: BatchItem) -> BatchResult:
        """Genera una imagen individual con cache + retry."""
        log.info(f"Generando item {item.id}",
                 extra={"prompt_preview": item.prompt[:60]})

        # 1. Check cache
        if item.use_cache:
            cached_path = self.cache.get(item.prompt, item.hash_key_params())
            if cached_path:
                log.info(f"Cache hit para {item.id}: {cached_path}")
                return BatchResult(
                    item_id=item.id, success=True,
                    output_path=cached_path,
                    cache_hit=True, attempts=0, duration_seconds=0.0,
                )

        # 2. Generar con retry
        start = time.time()
        attempts = 0
        last_error: str | None = None

        for attempt in range(1, item.max_retries + 1):
            attempts = attempt
            try:
                result = self.generator.generar(
                    prompt=item.prompt,
                    output_path=item.output_path,
                    **item.params,
                )
                if item.output_path:
                    self.cache.put(
                        item.prompt, item.hash_key_params(),
                        str(item.output_path),
                    )
                duration = time.time() - start
                log.info(f"Item {item.id} generado en {duration:.1f}s "
                         f"(intento {attempt})")
                return BatchResult(
                    item_id=item.id, success=True,
                    output_path=str(item.output_path) if item.output_path else None,
                    cache_hit=False, attempts=attempt,
                    duration_seconds=duration,
                    metadata={"resultado": result.to_dict()} if result else {},
                )
            except Exception as e:
                last_error = str(e)
                if attempt < item.max_retries:
                    wait = self.retry_policy.delay_for_attempt(attempt)
                    log.warning(f"Item {item.id} intento {attempt} fallo: {e}. "
                                f"Reintento en {wait:.1f}s")
                    time.sleep(wait)

        duration = time.time() - start
        log.error(f"Item {item.id} fallo despues de {attempts} intentos: {last_error}")
        return BatchResult(
            item_id=item.id, success=False,
            cache_hit=False, attempts=attempts,
            duration_seconds=duration, error=last_error,
        )

    def generate_all(self, items: list[BatchItem]) -> list[BatchResult]:
        """Genera todos los items en paralelo."""
        if not items:
            return []
        log.info(f"Iniciando batch de {len(items)} items "
                 f"con {self.max_workers} workers")

        results: list[BatchResult | None] = [None] * len(items)
        completed = 0

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_idx = {
                executor.submit(self.generate_one, item): idx
                for idx, item in enumerate(items)
            }

            for future in as_completed(future_to_idx):
                idx = future_to_idx[future]
                result = future.result()
                results[idx] = result
                completed += 1
                if self.on_progress:
                    try:
                        self.on_progress(completed, len(items), result)
                    except Exception as e:
                        log.warning(f"on_progress call fallo: {e}")

        log.info(f"Batch completo: {completed}/{len(items)} items")
        return [r for r in results if r is not None]


# ============== ESTIMACION ==============

def estimate_time(num_items: int,
                 seconds_per_image: float = DEFAULT_SECONDS_PER_IMAGE_MEDIUM,
                 max_workers: int = 3,
                 cache_hit_rate: float = 0.0) -> dict[str, Any]:
    """Estima cuanto tardara una generacion batch.

    Args:
        num_items: cantidad de imagenes a generar.
        seconds_per_image: tiempo promedio por imagen (default = 25s, Apple Silicon).
        max_workers: cantidad de workers en paralelo.
        cache_hit_rate: 0.0 a 1.0, fraccion de cache hits esperada.

    Returns dict con: total_seconds, parallel_seconds, human_readable.
    """
    if num_items <= 0:
        return {"total_seconds": 0, "parallel_seconds": 0, "human_readable": "0s"}

    cache_hits = int(num_items * cache_hit_rate)
    cache_misses = num_items - cache_hits

    # Cache hits son instantaneos (~0.5s por overhead de I/O)
    cache_hit_seconds = cache_hits * 0.5
    # Cache misses tardan seconds_per_image cada uno, en paralelo
    if max_workers > 1 and cache_misses > 0:
        parallel_image_seconds = (cache_misses / max_workers) * seconds_per_image
    else:
        parallel_image_seconds = cache_misses * seconds_per_image

    total = cache_hit_seconds + parallel_image_seconds

    return {
        "num_items": num_items,
        "cache_hits_expected": cache_hits,
        "cache_misses_expected": cache_misses,
        "total_seconds": round(total, 1),
        "parallel_seconds": round(parallel_image_seconds, 1),
        "human_readable": _humanize_seconds(total),
    }


def _humanize_seconds(seconds: float) -> str:
    """Formatea segundos a string legible."""
    if seconds < 60:
        return f"{int(seconds)}s"
    if seconds < 3600:
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes}m {secs}s"
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    return f"{hours}h {minutes}m"


# ============== COLA DE GENERACION (preparada para Fase futura) ==============

@dataclass
class QueueItem:
    """Item en la cola de generacion."""
    id: int | None = None
    prompt: str = ""
    params_json: str = "{}"
    output_path: str | None = None
    status: str = "pending"  # pending | running | done | error
    attempts: int = 0
    last_error: str | None = None
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    finished_at: str | None = None


class GenerationQueue:
    """Cola persistente para ejecutar generaciones en background.

    Usa SQLite para persistencia. El worker en background (Fase futura)
    leera items 'pending' y los ira procesando.
    """

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self._lock = threading.Lock()
        self._init_db()

    def _init_db(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS queue (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    prompt TEXT NOT NULL,
                    params_json TEXT DEFAULT '{}',
                    output_path TEXT,
                    status TEXT DEFAULT 'pending',
                    attempts INTEGER DEFAULT 0,
                    last_error TEXT,
                    created_at TEXT NOT NULL,
                    finished_at TEXT
                )
            """)
            conn.commit()

    def enqueue(self, item: QueueItem) -> int:
        """Encola un item. Devuelve el id asignado."""
        with self._lock, sqlite3.connect(str(self.db_path)) as conn:
            cur = conn.execute(
                "INSERT INTO queue (prompt, params_json, output_path, created_at) "
                "VALUES (?, ?, ?, ?)",
                (item.prompt, item.params_json, item.output_path, item.created_at),
            )
            conn.commit()
            return cur.lastrowid or 0

    def list_pending(self, limit: int = 100) -> list[QueueItem]:
        """Devuelve items pendientes."""
        with sqlite3.connect(str(self.db_path)) as conn:
            rows = conn.execute(
                "SELECT id, prompt, params_json, output_path, status, "
                "attempts, last_error, created_at, finished_at "
                "FROM queue WHERE status='pending' ORDER BY id LIMIT ?",
                (limit,),
            ).fetchall()
        return [
            QueueItem(
                id=r[0], prompt=r[1], params_json=r[2], output_path=r[3],
                status=r[4], attempts=r[5], last_error=r[6],
                created_at=r[7], finished_at=r[8],
            ) for r in rows
        ]

    def mark_done(self, item_id: int) -> None:
        with self._lock, sqlite3.connect(str(self.db_path)) as conn:
            conn.execute(
                "UPDATE queue SET status='done', finished_at=? WHERE id=?",
                (datetime.now().isoformat(), item_id),
            )
            conn.commit()

    def mark_error(self, item_id: int, error: str) -> None:
        with self._lock, sqlite3.connect(str(self.db_path)) as conn:
            conn.execute(
                "UPDATE queue SET status='error', last_error=?, finished_at=? WHERE id=?",
                (error, datetime.now().isoformat(), item_id),
            )
            conn.commit()

    def stats(self) -> dict[str, Any]:
        with sqlite3.connect(str(self.db_path)) as conn:
            row = conn.execute(
                "SELECT status, COUNT(*) FROM queue GROUP BY status"
            ).fetchall()
        return {status: count for status, count in row}
