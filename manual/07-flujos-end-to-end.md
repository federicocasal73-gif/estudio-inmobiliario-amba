# 07 - Flujos end-to-end

Los pipelines automaticos mas utiles del estudio. Cada flujo muestra:
- **Que resuelve**: que caso de uso cubre
- **Codigo**: copy-paste directo
- **Output**: que archivos se generan
- **Variaciones**: como adaptarlo

---

## Flujo 1: Pipeline semanal completo (el mas usado)

**Que resuelve**: en una sola llamada, planificar toda la semana de contenido
para 1+ proyectos, generar carruseles faltantes, validar posts, y dejar
todo listo para publicar.

**Codigo**:
```python
from studio import Studio
from instagram_publisher import ModoPublicacion

studio = Studio()
resultado = studio.pipeline_semana(
    semana_n=1,                              # esta semana
    proyectos=["chacra-canuelas-5ha"],        # proyectos a rotar
    posts_por_semana=5,                       # 5 posts esta semana
    municipio_principal="Cañuelas",
    modo_publicacion=ModoPublicacion.DRY_RUN, # no publica
    generar_carruseles_faltantes=True,
    validar_posts=True,
)

print(resultado.resumen)
```

**Output esperado**:
```
Semana 1 (2026-07-06 → 2026-07-12): 5 slots, 2 carruseles generados, 0/5 publicaciones OK
```

**Archivos generados**:
- `inmuebles/calendarios/semana_01/plan.md` - tabla legible
- `inmuebles/calendarios/semana_01/plan.json` - datos completos
- `inmuebles/calendarios/semana_01/plan.ics` - Google Calendar
- `inmuebles/calendarios/semana_01/plan.csv` - Excel
- `inmuebles/lotes/chacra-canuelas-5ha/carruseles/...` - carruseles nuevos
- `inmuebles/pipelines/pipeline_semana_01_*.json` - reporte completo con
  validaciones, publicaciones, errores

**Variaciones**:
- Cambiar `posts_por_semana=7` para mas posts
- Cambiar `proyectos=[...]` para incluir mas
- Pasar `fecha_inicio="2026-12-15"` para semana especifica

---

## Flujo 2: Generar imagenes reales para todos los carruseles de una semana

**Que resuelve**: tener las imagenes reales (no solo prompts) listas para
publicar. Requiere Fooocus corriendo.

**Pre-condiciones**: Fooocus activo en `http://127.0.0.1:7865` y
`gradio-client` instalado.

**Codigo**:
```python
from studio import Studio

studio = Studio()

# 1. Generar la semana completa
resultado = studio.pipeline_semana(
    semana_n=1,
    proyectos=["chacra-canuelas-5ha"],
    posts_por_semana=3,
    municipio_principal="Cañuelas",
    modo_publicacion=studio.image_generator.__class__.__name__ != "StubImageGenerator",
)

# 2. Para cada carrusel generado, enviar prompts a Fooocus
reporte = studio.generar_imagenes_pipeline(resultado)
print(f"Carruseles procesados: {len(reporte['carruseles'])}")
```

**Output esperado** (con Fooocus activo):
- Imagenes `.jpg` en cada carpeta `slides/` de los carruseles
- Reporte con metadata de cada generacion

**Sin Fooocus**: cae al stub, los prompts quedan guardados como `.prompt.json`
para que los pegues manualmente.

---

## Flujo 3: Publicar un carrusel especifico

**Que resuelve**: subir a IG un carrusel que ya tenes generado y con imagenes
listas.

**Pre-condiciones**: `auth.json` configurado, imagenes en `slides/`.

**Codigo** (sin publicacion real, para verificar):
```python
from studio import Studio
from instagram_publisher import ModoPublicacion

studio = Studio()
resultado = studio.publicar_carrusel_existente(
    "inmuebles/lotes/chacra-canuelas-5ha/carruseles/lote_premium/carrusel.json",
    modo=ModoPublicacion.DRY_RUN,
)
print(f"Exito: {resultado.exito}")
print(f"Imagenes encontradas: {resultado.n_imagenes}")
if resultado.error:
    print(f"Error: {resultado.error}")
```

**Codigo** (publicar de verdad):
```python
# Cambiar modo a REAL solo cuando estes seguro
resultado = studio.publicar_carrusel_existente(
    "inmuebles/lotes/chacra-canuelas-5ha/carruseles/lote_premium/carrusel.json",
    modo=ModoPublicacion.REAL,
)
print(f"IG Post ID: {resultado.instagram_post_id}")
print(f"Permalink: {resultado.permalink}")
```

**Output esperado** (DRY_RUN, sin imagenes):
```
Exito: False
Imagenes encontradas: 0
Error: Necesita >= 2 imagenes (encontradas: 0)
```

**Output esperado** (REAL, con imagenes y auth OK):
```
Exito: True
IG Post ID: 17912345678901234
Permalink: https://www.instagram.com/p/CxYz...
```

