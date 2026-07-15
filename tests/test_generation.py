"""Tests del modulo de generacion (cache, retry, batch, estimacion)."""

from __future__ import annotations

import json
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from generation_pipeline import (
    BatchGenerator,
    BatchItem,
    BatchResult,
    GenerationQueue,
    ImageCache,
    QueueItem,
    RetryPolicy,
    _humanize_seconds,
    estimate_time,
    with_retry,
)


class TestRetryPolicy:
    """Tests de la politica de retry."""

    def test_initial_delay(self):
        # Arrange
        policy = RetryPolicy(initial_delay_seconds=5.0, backoff_factor=2.0, jitter=False)

        # Act
        delay = policy.delay_for_attempt(1)

        # Assert
        assert delay == 5.0

    def test_exponential_growth(self):
        # Arrange
        policy = RetryPolicy(
            initial_delay_seconds=1.0, backoff_factor=2.0, jitter=False, max_delay_seconds=1000.0
        )

        # Act & Assert
        assert policy.delay_for_attempt(1) == 1.0
        assert policy.delay_for_attempt(2) == 2.0
        assert policy.delay_for_attempt(3) == 4.0
        assert policy.delay_for_attempt(4) == 8.0

    def test_max_delay_cap(self):
        # Arrange
        policy = RetryPolicy(
            initial_delay_seconds=1.0, backoff_factor=10.0, max_delay_seconds=50.0, jitter=False
        )

        # Act
        delay = policy.delay_for_attempt(5)

        # Assert
        assert delay == 50.0  # capped

    def test_jitter_makes_non_deterministic(self):
        # Arrange
        policy = RetryPolicy(initial_delay_seconds=10.0, jitter=True)

        # Act
        delays = [policy.delay_for_attempt(1) for _ in range(10)]

        # Assert (al menos 2 valores distintos por el jitter)
        assert len(set(delays)) >= 2

    def test_jitter_range(self):
        # Arrange
        policy = RetryPolicy(initial_delay_seconds=10.0, jitter=True)

        # Act
        for _ in range(50):
            delay = policy.delay_for_attempt(1)
            # Jitter es entre 0.5x y 1.5x
            assert 5.0 <= delay <= 15.0


class TestWithRetryDecorator:
    """Tests del helper with_retry."""

    def test_success_first_attempt(self):
        # Arrange
        calls = []

        def func():
            calls.append(1)
            return "ok"

        # Act
        result = with_retry(func, RetryPolicy(max_attempts=3))

        # Assert
        assert result == "ok"
        assert len(calls) == 1

    def test_retries_on_exception(self):
        # Arrange
        calls = [0]

        def func():
            calls[0] += 1
            if calls[0] < 3:
                raise ValueError("fail")
            return "ok"

        # Act
        policy = RetryPolicy(max_attempts=3, initial_delay_seconds=0.01)
        result = with_retry(func, policy, exceptions=(ValueError,))

        # Assert
        assert result == "ok"
        assert calls[0] == 3

    def test_raises_after_max_attempts(self):
        # Arrange
        def func():
            raise ValueError("always fails")

        # Act & Assert
        policy = RetryPolicy(max_attempts=2, initial_delay_seconds=0.01)
        with pytest.raises(ValueError, match="always fails"):
            with_retry(func, policy, exceptions=(ValueError,))


class TestHumanizeSeconds:
    """Tests del formateador de tiempo."""

    @pytest.mark.parametrize(
        "seconds,expected",
        [
            (0, "0s"),
            (5, "5s"),
            (59, "59s"),
            (60, "1m 0s"),
            (90, "1m 30s"),
            (3600, "1h 0m"),
            (3660, "1h 1m"),
            (7200, "2h 0m"),
        ],
    )
    def test_humanize(self, seconds, expected):
        # Act & Assert
        assert _humanize_seconds(seconds) == expected


