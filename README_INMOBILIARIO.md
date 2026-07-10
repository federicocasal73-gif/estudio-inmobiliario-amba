# Estudio Inmobiliario AMBA — Fooocus + opencode

Sistema completo para crear contenido de Instagram enfocado en lotes, chacras,
campos, countries y servicios de construcción en la Zona Metropolitana de
Buenos Aires. Orquesta generación de imágenes con Fooocus + IA externa, copy
rioplatense, antes/después, calendarios editoriales y publicación automática.

## Inicio rápido

**¿Primera vez?** Empezá por `WORKFLOW_PRIMER_POST.md` — te lleva paso a paso
desde cero hasta tu primer post publicado en Instagram.

**¿Ya conocés el estudio?** Andá directo a `CHEATSHEET.md` con los 12 comandos
más usados.

**¿Algo no funciona?** Mirá `TROUBLESHOOTING.md` con los 15 errores comunes.

```bash
python3 realestate_studio.py           # demo del estudio
python3 generar_proyecto_ejemplo.py    # proyecto "Chacra 5 ha Cañuelas"
python3 generar_carruseles_ejemplo.py  # 4 carruseles de ejemplo
python3 antes_despues.py               # demo antes/después
python3 calendario_editorial.py        # calendario semana 1
python3 mejora_fotos.py                # mejora de fotos (crea imagen de prueba)
python3 studio.py                      # pipeline end-to-end dry-run

# CLI unificado (7 subcomandos):
python3 studio.py demo
python3 studio.py semana --n 1 --proyectos chacra-canuelas-5ha --publicar dry-run
python3 studio.py duplicar --origen X --destino Y --hectareas 8 --municipio Mercedes
python3 studio.py publicar --carrusel path/carrusel.json --modo dry-run
python3 studio.py preview --carrusel path/carrusel.json
python3 studio.py generar --carrusel path/carrusel.json
python3 studio.py listar
```

## Módulos del estudio

| Archivo | Función |
|---|---|
| `realestate_studio.py` | Orquestador principal: verticales lotes/construcción + posts |
| `carruseles.py` | Carruseles automáticos (4 tipos) con caption narrativo |
| `calendario_editorial.py` | Calendario semanal con fechas clave AR + exportadores |
| `antes_despues.py` | Flujo antes/después en 3 modos (real / ia / mixto) |
| `mejora_fotos.py` | Mejora de fotos con Pillow (5 looks: magazine, golden_hour, etc) |
| `instagram_auth.py` | Auth con Instagram Graph API |
| `instagram_publisher.py` | Publicador de fotos y carruseles (dry-run / interactivo / real) |
| `cloudinary_upload.py` | Upload a Cloudinary (URL pública requerida por IG) |
| `studio.py` | Orquestador end-to-end: pipeline semanal + CLI argparse + duplicar proyecto |
| `validators.py` | Validaciones centralizadas (caption, hashtags, municipio, hectáreas) |
| `image_generator.py` | Stub `StubImageGenerator` + `FooocusImageGenerator` documentado |
| `preview_html.py` | Genera preview HTML self-contained de carruseles y posts |
| `caption_variants.py` | A/B testing: N variantes de caption para un mismo post |
| `historial_publicaciones.py` | Historial + rotación inteligente de proyectos |
| `prompts_inmobiliarios.json` | Vocabulario rural pampeano (ombú, alambrado, molino) |
| `captions_instagram.json` | Captions rioplatenses + hashtags por nicho/municipio |

## Uso típico desde opencode

### 1) Generar un prompt visual

```python
from realestate_studio import RealestateStudio
studio = RealestateStudio()

req = studio.lotes.chacra_pampeana(hectareas=5, municipio="Cañuelas")
print(req.prompt)
```

### 2) Generar un post completo

```python
post = studio.post.post_lote_venta(
    tema="5 ha en Cañuelas",
    municipio="Cañuelas",
    hectareas="5 ha",
    distancia_caba="65 km",
    tono="emotivo",
)
print(post["caption_completo"])
```

### 3) Crear un carrusel

