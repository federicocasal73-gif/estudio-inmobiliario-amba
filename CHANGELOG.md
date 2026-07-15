# Changelog

Todos los cambios notables de este proyecto se documentaran aca.

El formato sigue [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
y este proyecto se adhiere a [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Fase 1 Foundation: sistema de configuracion jerarquica, logging estructurado, tests pytest, CI/CD con GitHub Actions, governance (CODEOWNERS, CONTRIBUTING, SECURITY, CoC).
- Fase 2 Pipeline: cache de imagenes (hash + JSON), retry con backoff exponencial + jitter, batch paralelo con ThreadPoolExecutor, cola persistente SQLite para background jobs, estimacion de tiempo, 4 nuevos subcomandos CLI (`generar-carousel`, `cache-stats`, `generar-cola`, `procesar-cola`).
- 57 tests nuevos (97 → 154, 41% coverage).
- Skills de `autoskills` instaladas (solo local, ignoradas via .gitignore).

### Changed
- Migrado a `pyproject.toml` (PEP 621).
- Bugfix: handlers del CLI ahora propagan return codes a `sys.exit`.
- Bugfix: alias `generar` ahora acepta `--yes`.

## [0.2.0] - 2026-07-XX

### Added
- Pipeline de generacion con cache + retry + batch.
- 154 tests pytest.

## [0.1.0] - 2026-07-XX

### Added
- 14 modulos Python para generacion de contenido inmobiliario.
- 43 plantillas de prompts SDXL rurales pampeanas.
- 24 tipos de caption rioplatenses con hashtags zonales.
- 17 nichos de hashtags.
- 11 tipos de carruseles automaticos.
- Cliente real de Fooocus con gradio-client.
- Publicador Instagram con 3 modos (DRY_RUN, INTERACTIVO, REAL).
- Manual completo en 11 archivos.

## [0.1.0] - 2026-07-XX

### Added
- 14 modulos Python para generacion de contenido inmobiliario.
- 43 plantillas de prompts SDXL rurales pampeanas.
- 24 tipos de caption rioplatenses con hashtags zonales.
- 17 nichos de hashtags.
- 11 tipos de carruseles automaticos.
- Cliente real de Fooocus con gradio-client.
- Publicador Instagram con 3 modos (DRY_RUN, INTERACTIVO, REAL).
- Manual completo en 11 archivos.
