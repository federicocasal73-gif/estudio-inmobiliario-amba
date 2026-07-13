# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 0.1.x   | :white_check_mark: |

## Reporting a Vulnerability

**No abras un Issue publico** si descubris una vulnerabilidad. En su lugar:

1. Email a tu direccion personal con subject `[SECURITY] estudio-inmobiliario-amba`
2. Incluí pasos para reproducir
3. Incluí el impacto potencial
4. Dame al menos 48 horas antes de disclosure publico

Responderé en 24-48 hs con un plan de mitigacion.

## Mejores practicas para usuarios

- **No commitees `auth.json`**: esta en `.gitignore` pero verificar antes de
  cada `git add`
- **Rota el token de Instagram cada 60 dias**: ver README_PUBLICACION_IG.md
- **Usa API keys con scopes limitados** en deployments cloud
- **No expongas el endpoint de publicacion** sin autenticacion

## Dependencias

Corremos `pip-audit` o `safety` periodicamente para detectar CVEs en
nuestras dependencias (Pillow, PyYAML, gradio-client, etc).