class TestEstimateTime:
    """Tests de la estimacion de tiempo."""

    def test_zero_items(self):
        # Act
        result = estimate_time(0)

        # Assert
        assert result["total_seconds"] == 0

    def test_serial_estimation(self):
        # Arrange
        result = estimate_time(
            num_items=4,
            seconds_per_image=10.0,
            max_workers=1,
            cache_hit_rate=0.0,
        )

        # Assert (sin paralelismo: 4 * 10 = 40s)
        assert result["total_seconds"] == 40.0

    def test_parallel_estimation(self):
        # Arrange
        result = estimate_time(
            num_items=6,
            seconds_per_image=10.0,
            max_workers=3,
            cache_hit_rate=0.0,
        )

        # Assert (con 3 workers: ceil(6/3) * 10 = 20s)
        assert result["total_seconds"] == 20.0

    def test_cache_hits_reduce_time(self):
        # Arrange
        result = estimate_time(
            num_items=10,
            seconds_per_image=10.0,
            max_workers=3,
            cache_hit_rate=0.5,  # 50% cache hits
        )

        # Assert (5 cache hits = 2.5s, 5 misses paralelos = 16.67s)
        assert result["total_seconds"] < 20.0
        assert result["cache_hits_expected"] == 5

    def test_human_readable_present(self):
        # Act
        result = estimate_time(60, seconds_per_image=60.0, max_workers=1)

        # Assert
        assert "human_readable" in result
        assert "h" in result["human_readable"]  # 60min = 1h


class TestImageCache:
    """Tests del cache de imagenes."""

    def test_get_missing_returns_none(self, tmp_path):
        # Arrange
        cache = ImageCache(tmp_path / "cache.json")

        # Act
        result = cache.get("prompt x", {"aspect": "1:1"})

        # Assert
        assert result is None

    def test_put_then_get(self, tmp_path):
        # Arrange
        cache = ImageCache(tmp_path / "cache.json")
        image_path = tmp_path / "image.jpg"
        image_path.write_bytes(b"fake image")

        # Act
        cache.put("test prompt", {"aspect": "1:1"}, str(image_path))
        result = cache.get("test prompt", {"aspect": "1:1"})

        # Assert
        assert result == str(image_path)

    def test_different_params_different_keys(self, tmp_path):
        # Arrange
        cache = ImageCache(tmp_path / "cache.json")
        path_a = tmp_path / "a.jpg"
        path_b = tmp_path / "b.jpg"
        path_a.write_bytes(b"a")
        path_b.write_bytes(b"b")

        # Act
        cache.put("same prompt", {"aspect": "1:1"}, str(path_a))
        cache.put("same prompt", {"aspect": "16:9"}, str(path_b))

        # Assert
        assert cache.get("same prompt", {"aspect": "1:1"}) == str(path_a)
        assert cache.get("same prompt", {"aspect": "16:9"}) == str(path_b)

    def test_persistence_across_instances(self, tmp_path):
        # Arrange
        path = tmp_path / "image.jpg"
        path.write_bytes(b"x")
        cache_file = tmp_path / "cache.json"

        # Act
        c1 = ImageCache(cache_file)
        c1.put("p", {}, str(path))
        c2 = ImageCache(cache_file)

        # Assert
        assert c2.get("p", {}) == str(path)

    def test_stale_entry_detected(self, tmp_path):
        # Arrange
        cache = ImageCache(tmp_path / "cache.json")
        # Ponemos un path que no existe
        cache.put("p", {}, "/nonexistent/path.jpg")

        # Act
        result = cache.get("p", {})

        # Assert
        assert result is None

    def test_clear(self, tmp_path):
        # Arrange
        cache = ImageCache(tmp_path / "cache.json")
        cache.put("a", {}, "/tmp/a.jpg")
        cache.put("b", {}, "/tmp/b.jpg")

        # Act
        cache.clear()

        # Assert
        assert cache.get("a", {}) is None
        assert cache.get("b", {}) is None

    def test_stats(self, tmp_path):
        # Arrange
        cache = ImageCache(tmp_path / "cache.json")
        for i in range(3):
            p = tmp_path / f"img_{i}.jpg"
            p.write_bytes(b"x" * 100)
            cache.put(f"p{i}", {}, str(p))

        # Act
        stats = cache.stats()

        # Assert
        assert stats["total_entries"] == 3
        assert stats["total_size_bytes"] == 300