```python
from carruseles import CarruselFactory
factory = CarruselFactory(studio)

carrusel = factory.lote_premium(
    tema="5 ha en Cañuelas",
    municipio="Cañuelas", hectareas=5,
    precio_usd="USD 60.000",
    tono="emotivo", n_slides=6,
)
factory.guardar(carrusel, nombre="mi_carrusel",
                proyecto="chacra-canuelas-5ha")
```

### 4) Antes/después de una obra

```python
from antes_despues import AntesDespuesFactory
ad = AntesDespuesFactory(studio)

resultado = ad.generar(
    foto_antes_path="inmuebles/obras/casa-perez/inputs/semana-01.jpg",
    estilo_casa="casa de campo tradicional",
    hectareas=1, municipio="Escobar",
    cliente="Familia Pérez",
    tiempo_construccion_meses=8,
    modo="ia",     # o "real" si tenes foto del después
)
ad.guardar(resultado)
```

### 5) Mejorar una foto

```python
from mejora_fotos import MejoraFotos
mejora = MejoraFotos()

resultado = mejora.mejorar(
    foto_path="foto.jpg",
    modo="magazine",   # natural | magazine | instagram | golden_hour | pampa
    intensidad="media",
    upscale=2,
)
print(resultado.foto_destino)
```

### 6) Generar calendario semanal

```python
from calendario_editorial import CalendarioEditorial
cal = CalendarioEditorial(studio)

semana = cal.generar_semana(
    semana_n=1,
    proyectos=["chacra-canuelas-5ha", "country-pilar-ejemplo"],
    posts_por_semana=5,
    municipio_principal="Cañuelas",
)
cal.guardar(semana)
cal.exportar_markdown(semana)
cal.exportar_ics(semana)         # importable a Google Calendar
```

### 7) Publicar en Instagram (requiere setup previo)

```python
from instagram_publisher import InstagramPublisher, ModoPublicacion
from instagram_auth import InstagramAuth

publisher = InstagramPublisher(InstagramAuth())

# Dry-run (no publica)
publisher.publicar_foto(
    ruta_imagen="imagen.jpg",
    caption="Mi caption",
    hashtags=["#lotes"],
    modo=ModoPublicacion.DRY_RUN,
)

# Real (publica de verdad)
publisher.publicar_foto(..., modo=ModoPublicacion.REAL)

# Carrusel
publisher.publicar_carrusel(
    rutas_imagenes=["s1.jpg", "s2.jpg", "s3.jpg"],
    caption="...", hashtags=["#lotes"],
    modo=ModoPublicacion.DRY_RUN,
)
```

## Estructura de carpetas

```
Fooocus/
├── realestate_studio.py
├── prompts_inmobiliarios.json
├── captions_instagram.json
├── auth_instagram_example.json      ← plantilla para auth.json
├── README_PUBLICACION_IG.md         ← guía de setup Meta Business + Cloudinary
│
├── inmuebles/
│   ├── lotes/
│   │   └── chacra-canuelas-5ha/
│   │       ├── prompts/
│   │       ├── posts/
│   │       └── carruseles/
│   ├── obras/                       ← antes/después generados
│   ├── servicios/
│   │   └── carruseles/
│   └── calendarios/
│       └── semana_01/
│           ├── plan.json
│           ├── plan.md
│           └── plan.ics
```

## Verticales del estudio

### `studio.lotes` — venta de tierra

| Función | Descripción |
|---|---|
| `chacra_pampeana()` | Chacra residencial 1-5 ha |
| `country_premium()` | Entrada de country con amenities |
| `lote_periurbano()` | Lote baldío periurbano |
| `vista_aerea_loteo()` | Vista drone de loteo |
| `loteo_en_desarrollo()` | Obra de movimiento de suelo |
| `campo_mediano()` | Campo 10-50 ha productivo |
| `amanecer_pampa()` / `atardecer_campo()` | Atmósferas |
| `tranquera_argentina()` / `molino_tanque_australiano()` / `casco_estancia()` | Detalles rurales |

### `studio.construccion` — servicios y obras

| Función | Descripción |
|---|---|
| `movimiento_suelo()` | Maquinaria pesada trabajando |
| `obra_gruesa()` | Hormigón, mampostería |
| `steel_framing()` | Steel frame en proceso |
| `render_proyecto()` | Render arquitectónico |

