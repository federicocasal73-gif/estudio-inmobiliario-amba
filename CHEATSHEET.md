# CHEATSHEET — Estudio Inmobiliario AMBA

Los 12 comandos más usados desde opencode. Copiá, pegá, ejecutá.

---

## 1. Generar un prompt visual (para Fooocus / Midjourney / DALL-E)

```python
from realestate_studio import RealestateStudio
studio = RealestateStudio()

# Chacra 5 ha en Cañuelas al atardecer
req = studio.lotes.chacra_pampeana(hectareas=5, municipio="Cañuelas")
print(req.prompt)
print(req.aspect_ratio, req.styles)
```

**Salida esperada**: prompt SDXL en inglés con vocabulario pampeano (ombú,
alambrado, golden hour, 8k, real estate photography).

---

## 2. Generar un post de venta completo (caption + hashtags)

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

**Tonos disponibles**: `emotivo`, `inversion`, `practico`, `premium`.

---

## 3. Crear un carrusel (4 tipos disponibles)

```python
from carruseles import CarruselFactory
factory = CarruselFactory(studio)

carrusel = factory.lote_premium(
    tema="5 ha en Cañuelas",
    municipio="Cañuelas",
    hectareas=5,
    precio_usd="USD 60.000",
    n_slides=6,
)
factory.guardar(carrusel, "mi_carrusel", proyecto="chacra-canuelas-5ha")
```

**Tipos**: `lote_premium`, `country_etapa`, `obra_avance`, `servicios`.
Cambiá `n_slides` para más/menos slides.

---

## 4. Antes/después de una obra

```python
from antes_despues import AntesDespuesFactory
ad = AntesDespuesFactory(studio)

resultado = ad.generar(
    foto_antes_path="ruta/a/foto_antes.jpg",
    estilo_casa="casa de campo tradicional con galería",
    hectareas=1,
    municipio="Escobar",
    cliente="Familia Pérez",
    tiempo_construccion_meses=8,
    modo="ia",  # o "real" si tenés foto del después
)
ad.guardar(resultado)
```

**Modos**: `real` (ambas fotos), `ia` (solo antes → prompt + workflow), `mixto`.

---

## 5. Mejorar una foto

```python
from mejora_fotos import MejoraFotos
mejora = MejoraFotos()

resultado = mejora.mejorar(
    foto_path="ruta/a/foto.jpg",
    modo="magazine",          # natural | magazine | instagram | golden_hour | pampa
    intensidad="media",       # baja | media | alta
    upscale=2,                # 1, 2, 3, 4
)
print(resultado.foto_destino)
```

---

## 6. Generar calendario semanal

```python
from calendario_editorial import CalendarioEditorial
cal = CalendarioEditorial(studio)

semana = cal.generar_semana(
    semana_n=1,
    proyectos=["chacra-canuelas-5ha"],
    posts_por_semana=5,
    municipio_principal="Cañuelas",
)
cal.guardar(semana)
cal.exportar_markdown(semana)      # tabla Markdown
cal.exportar_ics(semana)          # importable a Google Calendar
```

---

## 7. Pipeline completo de una semana (dry-run)

```python
from studio import Studio
from instagram_publisher import ModoPublicacion

studio = Studio()
resultado = studio.pipeline_semana(
    semana_n=1,
    proyectos=["chacra-canuelas-5ha"],
    posts_por_semana=5,
    municipio_principal="Cañuelas",
    modo_publicacion=ModoPublicacion.DRY_RUN,  # NO publica
)
print(resultado.resumen)
studio.guardar_pipeline(resultado)
```

---

## 8. Publicar una foto (dry-run por defecto)

```python
from instagram_publisher import InstagramPublisher, ModoPublicacion
from instagram_auth import InstagramAuth

publisher = InstagramPublisher(InstagramAuth())
resultado = publisher.publicar_foto(
    ruta_imagen="imagen.jpg",
    caption="Mi caption",
    hashtags=["#lotes", "#chacras"],
    modo=ModoPublicacion.DRY_RUN,
)
print(resultado.to_dict())
```

**Modos**: `DRY_RUN` (default), `INTERACTIVO` (pide confirmación), `REAL` (publica).

---

## 9. Publicar un carrusel

```python
resultado = publisher.publicar_carrusel(
    rutas_imagenes=["s1.jpg", "s2.jpg", "s3.jpg"],
    caption="...",
    hashtags=["#lotes"],
    modo=ModoPublicacion.DRY_RUN,
)
```

---

## 10. Verificar setup de Meta + Cloudinary

```bash
python3 instagram_auth.py
```

**Salida esperada**:
```
✓ Token válido
✓ Permisos OK
✓ Cuenta: @tu_cuenta (XXX seguidores)
```

Si falta algo, seguí `README_PUBLICACION_IG.md`.

---