class TestBatchItem:
    """Tests del dataclass BatchItem."""

    def test_hash_key_params_defaults(self):
        # Arrange
        item = BatchItem(id="1", prompt="test")

        # Act
        params = item.hash_key_params()

        # Assert
        assert params["aspect_ratio"] == "1152*896"
        assert params["steps"] == 30
        assert params["cfg_scale"] == 4.0


class TestBatchGenerator:
    """Tests del BatchGenerator con mocks."""

    def test_generate_all_calls_generator(self, tmp_path):
        # Arrange
        mock_gen = MagicMock()
        mock_result = MagicMock()
        mock_result.output_path = str(tmp_path / "img_0.jpg")
        mock_gen.generar.return_value = mock_result

        cache = ImageCache(tmp_path / "cache.json")
        gen = BatchGenerator(generator=mock_gen, cache=cache, max_workers=2)

        items = [
            BatchItem(id="0", prompt="a", output_path=tmp_path / "img_0.jpg"),
            BatchItem(id="1", prompt="b", output_path=tmp_path / "img_1.jpg"),
        ]

        # Act
        results = gen.generate_all(items)

        # Assert
        assert len(results) == 2
        assert all(r.success for r in results)
        assert mock_gen.generar.call_count == 2

    def test_cache_hit_avoids_generator(self, tmp_path):
        # Arrange
        mock_gen = MagicMock()  # No debe ser llamado

        image_path = tmp_path / "cached.jpg"
        image_path.write_bytes(b"x")

        cache = ImageCache(tmp_path / "cache.json")
        cache.put(
            "cached",
            {
                "aspect_ratio": "1152*896",
                "styles": [],
                "negative_prompt": "",
                "steps": 30,
                "cfg_scale": 4.0,
            },
            str(image_path),
        )

        gen = BatchGenerator(generator=mock_gen, cache=cache)
        items = [BatchItem(id="0", prompt="cached", output_path=tmp_path / "out.jpg")]

        # Act
        results = gen.generate_all(items)

        # Assert
        assert len(results) == 1
        assert results[0].cache_hit is True
        assert mock_gen.generar.call_count == 0

    def test_use_cache_false_skips_cache(self, tmp_path):
        # Arrange
        mock_gen = MagicMock()
        mock_result = MagicMock()
        mock_result.output_path = str(tmp_path / "img.jpg")
        mock_gen.generar.return_value = mock_result

        cache = ImageCache(tmp_path / "cache.json")
        cache.put(
            "p",
            {
                "aspect_ratio": "1152*896",
                "styles": [],
                "negative_prompt": "",
                "steps": 30,
                "cfg_scale": 4.0,
            },
            str(tmp_path / "cached.jpg"),
        )

        gen = BatchGenerator(generator=mock_gen, cache=cache)
        items = [
            BatchItem(id="0", prompt="p", output_path=tmp_path / "out.jpg", use_cache=False),
        ]

        # Act
        results = gen.generate_all(items)

        # Assert
        assert results[0].cache_hit is False
        assert mock_gen.generar.call_count == 1  # forzo regeneracion

    def test_retry_then_success(self, tmp_path):
        # Arrange
        call_count = [0]

        def mock_generar(prompt, output_path=None, **kwargs):
            call_count[0] += 1
            if call_count[0] < 2:
                raise RuntimeError("fooocus down")
            r = MagicMock()
            r.output_path = str(output_path)
            return r

        mock_gen = MagicMock()
        mock_gen.generar.side_effect = mock_generar

        cache = ImageCache(tmp_path / "cache.json")
        gen = BatchGenerator(
            generator=mock_gen,
            cache=cache,
            retry_policy=RetryPolicy(max_attempts=3, initial_delay_seconds=0.01),
        )
        items = [
            BatchItem(id="0", prompt="p", output_path=tmp_path / "out.jpg", max_retries=3),
        ]

        # Act
        results = gen.generate_all(items)

        # Assert
        assert results[0].success is True
        assert results[0].attempts == 2

    def test_retry_exhausted_returns_error(self, tmp_path):
        # Arrange
        mock_gen = MagicMock()
        mock_gen.generar.side_effect = RuntimeError("always fail")

        cache = ImageCache(tmp_path / "cache.json")
        gen = BatchGenerator(
            generator=mock_gen,
            cache=cache,
            retry_policy=RetryPolicy(max_attempts=2, initial_delay_seconds=0.01),
        )
        items = [
            BatchItem(id="0", prompt="p", output_path=tmp_path / "out.jpg", max_retries=2),
        ]

        # Act
        results = gen.generate_all(items)

        # Assert
        assert results[0].success is False
        assert "always fail" in results[0].error
        assert results[0].attempts == 2

    def test_empty_list_returns_empty(self, tmp_path):
        # Arrange
        gen = BatchGenerator()

        # Act
        results = gen.generate_all([])

        # Assert
        assert results == []

    def test_progress_callback_called(self, tmp_path):
        # Arrange
        mock_gen = MagicMock()
        mock_result = MagicMock()
        mock_result.output_path = "/tmp/x.jpg"
        mock_gen.generar.return_value = mock_result

        gen = BatchGenerator(generator=mock_gen)
        progress_calls = []

        def on_progress(completed, total, result):
            progress_calls.append((completed, total, result.item_id))

        gen.on_progress = on_progress
        items = [
            BatchItem(id=f"id{i}", prompt="p", output_path=tmp_path / f"x{i}.jpg") for i in range(3)
        ]

        # Act
        gen.generate_all(items)

        # Assert
        assert len(progress_calls) == 3
        assert all(total == 3 for _, total, _ in progress_calls)
        assert sorted([c for c, _, _ in progress_calls]) == [1, 2, 3]