### `studio.post` — captions + hashtags

| Función | Tonos |
|---|---|
| `post_lote_venta()` | emotivo, practico, inversion, premium |
| `post_country()` | premium, familia, inversion |
| `post_campo()` | inversion, productor |
| `post_preventa()` | oportunidad, urgencia |
| `post_lote_periurbano()` | practico |

### `CarruselFactory` — carruseles automáticos

| Tipo | Slides default | Función |
|---|---|---|
| `lote_premium` | 6 | Portada + aérea + tranquera + molino + render + CTA |
| `country_etapa` | 5 | Portada + masterplan + amenity + obra + CTA |
| `obra_avance` | 4 | Portada + foto real (placeholder) + render + CTA |
| `servicios` | 8 | Portada + 6 servicios + CTA |

### `AntesDespuesFactory` — antes/después

3 modos: `real` (ambas fotos), `ia` (solo antes → prompt + workflow img2img),
`mixto` (antes + sugerencias IA).

### `MejoraFotos` — mejora de fotos

5 looks: `natural`, `magazine`, `instagram`, `golden_hour`, `pampa`.
3 intensidades: `baja`, `media`, `alta`.
Upscale opcional: x1, x2, x3, x4.

### `CalendarioEditorial` — planificación semanal

- 1-7 posts por semana (configurable)
- Distribución por día priorizando engagement
- Detección automática de fechas clave AR (Día de la Madre, Padre,
  Black Friday, Navidad, etc) calculadas dinámicamente
- Posts completos generados por slot (caption + hashtags)
- Exportadores: Markdown + ICS (Google Calendar)

### `InstagramPublisher` — publicación automática

3 modos: `DRY_RUN`, `INTERACTIVO`, `REAL`.
Soporta: fotos individuales, carruseles (2-10 imágenes).
Upload automático a Cloudinary.
Logs de cada publicación.

## Fechas clave argentinas soportadas

Calculadas dinámicamente (Madre y Padre como 3er domingo):

- Enero: Año Nuevo
- Febrero: San Valentín
- Marzo: Día de la Memoria
- Abril: Día del Veterano
- Mayo: Trabajador, Revolución de Mayo
- Junio: Padre (3er dom), Bandera
- Julio: Independencia
- Agosto: Niño
- Septiembre: Maestro
- Octubre: Diversidad Cultural, Madre (3er dom)
- Noviembre: Soberanía, Black Friday
- Diciembre: Inmaculada, Nochebuena, Navidad, Fin de Año, Cyber Monday

## Comandos rápidos desde opencode

- *"Genera preventa country en Pilar con 12 lotes y carrusel de 5 slides"*
- *"Carrusel emotivo para familia que construyó en Cañuelas"*
- *"5 captions para campo de 50 ha en Brandsen"*
- *"Antes/después modo IA de una casa en Escobar de 8 meses de obra"*
- *"Mejorá esta foto con look magazine x2"*
- *"Calendario de 5 posts para esta semana"*
- *"Generá semana 23 con 7 posts incluyendo fechas clave"*

## Setup de Fooocus (cuando lo necesites)

```bash
cd /home/fede/Desktop/Proyecto/Fooocus
pyenv install 3.11.9
pyenv local 3.11.9
python -m venv venv
source venv/bin/activate
export PYTORCH_ENABLE_MPS_FALLBACK=1
python launch.py --disable-offload-from-vram --preset default
```

## Setup de publicación en Instagram

Ver `README_PUBLICACION_IG.md` para instrucciones paso a paso.
Requiere: cuenta IG Business, app Meta Developers, Cloudinary.
Sin este setup, todo funciona en modo `--dry-run`.

## Documentación adicional

- `CHEATSHEET.md` — los 12 comandos más usados para tener siempre a mano
- `TROUBLESHOOTING.md` — 15 errores comunes con causa y fix
- `WORKFLOW_PRIMER_POST.md` — paso a paso guiado desde cero hasta publicar
- `README_PUBLICACION_IG.md` — setup de Meta + Cloudinary
- `readme.md` — documentación original de Fooocus (no modificada)