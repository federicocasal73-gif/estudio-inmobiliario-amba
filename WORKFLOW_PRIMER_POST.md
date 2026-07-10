# WORKFLOW — Tu primer post de Instagram con el estudio

Escenario: querés publicar tu primer carrusel sobre una **chacra de 5 ha en Cañuelas**.
Tiempo total estimado: **30-45 minutos** (la mayoría es setup de Meta si es la primera vez).

---

## Antes de empezar

Tenés que tener:
- Python 3.10+ instalado
- Pillow instalado (`pip install pillow`)
- Una idea clara del proyecto que querés publicar

---

## Paso 1 — Probar que el estudio funciona (2 minutos)

Desde la raíz del proyecto:

```bash
python3 realestate_studio.py
```

**Salida esperada**: ves un prompt generado + un caption + hashtags.
Si ves eso, todo el estudio está OK.

Si falla, mirá `TROUBLESHOOTING.md` sección 1 (Pillow) o 11 (Python).

---

## Paso 2 — Definir el proyecto (5 minutos)

Crear la carpeta del proyecto:

```bash
mkdir -p inmuebles/lotes/chacra-canuelas-5ha/{prompts,posts,carruseles}
```

Anotar los datos clave del proyecto (los vas a usar todo el tiempo):
- **Municipio**: Cañuelas (Buenos Aires)
- **Hectáreas**: 5
- **Distancia a CABA**: 65 km
- **Precio referencial**: USD 60.000
- **Servicios**: luz eléctrica, alambrado perimetral, tranquera, molino

---

## Paso 3 — Generar los prompts visuales (5 minutos)

```python
from realestate_studio import RealestateStudio
studio = RealestateStudio()

proyecto = "chacra-canuelas-5ha"
municipio = "Cañuelas"
hectareas = 5

# 1. Vista principal (portada)
req = studio.lotes.chacra_pampeana(
    hectareas=hectareas, municipio=municipio, momento="atardecer")
studio.guardar_prompt(req, "01_portada_atardecer",
                      subcarpeta=f"lotes/{proyecto}/prompts")

# 2. Vista aerea drone
req = studio.lotes.vista_aerea_loteo(n_lotes=20, municipio=municipio)
studio.guardar_prompt(req, "02_vista_aerea",
                      subcarpeta=f"lotes/{proyecto}/prompts")

# 3. Amanecer
req = studio.lotes.amanecer_pampa(municipio=municipio)
studio.guardar_prompt(req, "03_amanecer_pampa",
                      subcarpeta=f"lotes/{proyecto}/prompts")

# 4. Tranquera
req = studio.lotes.tranquera_argentina(municipio=municipio)
studio.guardar_prompt(req, "04_tranquera",
                      subcarpeta=f"lotes/{proyecto}/prompts")

# 5. Molino
req = studio.lotes.molino_tanque_australiano(municipio=municipio)
studio.guardar_prompt(req, "05_molino_tanque",
                      subcarpeta=f"lotes/{proyecto}/prompts")

# 6. Render del proyecto (casa posible)
req = studio.construccion.render_proyecto(
    estilo="casa de campo tradicional con galería",
    hectareas=hectareas, municipio=municipio)
studio.guardar_prompt(req, "06_render_proyecto",
                      subcarpeta=f"lotes/{proyecto}/prompts")

print("6 prompts generados en inmuebles/lotes/chacra-canuelas-5ha/prompts/")
```

**Resultado**: 6 archivos `.json` con los prompts optimizados para SDXL.

---

## Paso 4 — Generar las imágenes (10-30 minutos)

**Opción A — Con Fooocus local** (recomendado si lo tenés corriendo):

1. Abrir Fooocus en `http://127.0.0.1:7865`
2. Para cada prompt en `inmuebles/.../prompts/*.json`:
   - Copiar el campo `prompt` al textbox "Prompt"
   - Copiar `negative_prompt` al "Negative Prompt"
   - Seleccionar el `aspect_ratio` del JSON
   - En "Styles" tildar los listados en `styles`
   - Click "Generate"
   - Descargar el resultado con el mismo nombre del JSON (`01_portada_atardecer.jpg`)

