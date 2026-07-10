# 05 - Referencia de los 11 modulos

Para cada modulo: que hace, cuando usarlo, ejemplo minimo, errores comunes.

---

## 1. `realestate_studio.py` (orquestador principal)

**Que hace**: punto de entrada del estudio. Contiene las clases `VerticalLotes`
(17 funciones para generar prompts rurales), `VerticalConstruccion` (28
funciones para prompts de obra) y `CaptionFactory` (23 metodos `post_*` para
generar captions completos). Carga los JSONs de datos al inicio.

**Cuando usarlo**: SIEMPRE. Es el corazon del estudio.

**Ejemplo minimo**:
```python
from realestate_studio import RealestateStudio
s = RealestateStudio()
print(s.post.post_lote_venta(tema="5 ha", municipio="Cañuelas", ...)["caption"])
```

**Errores comunes**: no lee JSONs si la primera linea falla. Pasa si el JSON
esta corrupto; restaurar el archivo original.

---

## 2. `carruseles.py`

**Que hace**: genera 11 tipos de carruseles (lote_premium, country_etapa,
obra_avance, etapas_construccion, steel_frame_completo, llave_en_mano_completo,
terminaciones_detalle, obra_completa, servicios, story, reel). Cada uno con
caption narrativo, prompts por slide y persistencia a disco.

**Cuando usarlo**: cuando queres contenido multi-slide para IG.

**Ejemplo minimo**:
```python
from realestate_studio import RealestateStudio
from carruseles import CarruselFactory
s = RealestateStudio()
f = CarruselFactory(s)
c = f.lote_premium(tema="5 ha en Cañuelas", municipio="Cañuelas", hectareas=5)
f.guardar(c, "mi_carrusel", proyecto="chacra-canuelas-5ha")
```

**Errores comunes**: si `proyecto=None`, intenta guardar en `_generados/`.
Es mejor siempre pasar un `proyecto`.

---

## 3. `calendario_editorial.py`

**Que hace**: genera un plan semanal (5 slots por defecto) con posts
completos por slot. Detecta fechas clave argentinas (Madre, Padre, Black
Friday, Navidad, etc) y las incluye automaticamente. Exporta a Markdown,
ICS (Google Calendar), JSON y CSV.

**Cuando usarlo**: cada lunes para planificar la semana.

**Ejemplo minimo**:
```python
from realestate_studio import RealestateStudio
from calendario_editorial import CalendarioEditorial
s = RealestateStudio()
cal = CalendarioEditorial(s)
semana = cal.generar_semana(semana_n=1, posts_por_semana=5)
cal.exportar_markdown(semana)
cal.exportar_ics(semana)
```

**Errores comunes**: si la fecha_inicio no es lunes, las fechas del calendario
se corren. Usar siempre lunes como inicio.

---

## 4. `antes_despues.py`

**Que hace**: genera contenido de progreso de obra en 3 modos: **real**
(tu foto del antes y el despues), **ia** (solo tu foto del antes + workflow
para img2img), **mixto** (combinacion).

**Cuando usarlo**: para mostrar el progreso de una obra a tu audiencia.

**Ejemplo minimo**:
```python
from realestate_studio import RealestateStudio
from antes_despues import AntesDespuesFactory
s = RealestateStudio()
ad = AntesDespuesFactory(s)
resultado = ad.generar(
    foto_antes_path="mis_fotos/antes.jpg",
    modo="ia",
    estilo_casa="casa de campo tradicional",
    hectareas=1,
    municipio="Escobar",
    cliente="Familia Perez",
    tiempo_construccion_meses=8,
)
ad.guardar(resultado)
```

**Errores comunes**: la foto debe existir; si no, falla. Verificar path
antes de llamar.

---

## 5. `mejora_fotos.py`

**Que hace**: aplica 5 looks (natural, magazine, instagram, golden_hour,
pampa) a fotos existentes con Pillow. Tambien permite upscale x2/x3/x4.

**Cuando usarlo**: para mejorar fotos reales antes de publicar.

**Ejemplo minimo**:
```python
from mejora_fotos import MejoraFotos
m = MejoraFotos()
r = m.mejorar("foto.jpg", modo="magazine", intensidad="media", upscale=2)
print(r.foto_destino)
```

**Errores comunes**: intensidad "alta" puede saturar fotos ya brillantes.
Probar primero con "baja" si la foto ya tiene buena exposure.

---

## 6. `validators.py`

**Que hace**: validaciones centralizadas para no publicar posts rotos.
Chequea: caption <= 2200 chars, hashtags <= 30, municipio conocido, hectareas > 0.

**Cuando usarlo**: antes de publicar en IG, o dentro del pipeline automatico.

**Ejemplo minimo**:
```python
from validators import validate_post
resultado = validate_post(
    caption="Mi caption",
    hashtags=["#lotes", "#chacras"],
    municipio="Cañuelas",
    hectareas=5,
)
if not resultado.ok:
    print("Errores:", resultado.errores)
```

**Errores comunes**: pasa por alto validaciones si llamas directo a los
metodos `post_*` sin validar. Mejor usar `safe_post(post)` que lo hace auto.

---

## 7. `image_generator.py`

**Que hace**: interfaz abstracta `ImageGenerator` con dos implementaciones:
`StubImageGenerator` (no genera, devuelve instrucciones) y
`FooocusImageGenerator` (usa `gradio-client` para conectar con Fooocus real).
La factory `get_generator()` devuelve el apropiado automaticamente.

**Cuando usarlo**: cuando quieras generar las imagenes reales (no solo los
prompts).

