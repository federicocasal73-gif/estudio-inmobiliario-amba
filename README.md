# Estudio Inmobiliario AMBA

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/)
[![Pillow](https://img.shields.io/badge/Pillow-required-green.svg)](https://python-pillow.org/)
[![Fooocus](https://img.shields.io/badge/Fooocus-optional-orange.svg)](https://github.com/lllyasviel/Fooocus)
[![gradio-client](https://img.shields.io/badge/gradio--client-optional-orange.svg)](https://gradio.app/)
[![Tests](https://img.shields.io/badge/tests-154%20passed-brightgreen.svg)](tests/)
[![Coverage](https://img.shields.io/badge/coverage-41%25-yellow.svg)](tests/)
[![Argentina](https://img.shields.io/badge/Argentina-AMBBA-blue.svg)](https://github.com/)
[![Vertical: real estate](https://img.shields.io/badge/vertical-real%20estate-lightgrey.svg)]()
[![Vertical: rural](https://img.shields.io/badge/vertical-rural-lightgrey.svg)]()
[![Vertical: construction](https://img.shields.io/badge/vertical-construction-lightgrey.svg)]()

> Sistema completo para crear contenido de Instagram enfocado en lotes,
> chacras, campos, countries y servicios de construcción en la Zona
> Metropolitana de Buenos Aires (Argentina).

---

## Que hace

Genera **prompts visuales SDXL**, **captions en español rioplatense**,
**carruseles** con caption narrativo, **calendarios editoriales** semanales
con fechas clave argentinas (Día de la Madre, Padre, Black Friday, Navidad),
y **publicación automática en Instagram** via Graph API.

Incluye **43 plantillas rurales pampeanas**, **24 tipos de caption**,
**17 nichos de hashtags**, **11 tipos de carruseles**, y un manual completo
distribuido en 11 archivos `markdown`.

---

## Inicio rapido (5 minutos)

```bash
# 1. Instalar la unica dependencia obligatoria
pip install Pillow

# 2. Generar un prompt + caption de ejemplo
python3 realestate_studio.py

# 3. Probar el pipeline end-to-end
python3 studio.py demo
```

Si ves prompts y captions generados → todo OK.

---

## TL;DR: 6 ejemplos practicos

```python
from realestate_studio import RealestateStudio
from carruseles import CarruselFactory
from studio import Studio
from instagram_publisher import ModoPublicacion

studio = RealestateStudio()

# 1) Prompt visual
req = studio.lotes.chacra_pampeana(hectareas=5, municipio="Cañuelas")
print(req.prompt)

# 2) Post simple
post = studio.post.post_lote_venta(
    tema="5 ha en Cañuelas", municipio="Cañuelas",
    hectareas="5 ha", distancia_caba="65 km", tono="emotivo",
)
print(post["caption_completo"])

# 3) Carrusel
factory = CarruselFactory(studio)
carrusel = factory.lote_premium(tema="5 ha en Cañuelas",
                                  municipio="Cañuelas", hectareas=5)
factory.guardar(carrusel, "mi_carrusel",
                proyecto="chacra-canuelas-5ha")

# 4) Mejorar foto existente
from mejora_fotos import MejoraFotos
MejoraFotos().mejorar("foto.jpg", modo="magazine", intensidad="media", upscale=2)

# 5) Antes/despues de obra
from antes_despues import AntesDespuesFactory
AntesDespuesFactory(studio).generar(
    foto_antes_path="antes.jpg", modo="ia",
    cliente="Familia Pérez", tiempo_construccion_meses=8,
)

# 6) Pipeline semanal completo
Studio().pipeline_semana(
    semana_n=1, proyectos=["chacra-canuelas-5ha"],
    posts_por_semana=5, municipio_principal="Cañuelas",
    modo_publicacion=ModoPublicacion.DRY_RUN,
)
```

Mas ejemplos en `WORKFLOW_PRIMER_POST.md` y el manual completo en `MANUAL.md`.

---

## CLI

```bash
python3 studio.py demo                                          # Pipeline de demo
python3 studio.py semana --n 1 --proyectos X --publicar dry-run # Generar semana
python3 studio.py duplicar --origen X --destino Y              # Clonar proyecto
python3 studio.py publicar --carrusel path --modo dry-run       # Publicar (3 modos)
python3 studio.py preview --carrusel path                       # Preview HTML
python3 studio.py generar --carrusel path --yes                 # Generar imagenes (alias)
python3 studio.py listar                                        # Ver carruseles

# Comandos nuevos (Fase 2: pipeline de generacion):
python3 studio.py generar-carousel \
    --carrusel path --batch 4 --workers 3 --yes                # Generar con cache + batch
python3 studio.py cache-stats                                   # Ver stats de cache
python3 studio.py cache-stats --clear                           # Limpiar cache
python3 studio.py generar-cola --carrusel path                  # Encolar para background
python3 studio.py procesar-cola                                 # Procesar cola
```

## Pipeline de generacion (Fase 2)

El estudio tiene un pipeline de generacion con 3 componentes clave:

1. **Cache**: si el mismo prompt se genera 2 veces, la segunda vez usa la
   imagen ya guardada. Persistente en `.cache/generation_cache.json`.

2. **Retry**: si Fooocus falla, se reintenta con backoff exponencial + jitter
   (3 reintentos por default, configurable).

3. **Batch + paralelo**: N imagenes en paralelo con `ThreadPoolExecutor`
   (3 workers por default, configurable). Genera multiples variantes por
   slide para A/B testing.

Ejemplo:
```bash
python3 studio.py generar-carousel \
    --carrusel inmuebles/lotes/chacra-canuelas-5ha/carruseles/lote_premium/carrusel.json \
    --batch 3 --workers 5 --yes
```

Salida:
```
Carrusel: ...
Slides a generar: 15 (batch=3, workers=5, retries=3, cache=on)
  - Cache hits esperados: 8/15 (53%)
  - Tiempo estimado: 1m 30s
  [1/15] slide slide_01_v1: OK
  ...

Resultado: 15/15 OK (8 cache hits, 0 fallaron)
Cache total: 7 entradas, 1.2 MB
```

---

## Que hay en este repo

```
.
├── MANUAL.md                  ← indice del manual completo
├── manual/                    ← 10 archivos con todo lo que necesitas saber
├── realestate_studio.py       ← orquestador (92+ funciones)
├── carruseles.py              ← 11 tipos de carruseles
├── calendario_editorial.py    ← planificacion semanal + ICS + CSV
├── antes_despues.py           ← flujo 3 modos para obras
├── mejora_fotos.py            ← 5 looks (magazine, golden hour, pampa)
├── validators.py              ← validaciones IG (caption, hashtags)
├── image_generator.py         ← stub + cliente Fooocus real
├── preview_html.py            ← preview self-contained
├── caption_variants.py        ← A/B testing de captions
├── historial_publicaciones.py ← rotacion inteligente
├── studio.py                  ← pipeline + CLI (7 subcomandos)
├── instagram_auth.py          ← auth IG
├── instagram_publisher.py     ← publicador (DRY_RUN / INTERACTIVO / REAL)
├── cloudinary_upload.py       ← upload a Cloudinary
│
├── prompts_inmobiliarios.json  ← 43 plantillas SDXL
├── captions_instagram.json     ← 24 tipos + 17 nichos
├── auth_instagram_example.json ← plantilla para auth.json
│
├── TOPICS.md                   ← tags para GitHub (config manual)
├── README.md                   ← este archivo
├── CHEATSHEET.md               ← 17 ejemplos copy-paste
├── TROUBLESHOOTING.md          ← 15 errores con fix
├── WORKFLOW_PRIMER_POST.md     ← paso a paso del primer post
└── LICENSE                     ← MIT
```

---

## Stats

| Metrica | Valor |
|---|---|
| Modulos Python | 14 |
| Plantillas de prompts SDXL | 43 |
| Tipos de caption rioplatenses | 24 |
| Nichos de hashtags | 17 |
| Tipos de carruseles | 11 |
| Subcomandos CLI | 7 |
| Metodos `post_*` en CaptionFactory | 23 |
| Funciones VerticalLotes | 17 |
| Funciones VerticalConstruccion | 28 |
| Manual (archivos .md) | 13 |

---

## Documentacion

- **[`MANUAL.md`](MANUAL.md)**: indice del manual completo
- **[`manual/01-vision-y-alcance.md`](manual/01-vision-y-alcance.md)**: que hace y que NO hace
- **[`manual/02-arquitectura.md`](manual/02-arquitectura.md)**: diagrama de modulos
- **[`manual/03-instalacion.md`](manual/03-instalacion.md)**: setup paso a paso
- **[`manual/04-casos-de-uso.md`](manual/04-casos-de-uso.md)**: 6 ejemplos end-to-end
- **[`manual/05-modulos.md`](manual/05-modulos.md)**: referencia de los 11 modulos
- **[`manual/06-comandos-cli.md`](manual/06-comandos-cli.md)**: CLI completo
- **[`manual/07-flujos-end-to-end.md`](manual/07-flujos-end-to-end.md)**: pipelines
- **[`manual/08-publicacion-instagram.md`](manual/08-publicacion-instagram.md)**: Meta + Cloudinary
- **[`manual/09-limitaciones-y-workarounds.md`](manual/09-limitaciones-y-workarounds.md)**: 15 limitaciones
- **[`manual/10-personalizacion.md`](manual/10-personalizacion.md)**: como extender
- **[`CHEATSHEET.md`](CHEATSHEET.md)**: 17 ejemplos copy-paste
- **[`TROUBLESHOOTING.md`](TROUBLESHOOTING.md)**: 15 errores comunes
- **[`WORKFLOW_PRIMER_POST.md`](WORKFLOW_PRIMER_POST.md)**: primer post paso a paso

---

## Setup completo (30 min para publicar de verdad)

1. ✅ Instalar Pillow (5 min)
2. ▶️ Arrancar Fooocus local (10 min, opcional)
3. ▶️ Setup Meta + Cloudinary (15 min, ver [`README_PUBLICACION_IG.md`](README_PUBLICACION_IG.md))

Sin Fooocus: el estudio genera prompts para pegar en Midjourney/DALL-E/Flux.
Sin Meta+Cloudinary: el estudio funciona en `--modo dry-run` (no publica, simula).

---

## Licencia

MIT - ver [`LICENSE`](LICENSE). © 2026.

---

> Si este sistema te sirve para generar contenido inmobiliario real,
> considera dar una star en GitHub ⭐