---

## Flujo 4: Regenerar carruseles de una semana ya planificada

**Que resuelve**: si no te gustaron los prompts de los carruseles generados
la primera vez, regenerarlos con la misma distribucion.

**Codigo**:
```python
from studio import Studio

studio = Studio()
resultado = studio.regenerar_carruseles(
    semana_n=1,
    proyectos=["chacra-canuelas-5ha"],
    posts_por_semana=3,
    municipio_principal="Cañuelas",
)
print(resultado.resumen)
```

**Output esperado**:
```
Semana 1 (...): 3 slots, 3 carruseles regenerados, 0/3 publicaciones OK
```

---

## Flujo 5: Duplicar proyecto con cambios

**Que resuelve**: crear una variante rapida de un proyecto (otra hectarea,
otra ubicacion).

**Codigo**:
```python
from studio import Studio

studio = Studio()
carpeta = studio.duplicar_proyecto(
    origen="chacra-canuelas-5ha",
    destino="chacra-mercedes-3ha",
    cambios={"hectareas": 3, "municipio": "Mercedes"},
)
print(f"Proyecto duplicado en: {carpeta}")
```

**Output esperado**:
```
Proyecto duplicado en: /home/.../inmuebles/lotes/chacra-mercedes-3ha
```

**Output de archivos**: nueva carpeta con prompts actualizados pero el resto
del contenido (posts, captions) copiado tal cual.

**Limitacion**: solo actualiza los prompts SDXL (los `prompt` strings). Los
archivos JSON con captions/hashtags no se modifican; solo se copian.

---

## Flujo 6: Validar un post antes de publicar

**Que resuelve**: chequear que un post cumple los limites de IG antes de
intentar publicarlo.

**Codigo**:
```python
from validators import validate_post

resultado = validate_post(
    caption="Mi caption largo...",
    hashtags=["#lotes", "#chacras", "#campo", "#inversion"],
    municipio="Cañuelas",
    hectareas=5,
    hashtags_blacklist=["inversion"],          # excluir
    hashtags_must_include=["#patrimonio"],     # forzar inclusion
)

if not resultado.ok:
    print("Errores:", resultado.errores)
print("Warnings:", resultado.advertencias)
print("Metadata:", resultado.metadata)
```

**Output esperado**:
```
Errores: ['hashtags en blacklist: ["#inversion"]']
Warnings: []
```

---

## Flujo 7: Mejorar una foto y publicar

**Que resuelve**: tomar una foto real (de celular, dron, etc), mejorarla
visualmente, y dejarla lista para IG.

**Codigo**:
```python
from mejora_fotos import MejoraFotos

mejora = MejoraFotos()
resultado = mejora.mejorar(
    foto_path="mis_fotos/lote_original.jpg",
    modo="magazine",        # natural, magazine, instagram, golden_hour, pampa
    intensidad="media",     # baja, media, alta
    upscale=2,               # 1, 2, 3, 4
)
print(f"Foto mejorada en: {resultado.foto_destino}")
print(f"Transformaciones aplicadas: {resultado.transformaciones}")
```

**Output esperado**:
```
Foto mejorada en: mis_fotos/lote_original/mejoras/lote_original_magazine_x2.jpg
Transformaciones aplicadas: ['look:magazine ...', 'unsharp_mask_final', 'upscale_x2']
```

---

## Flujo 8: A/B testing con multiples captions

**Que resuelve**: probar 3 versiones del mismo post y publicar el que mejor
funcione.

**Codigo**:
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

# Imprimir y guardar
for v in variantes:
    print(f"--- {v.variante_id} ({v.tono}) ---")
    print(v.caption_completo[:200])

cv.guardar(variantes, "variantes_demo", proyecto="chacra-canuelas-5ha")
```

**Output esperado**:
- 3 variantes impresas
- `inmuebles/lotes/chacra-canuelas-5ha/variantes/variantes_demo.txt` con las
  3 lado a lado

---

## Combinacion recomendada: lunes completo

```bash
# 1. Planificar la semana
python3 studio.py semana --n 1 --proyectos chacra-canuelas-5ha --publicar dry-run

# 2. Revisar el plan
cat inmuebles/calendarios/semana_01/plan.md

# 3. Generar imagenes (si Fooocus esta activo)
python3 studio.py generar --carrusel inmuebles/.../lote_premium/carrusel.json

# 4. Publicar (cambiar --modo a real solo cuando estes seguro)
python3 studio.py publicar --carrusel path/carrusel.json --modo real
```

---

## Que sigue

- [08-publicacion-instagram.md](08-publicacion-instagram.md): setup Meta + Cloudinary
- [09-limitaciones-y-workarounds.md](09-limitaciones-y-workarounds.md): 15 limitaciones conocidas
- [10-personalizacion.md](10-personalizacion.md): como agregar tus propios templates