## 11. Demo rápida (corre los ejemplos sin tocar nada)

```bash
python3 realestate_studio.py            # demo del estudio
python3 generar_proyecto_ejemplo.py     # proyecto Cañuelas completo
python3 generar_carruseles_ejemplo.py   # 4 carruseles
python3 antes_despues.py                # antes/después modo IA
python3 calendario_editorial.py         # calendario semana actual
python3 mejora_fotos.py                 # crea imagen de prueba + mejora
python3 studio.py                       # pipeline end-to-end dry-run
```

---

## 12. Listar proyectos disponibles

```bash
ls inmuebles/lotes/
python3 studio.py listar
```

---

## 13. Duplicar proyecto (variantes rápidas)

```python
from studio import Studio
studio = Studio()

# Crea chacra-canuelas-8ha clonando chacra-canuelas-5ha
# con 8 ha en lugar de 5 y municipio Mercedes en vez de Cañuelas
studio.duplicar_proyecto(
    origen="chacra-canuelas-5ha",
    destino="chacra-canuelas-8ha",
    cambios={"hectareas": 8, "municipio": "Mercedes"},
)
```

O por CLI:
```bash
python3 studio.py duplicar --origen chacra-canuelas-5ha \
    --destino chacra-canuelas-8ha --hectareas 8 --municipio Mercedes
```

---

## 14. A/B testing de captions

```python
from realestate_studio import RealestateStudio
from caption_variants import CaptionVariants

studio = RealestateStudio()
cv = CaptionVariants(studio)
variantes = cv.generar(
    tipo="lote_venta", n=3,
    tema="5 ha en Cañuelas", municipio="Cañuelas",
    hectareas="5 ha", distancia_caba="65 km",
    tonos=["emotivo", "inversion", "premium"],
)
# Mejor por tono preferido
mejor = cv.mejor_caption_para_publicar(
    variantes, criterios={"tono_preferido": ["emotivo", "inversion"]})
print(mejor.caption_completo)
```

---

## 15. Story + Reel de Instagram

```python
from realestate_studio import RealestateStudio
from carruseles import CarruselFactory

studio = RealestateStudio()
factory = CarruselFactory(studio)

# Story (9:16, varios slides)
story = factory.story(tema="5 ha en Cañuelas", municipio="Cañuelas")

# Reel (9:16, 1 slide con caption corto)
reel = factory.reel(tema="5 ha en Cañuelas", municipio="Cañuelas")
```

---

## 16. Preview HTML antes de generar imágenes

```bash
python3 studio.py preview \
    --carrusel inmuebles/lotes/chacra-canuelas-5ha/carruseles/lote_premium/carrusel.json
```

Abre el HTML generado con doble-click en el navegador.

---

## 17. Validar un post antes de publicar

```python
from validators import validate_post
resultado = validate_post(
    caption="Mi caption...",
    hashtags=["#lotes", "#chacras"],
    municipio="Cañuelas",
    hectareas=5,
    hashtags_blacklist=["inversion"],
    hashtags_must_include=["#patrimonio"],
)
if not resultado.ok:
    print("Errores:", resultado.errores)
print("Warnings:", resultado.advertencias)
```

Cada carpeta es un proyecto con `prompts/`, `posts/`, `carruseles/`.

---

## Frases mágicas para opencode

Cuando me pidas algo, estas frases activan flujos completos:

- *"Generá preventa country en Pilar con 12 lotes"* → carrusel `country_etapa`
- *"5 captions para campo de 50 ha en Brandsen"* → 5 captions con tonos distintos
- *"Mejorá esta foto con look magazine x2"* → `mejora_fotos.mejorar(...)`
- *"Calendario de 5 posts para esta semana"* → `calendario_editorial.generar_semana(...)`
- *"Pipeline completo semana 23 dry-run"* → `studio.pipeline_semana(...)`
- *"Antes/después modo IA de una casa en Escobar de 8 meses"* → `antes_despues.generar(...)`
- *"Carrusel emotivo para familia que construyó en Cañuelas"* → `carruseles.lote_premium(tono="emotivo")`

---

## Atajos de teclado opencode

- `Ctrl+I` → invocar inline (copia esto a un archivo `.py` y ejecutalo)
- Type `/` → ver comandos rápidos

---

## Próximo paso si tenés que publicar

1. `python3 instagram_auth.py` → verificar setup
2. Si todo OK: cambiar `ModoPublicacion.DRY_RUN` por `ModoPublicacion.REAL` en cualquier script
3. Si falla: ver `TROUBLESHOOTING.md`

---

## Ver también

- `README_INMOBILIARIO.md` — referencia completa del estudio
- `README_PUBLICACION_IG.md` — setup de Meta + Cloudinary
- `WORKFLOW_PRIMER_POST.md` — paso a paso del primer post
- `TROUBLESHOOTING.md` — 15 errores comunes con fix