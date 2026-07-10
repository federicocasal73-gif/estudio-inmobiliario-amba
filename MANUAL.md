# Manual del Estudio Inmobiliario AMBA

Sistema completo para crear contenido de Instagram enfocado en lotes,
chacras, campos, countries y servicios de construccion en la Zona
Metropolitana de Buenos Aires (Argentina).

## A quien esta dirigido

Este estudio es para vos si:

- Vendes **lotes, chacras, campos, countries o barrios cerrados** en Buenos Aires y el AMBA
- Ofreces **servicios de construccion** (llave en mano, movimiento de suelo, steel frame, etc)
- Necesitas contenido de Instagram de manera **recurrente** sin empezar de cero cada vez
- Queres **automatizar la planificacion** y publicacion

## TL;DR: arrancar en 5 minutos

```bash
# 1. Instalar dependencia
pip install Pillow

# 2. Generar un post de venta
python3 -c "
from realestate_studio import RealestateStudio
s = RealestateStudio()
post = s.post.post_lote_venta(
    tema='5 ha en Cañuelas',
    municipio='Cañuelas',
    hectareas='5 ha',
    distancia_caba='65 km',
    tono='emotivo',
)
print(post['caption_completo'])
"

# 3. Probar los demos
python3 realestate_studio.py        # prompts y captions
python3 generar_proyecto_ejemplo.py # proyecto completo
python3 studio.py demo               # pipeline end-to-end
```

Eso es todo. El resto del manual te dice que mas podes hacer.

## Indice del manual

| # | Documento | Que cubre |
|---|---|---|
| 01 | [Vision y alcance](manual/01-vision-y-alcance.md) | Que hace y que NO hace el estudio |
| 02 | [Arquitectura](manual/02-arquitectura.md) | Diagrama de modulos, flujo de datos |
| 03 | [Instalacion](manual/03-instalacion.md) | Setup paso a paso, requisitos, verificacion |
| 04 | [Casos de uso](manual/04-casos-de-uso.md) | 6 ejemplos practicos end-to-end |
| 05 | [Modulos](manual/05-modulos.md) | Referencia de los 11 modulos (1 parrafo c/u) |
| 06 | [Comandos CLI](manual/06-comandos-cli.md) | Los 7 subcomandos de `studio.py` |
| 07 | [Flujos end-to-end](manual/07-flujos-end-to-end.md) | Pipelines automaticos completos |
| 08 | [Publicacion Instagram](manual/08-publicacion-instagram.md) | Setup Meta + Cloudinary, los 3 modos |
| 09 | [Limitaciones y workarounds](manual/09-limitaciones-y-workarounds.md) | 15 limitaciones con solucion |
| 10 | [Personalizacion](manual/10-personalizacion.md) | Como agregar tus propios templates |

## Documentos adicionales en este repo

| Archivo | Para que sirve |
|---|---|
| `README_INMOBILIARIO.md` | Referencia rapida de los modulos (1 parrafo por modulo) |
| `CHEATSHEET.md` | 17 ejemplos copy-paste de los comandos mas usados |
| `TROUBLESHOOTING.md` | 15 errores comunes con solucion |
| `WORKFLOW_PRIMER_POST.md` | Paso a paso del primer post desde cero |
| `README_PUBLICACION_IG.md` | Setup especifico de Meta Business + Cloudinary |

## Stack tecnologico

**Lenguaje**: Python 3.10+ (testeado en 3.14)

**Dependencias obligatorias** (1 sola):
- `Pillow` >= 10.0.0 (para mejora de fotos y manipulacion basica)

**Dependencias opcionales**:
- `gradio-client` (para conectar con Fooocus real, generar imagenes automaticas)

**Sin Fooocus corriendo**: el estudio sigue funcionando, solo que las imagenes no se generan automaticamente (te da los prompts para pegar en Midjourney, DALL-E, Flux, o en la UI web de Fooocus).

**Sin Meta+Cloudinary configurados**: el estudio funciona en `DRY_RUN` (no publica, simula).

## TL;DR tecnico: cuantos modulos hay

- **11 modulos Python** (~3300 lineas)
- **92 funciones** en `realestate_studio.py` (vertical lotes + construccion)
- **26 funciones** en `carruseles.py` (11 tipos de carrusel)
- **23 metodos** `post_*` en `CaptionFactory`
- **43 plantillas** de prompts SDXL
- **24 tipos de caption** rioplatenses
- **17 nichos** de hashtags
- **7 subcomandos** CLI en `studio.py`

## Empezar ya

1. Lee [01-vision-y-alcance.md](manual/01-vision-y-alcance.md) (5 min)
2. Sigue [03-instalacion.md](manual/03-instalacion.md) (10 min)
3. Proba los 6 ejemplos de [04-casos-de-uso.md](manual/04-casos-de-uso.md) (30 min)

En 45 minutos estas produciendo contenido para tu cuenta de Instagram.

## Licencia

MIT. Ver `LICENSE`.