**Opción B — Con Midjourney / DALL-E / Flux**:

1. Abrir `inmuebles/.../prompts/01_portada_atardecer.json`
2. Copiar el `prompt` y pegarlo en Midjourney
3. Agregar al final: `--ar 16:9 --style raw --v 6` (para Midjourney v6)
4. Descargar el resultado y guardarlo en la misma carpeta con extensión `.jpg`

**Opción C — Hacerlo después**:

Podés seguir con el workflow sin imágenes todavía. El estudio va a hacer
dry-run sin imágenes y vos las agregás cuando estén listas.

---

## Paso 5 — Crear el post simple de venta (2 minutos)

```python
post = studio.post.post_lote_venta(
    tema="5 ha en Cañuelas, a 65 km de CABA",
    municipio="Cañuelas",
    hectareas="5 hectáreas",
    distancia_caba="65 km",
    servicios_disponibles=(
        "luz eléctrica, alambrado perimetral nuevo, "
        "calle de tierra mejorada, molino y tanque australiano"
    ),
    tono="emotivo",
    nichos=["general", "campo", "inversion"],
)
studio.guardar_post(post, "post_01_venta",
                    proyecto="chacra-canuelas-5ha")
print(post["caption_completo"])
```

**Salida**: archivo JSON en `inmuebles/lotes/chacra-canuelas-5ha/posts/`
con el caption completo (incluyendo hashtags).

---

## Paso 6 — Crear el carrusel (3 minutos)

```python
from carruseles import CarruselFactory
factory = CarruselFactory(studio)

carrusel = factory.lote_premium(
    tema="5 ha en Cañuelas, a 65 km de CABA",
    municipio="Cañuelas",
    hectareas=5,
    precio_usd="USD 60.000",
    distancia_caba="65 km",
    tono="emotivo",
    n_slides=6,
)
factory.guardar(carrusel, "lote_premium_emotivo",
                proyecto="chacra-canuelas-5ha")
print(f"Carrusel con {carrusel.n_slides} slides generado")
```

**Salida**: carpeta `inmuebles/.../carruseles/lote_premium_emotivo/`
con `carrusel.json`, `carrusel.md`, `caption_instagram.txt` y `slides/`
con un JSON por slide.

---

## Paso 7 — Dry-run del post (1 minuto)

```python
from instagram_publisher import InstagramPublisher, ModoPublicacion
from instagram_auth import InstagramAuth

publisher = InstagramPublisher(InstagramAuth())
resultado = publisher.publicar_foto(
    ruta_imagen="inmuebles/lotes/chacra-canuelas-5ha/prompts/01_portada_atardecer.jpg",
    caption=post["caption"],
    hashtags=post["hashtags"],
    modo=ModoPublicacion.DRY_RUN,
)
```

**Salida**: ves el preview de lo que se publicaría (caption, tamaño imagen).
**No publica nada**.

---

## Paso 8 — Configurar Meta + Cloudinary (15 minutos, solo primera vez)

Si querés publicar de verdad, seguí `README_PUBLICACION_IG.md`. Resumen:

1. Convertir tu IG a cuenta Business
2. Crear app en developers.facebook.com
3. Vincular IG + pedir permisos
4. Obtener token de larga duración (60 días)
5. Crear cuenta Cloudinary
6. Crear `auth.json` con todos los datos

Verificar todo:
```bash
python3 instagram_auth.py
```

Debe decir:
```
✓ Token válido
✓ Permisos OK
✓ Cuenta: @tu_cuenta (XXX seguidores)
```

---

## Paso 9 — Publicar de verdad (1 minuto)

⚠️ **Cuidado**, esto publica realmente en Instagram.