class TestGenerationQueue:
    """Tests de la cola persistente SQLite."""

    def test_enqueue_returns_id(self, tmp_path):
        # Arrange
        queue = GenerationQueue(tmp_path / "queue.db")

        # Act
        item_id = queue.enqueue(QueueItem(prompt="test", output_path="/tmp/a.jpg"))

        # Assert
        assert item_id > 0

    def test_list_pending_returns_items(self, tmp_path):
        # Arrange
        queue = GenerationQueue(tmp_path / "queue.db")
        queue.enqueue(QueueItem(prompt="p1", output_path="/tmp/a.jpg"))
        queue.enqueue(QueueItem(prompt="p2", output_path="/tmp/b.jpg"))

        # Act
        items = queue.list_pending()

        # Assert
        assert len(items) == 2
        prompts = [i.prompt for i in items]
        assert "p1" in prompts
        assert "p2" in prompts

    def test_mark_done_changes_status(self, tmp_path):
        # Arrange
        queue = GenerationQueue(tmp_path / "queue.db")
        item_id = queue.enqueue(QueueItem(prompt="p", output_path="/tmp/a.jpg"))

        # Act
        queue.mark_done(item_id)

        # Assert
        items = queue.list_pending()
        assert all(i.id != item_id for i in items)

    def test_mark_error(self, tmp_path):
        # Arrange
        queue = GenerationQueue(tmp_path / "queue.db")
        item_id = queue.enqueue(QueueItem(prompt="p", output_path="/tmp/a.jpg"))

        # Act
        queue.mark_error(item_id, "boom")

        # Assert
        items = queue.list_pending()
        assert all(i.id != item_id for i in items)

    def test_stats(self, tmp_path):
        # Arrange
        queue = GenerationQueue(tmp_path / "queue.db")
        i1 = queue.enqueue(QueueItem(prompt="a", output_path="/tmp/a.jpg"))
        i2 = queue.enqueue(QueueItem(prompt="b", output_path="/tmp/b.jpg"))
        queue.mark_done(i1)
        queue.mark_error(i2, "x")

        # Act
        stats = queue.stats()

        # Assert
        assert stats.get("done") == 1
        assert stats.get("error") == 1

    def test_persistence_across_instances(self, tmp_path):
        # Arrange
        db = tmp_path / "queue.db"

        # Act
        q1 = GenerationQueue(db)
        q1.enqueue(QueueItem(prompt="persistent", output_path="/tmp/a.jpg"))
        q2 = GenerationQueue(db)

        # Assert
        items = q2.list_pending()
        assert any(i.prompt == "persistent" for i in items)
