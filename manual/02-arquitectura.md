# 02 - Arquitectura del sistema

## Diagrama general

```
                         ┌──────────────────────────────┐
                         │       data (JSONs)            │
                         │  prompts_inmobiliarios.json    │
                         │  captions_instagram.json       │
                         └──────────────────────────────┘
                                       │
                          ┌────────────┴────────────┐
                          ▼                         ▼
              ┌────────────────────┐    ┌──────────────────────┐
              │ realestate_studio.py│    │  caption_variants.py │
              │ (orquestador)       │    │  (A/B testing)       │
              │                    │    └──────────────────────┘
              │ - VerticalLotes    │
              │   17 funciones     │    ┌──────────────────────┐
              │ - VerticalConstruc │    │ historial_publicaciones│
              │   28 funciones     │◄──┤ (rotacion proyectos) │
              │ - CaptionFactory   │    └──────────────────────┘
              │   23 metodos       │
              └────────────────────┘
                       │
        ┌──────────────┼──────────────┬────────────────┐
        ▼              ▼              ▼                ▼
  ┌──────────┐  ┌──────────────┐ ┌────────────┐ ┌──────────────┐
  │carruseles│  │calendario_   │ │antes_      │ │mejora_       │
  │  .py     │  │editorial.py   │ │despues.py  │ │fotos.py      │
  │ 11 tipos │  │semanal + ICS  │ │3 modos     │ │5 looks       │
  └──────────┘  └──────────────┘ └────────────┘ └──────────────┘
        │
        ▼
  ┌─────────────────┐  ┌──────────────────┐
  │  studio.py       │  │  preview_html.py │
  │  CLI + pipeline  │──┤  self-contained  │
  │  7 subcomandos   │  └──────────────────┘
  └─────────────────┘
        │
        ▼
  ┌──────────────────────────────────────────┐
  │     image_generator.py                   │
  │  StubImageGenerator o FooocusImageGen   │
  └──────────────────────────────────────────┘
        │
        ▼
  ┌──────────────────────────────────────────┐
  │  instagram_auth.py                       │
  │  instagram_publisher.py                  │
  │  cloudinary_upload.py                    │
  │  (opcional, solo si publicas en IG)      │
  └──────────────────────────────────────────┘
                       │
                       ▼
                  Instagram Graph API
```

## Los 11 modulos en detalle

| Archivo | Responsabilidad | LOC |
|---|---|---|
| `realestate_studio.py` | Orquestador: verticales lotes + construccion + factory de captions | ~1300 |
| `carruseles.py` | Genera 11 tipos de carruseles + story + reel | ~900 |
| `calendario_editorial.py` | Planificacion semanal + ICS + CSV + fechas clave AR | ~700 |
| `antes_despues.py` | Flujo 3 modos para mostrar progreso de obras | ~600 |
| `mejora_fotos.py` | 5 looks de mejora con Pillow | ~350 |
| `validators.py` | Validacion centralizada (caption, hashtags, municipio, ha) | ~300 |
| `image_generator.py` | Stub + cliente Fooocus real con gradio-client | ~400 |
| `preview_html.py` | Preview HTML self-contained de carruseles y posts | ~350 |
| `caption_variants.py` | A/B testing: N variantes de caption para el mismo post | ~250 |
| `historial_publicaciones.py` | Persistencia + rotacion inteligente de proyectos | ~250 |
| `studio.py` | Pipeline end-to-end + CLI argparse (7 subcomandos) | ~800 |
| `instagram_auth.py` + `instagram_publisher.py` + `cloudinary_upload.py` | Publicacion IG con 3 modos (DRY/INTERACTIVO/REAL) | ~700 |

## Flujo end-to-end: del lote al post publicado

```
1. usuario: "Quiero publicar Chacra 5 ha en Cañuelas"
        |
        ▼
2. VerticalLotes.chacra_pampeana(hectareas=5, municipio="Cañuelas")
        |
        ▼ (devuelve GenerationRequest con prompt SDXL)
3. usuario copia el prompt en Fooocus o Midjourney
        |
        ▼ (imagen generada)
4. usuario: "Dame un post de venta"
        |
        ▼
5. CaptionFactory.post_lote_venta(tema="...", municipio="Cañuelas", ...)
        |
        ▼ (devuelve dict con caption_completo + hashtags)
6. usuario decide: post simple o carrusel?
        |
        ├──> CarruselFactory.lote_premium(...) → 6 slides con prompts
        |
        ▼
7. studio.py: pipeline_semana(...) → genera calendario + carruseles
        |
        ▼
8. preview_html.py → preview para revisar antes de generar
        |
        ▼
9. usuario aprueba
        |
        ▼
10. instagram_publisher.publicar_carrusel(...) → modo DRY_RUN muestra preview
        |
        ▼
11. modo REAL → sube a IG (vía Cloudinary → Graph API)
```

## Capa de datos

```
prompts_inmobiliarios.json
├── plantillas_base (43 prompts SDXL)
├── negativos_default (string)
├── extras_utiles (epoca, momento_dia, clima, vegetacion, estilo_lote, ...)
├── municipios_amba (lista por region)
└── distancias_caba_referencia

captions_instagram.json
├── plantillas (24 tipos de post con tonos)
├── hashtags_por_nicho (17 nichos con 10 hashtags cada uno)
└── hashtags_zona_template (template por municipio)
```

## Dependencias externas

```
Opcionales pero utiles:
  Fooocus local (http://127.0.0.1:7865)
    - Genera imagenes reales a partir de los prompts
    - Requiere GPU o Apple Silicon
    - Setup en README_INMOBILIARIO.md

  Meta for Developers
    - Publicacion automatica en Instagram
    - Setup en README_PUBLICACION_IG.md (15-20 min)

  Cloudinary
    - Hosting publico de imagenes (requisito de IG Graph API)
    - 25 GB gratis
```

## Decisiones de diseno

### Por que JSON y no YAML o DB?
- Los JSONs son editables a mano
- Sin dependencias externas para parsear
- Diff-friendly en git
- Cambios atomicos por archivo

### Por que dataclasses y no Pydantic?
- Sin dependencias externas
- Codigo mas simple
- Suficiente para nuestro caso (validacion custom via validators.py)

### Por que subprocess en vez de imports circulares?
- Cada modulo se puede ejecutar standalone (`python3 realestate_studio.py`)
- Tests mas faciles
- CLI separada de la libreria

### Por que un solo repo y no microservicios?
- Es un estudio personal/profesional, no una empresa
- Deploy = clonar y usar
- Sin complejidad operativa innecesaria

## Que sigue

- [03-instalacion.md](03-instalacion.md): setup paso a paso
- [04-casos-de-uso.md](04-casos-de-uso.md): 6 ejemplos practicos
- [05-modulos.md](05-modulos.md): referencia rapida de los 11 modulos