**Ejemplo minimo**:
```python
from image_generator import get_generator
from pathlib import Path
gen = get_generator()  # devuelve FooocusImageGenerator si esta activo
r = gen.generar(
    prompt="5 hectares pampas farm, golden hour",
    output_path=Path("imagen.jpg"),
)
print(r.output_path)  # path a la imagen generada
```

**Errores comunes**: requiere `pip install gradio-client` y Fooocus corriendo
en `http://127.0.0.1:7865`. Si no, cae automaticamente al stub.

---

## 8. `preview_html.py`

**Que hace**: genera HTML self-contained (sin dependencias externas) de un
carrusel o un post. Permite ver como quedaria visualmente sin generar las
imagenes.

**Cuando usarlo**: para validar concepto de un carrusel antes de gastar
tokens en generar las 6 imagenes.

**Ejemplo minimo**:
```python
from preview_html import PreviewHTML
from realestate_studio import RealestateStudio
from carruseles import CarruselFactory
s = RealestateStudio()
f = CarruselFactory(s)
c = f.lote_premium(tema="5 ha en Cañuelas", municipio="Cañuelas", hectareas=5)
preview = PreviewHTML()
preview.carrusel(c, ruta_salida="preview.html")
```

**Errores comunes**: el HTML usa colores placeholder, no imagenes reales.
Para ver el carrusel con imagenes, primero generar y reemplazar.

---

## 9. `caption_variants.py`

**Que hace**: genera N variantes del mismo caption para A/B testing. Permite
elegir la "mejor" segun criterios configurables (tono preferido, longitud,
nicho).

**Cuando usarlo**: cuando queres probar diferentes angulos del mismo post
y ver cual funciona mejor con tu audiencia.

**Ejemplo minimo**:
```python
from realestate_studio import RealestateStudio
from caption_variants import CaptionVariants
s = RealestateStudio()
cv = CaptionVariants(s)
variantes = cv.generar(
    tipo="lote_venta", n=3,
    tema="5 ha en Cañuelas", municipio="Cañuelas",
    hectareas="5 ha", distancia_caba="65 km",
    tonos=["emotivo", "inversion", "premium"],
)
cv.guardar(variantes, "variantes_demo", proyecto="chacra-canuelas-5ha")
```

**Errores comunes**: `must_include` en el factory `hashtags(blacklist=,
must_include=)` se respeta pero algunos tipos de caption ya tienen placeholders
que el formatter completa; no hay problema.

---

## 10. `historial_publicaciones.py`

**Que hace**: persiste un JSON (`_historial_publicaciones.json`) con todas
las publicaciones hechas. `RotadorProyectos` decide que proyecto publicar
segun la ultima vez que se uso.

**Cuando usarlo**: cuando tenes varios proyectos y queres que Instagram no
vea siempre el mismo.

**Ejemplo minimo**:
```python
from historial_publicaciones import HistorialPublicaciones, RotadorProyectos
h = HistorialPublicaciones()
r = RotadorProyectos(h)
orden = r.ordenar_por_antiguedad(["A", "B", "C"])
# Resultado: proyectos menos recientes primero
```

**Errores comunes**: si nunca se publico nada, todos los proyectos tienen
`dias=None` y se ordenan alfabeticamente. Publicar al menos una vez antes
de esperar rotacion inteligente.

---

## 11. `studio.py` (orquestador end-to-end + CLI)

**Que hace**: el modulo "fachada". Coordina todos los anteriores en un pipeline
semanal + expone un CLI argparse con 7 subcomandos.

**Cuando usarlo**: como punto de entrada para el workflow completo. Tambien
tiene metodos `duplicar_proyecto`, `regenerar_carruseles`, `publicar_carrusel_existente`.

**Ejemplo minimo** (como modulo):
```python
from studio import Studio
s = Studio()
resultado = s.pipeline_semana(
    semana_n=1, proyectos=["chacra-canuelas-5ha"],
    posts_por_semana=5, municipio_principal="Cañuelas",
)
print(resultado.resumen)
```

**Como CLI**:
```bash
python3 studio.py demo
python3 studio.py semana --n 1 --proyectos chacra-canuelas-5ha --publicar dry-run
python3 studio.py duplicar --origen X --destino Y --hectareas 8
python3 studio.py publicar --carrusel path/carrusel.json
python3 studio.py preview --carrusel path/carrusel.json
python3 studio.py generar --carrusel path/carrusel.json
python3 studio.py listar
```

**Errores comunes**: el CLI espera paths relativos desde donde lo ejecutes.
Mejor correr desde la raiz del repo.

---

## Modulos de publicacion (3 archivos)

### `instagram_auth.py`
**Que hace**: wrapper para leer `auth.json`, validar que el token sirve,
pedir info de la cuenta. Lee tambien la seccion cloudinary del mismo JSON.

### `instagram_publisher.py`
**Que hace**: 3 modos de publicacion. `DRY_RUN` (default, no publica),
`INTERACTIVO` (pide confirmacion), `REAL` (publica de verdad). Soporta fotos
y carruseles (2-10 imagenes).

### `cloudinary_upload.py`
**Que hace**: sube imagenes a Cloudinary porque la API de IG requiere URLs
publicas. Sin esto, no se puede publicar nada en IG.

**Errores comunes**: los 3 modulos son opcionales. Si no tenes Meta + Cloudinary
configurados, todo el estudio funciona en DRY_RUN.

---

## Que sigue

- [06-comandos-cli.md](06-comandos-cli.md): CLI completo con todos los subcomandos
- [07-flujos-end-to-end.md](07-flujos-end-to-end.md): pipelines automaticos
- [08-publicacion-instagram.md](08-publicacion-instagram.md): setup Meta + Cloudinary