Cambiá el modo:
```python
resultado = publisher.publicar_foto(
    ruta_imagen="inmuebles/.../01_portada_atardecer.jpg",
    caption=post["caption"],
    hashtags=post["hashtags"],
    modo=ModoPublicacion.REAL,  # ← antes era DRY_RUN
)
print(resultado.to_dict())
```

**Salida exitosa**:
```
{'exito': True, 'instagram_post_id': '17912345678901234',
 'permalink': 'https://www.instagram.com/p/CxYz...'}
```

---

## Paso 10 — Verificar en Instagram

1. Abrir tu perfil de Instagram
2. Buscar el post recién publicado
3. Verificar que:
   - La imagen se vea bien
   - El caption esté completo
   - Los hashtags aparezcan al final
4. Si algo está mal, **borrar el post manualmente** desde IG y volver a empezar

---

## Resumen de tiempos

| Paso | Tiempo | Bloqueante |
|---|---|---|
| 1. Probar estudio | 2 min | sí |
| 2. Definir proyecto | 5 min | no |
| 3. Generar prompts | 5 min | sí |
| 4. Generar imágenes | 10-30 min | no (se puede después) |
| 5. Crear post simple | 2 min | no |
| 6. Crear carrusel | 3 min | no |
| 7. Dry-run | 1 min | no |
| 8. Setup Meta+Cloudinary | 15 min (solo 1ra vez) | sí para publicar |
| 9. Publicar real | 1 min | sí |
| 10. Verificar en IG | 2 min | sí |

**Total primera vez**: ~45 minutos
**Total siguientes veces**: ~5-10 minutos (sin setup Meta)

---

## Próximos posts

Una vez que tenés el primer post publicado, el flujo se simplifica:

1. Generar prompts nuevos (Paso 3)
2. Generar imágenes (Paso 4)
3. Crear post (Paso 5)
4. Dry-run (Paso 7)
5. Publicar (Paso 9)

Para **automatizar toda la semana**:
```python
from studio import Studio
from instagram_publisher import ModoPublicacion

studio = Studio()
resultado = studio.pipeline_semana(
    semana_n=2,  # siguiente semana
    proyectos=["chacra-canuelas-5ha"],
    posts_por_semana=5,
    municipio_principal="Cañuelas",
    modo_publicacion=ModoPublicacion.DRY_RUN,  # simula todo
)
print(resultado.resumen)
```

---

## Errores comunes durante el primer post

Si algo falla, andá directo a `TROUBLESHOOTING.md`. Los más frecuentes:

- **Token expirado**: TROUBLESHOOTING #3
- **Cloudinary sin configurar**: TROUBLESHOOTING #5
- **Imagen muy pesada**: TROUBLESHOOTING #6
- **Caption con emojis rotos**: TROUBLESHOOTING #7
- **Pipeline 0/5 OK**: TROUBLESHOOTING #14

---

## Tips para el primer post

1. **Empezá con un carrusel**, no con un post simple. Los carruseles tienen
   3x más alcance en IG.
2. **Usá tono emotivo** para el primer post. Genera más conexión.
3. **No publiques entre 22:00 y 8:00**. El algoritmo penaliza.
4. **Respondé todos los comentarios** de las primeras 2 horas.
5. **Esperá 24 hs antes de publicar el segundo post** para no saturar a
   tus primeros seguidores.

---

## Si todo sale bien

Después del primer post, ya tenés el flujo dominado. Los siguientes pasos
naturales son:

1. Crear más proyectos (`mkdir -p inmuebles/lotes/<otro_proyecto>/`)
2. Generar calendario mensual (5 posts/semana)
3. Probar antes/después con fotos reales de obras
4. Experimentar con los 4 tonos de caption
5. Una vez que publiques 10+ posts, ver qué horarios y tonos te dan
   mejor engagement y ajustar

---

## Soporte

- `CHEATSHEET.md` — comandos rápidos
- `TROUBLESHOOTING.md` — 15 errores comunes
- `README_PUBLICACION_IG.md` — setup Meta + Cloudinary
- `README_INMOBILIARIO.md` — referencia completa