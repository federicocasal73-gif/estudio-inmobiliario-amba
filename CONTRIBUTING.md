# Contributing a Estudio Inmobiliario AMBA

Gracias por tu interes en contribuir. Este documento explica como hacerlo.

## Code of Conduct

Seas cual sea tu rol (cliente, contributor, sponsor), trata a todos con
respeto. No toleramos acoso ni discriminacion de ningun tipo.

## Como contribuir

### 1. Reportar un bug

Abre un [Issue](../../issues/new) con:
- Titulo descriptivo (no "no anda")
- Version del estudio (`cat pyproject.toml | grep version`)
- Pasos para reproducir
- Comportamiento esperado vs observado
- Capturas si aplica

### 2. Proponer una feature

Abre un Issue con el tag `enhancement` primero. Discutimos antes de codear
para evitar trabajo desperdiciado.

### 3. Pull Requests

1. **Fork** el repo y crea tu branch desde `main`:
   ```bash
   git checkout -b feat/mi-feature
   ```

2. **Coding style** sigue el formato de ruff (`ruff format .`). El CI falla
   si no pasa:
   ```bash
   pip install ruff
   ruff check .
   ruff format --check .
   ```

3. **Tests**: agregá tests para cualquier cambio. Cobertura minima 70%.
   ```bash
   pytest tests/
   ```

4. **Commit messages** siguiendo [Conventional Commits](https://www.conventionalcommits.org/):
   - `feat:` nueva feature
   - `fix:` bug fix
   - `docs:` solo documentacion
   - `refactor:` cambio interno sin cambio funcional
   - `test:` solo tests
   - `chore:` tareas de mantenimiento

   Ejemplo: `feat: agregar carrusel de hipoteca UVA`

5. **Push y abre PR** apuntando a `main`. El CI corre tests + lint
   automaticamente.

6. **Espera review**. El CODEOWNERS se asigna el reviewer apropiado.

## Setup local para contribuidores

```bash
git clone https://github.com/federicocasal73-gif/estudio-inmobiliario-amba.git
cd estudio-inmobiliario-amba
pip install -e ".[dev]"
pytest tests/
```

## Versioning

Usamos [Semantic Versioning](https://semver.org/). Las releases se crean
automaticamente via GitHub Actions cuando se pushea un tag `v*`.

## Licencia

Al contribuir, aceptás que tu código se publique bajo la misma licencia
MIT del proyecto. Ver [LICENSE](LICENSE).
