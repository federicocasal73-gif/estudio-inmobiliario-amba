# TROUBLESHOOTING — Estudio Inmobiliario AMBA

15 errores comunes con causa y fix. Si tu problema no está acá, abrí un issue
o probá `python3 -c "import <modulo>; print(dir(<modulo>))"` para ver qué
funciones hay disponibles.

---

## 1. `ModuleNotFoundError: No module named 'Pillow'`

**Causa**: Pillow no está instalado en el Python que estás usando.

**Fix**:
```bash
pip install pillow
```

Si tenés varios Pythons:
```bash
python3 -m pip install pillow
```

---

## 2. `FileNotFoundError: auth.json` al intentar publicar

**Causa**: no seguiste el setup de Meta Developers + Cloudinary.

**Fix**:
1. Seguí `README_PUBLICACION_IG.md` paso a paso (10-20 min)
2. Creá `auth.json` en la raíz del proyecto
3. `chmod 600 auth.json`
4. Verificá con `python3 instagram_auth.py`

Mientras tanto, todo funciona en `ModoPublicacion.DRY_RUN`.

---

## 3. `Token inválido o expirado`

**Causa**: el access token vence cada 60 días.

**Fix**:
1. Ir a https://developers.facebook.com/tools/explorer/
2. Seleccionar tu app
3. Tildar permisos: `instagram_basic`, `instagram_content_publish`, `pages_show_list`
4. "Generate Access Token" → autorizar
5. Re-extender con curl:
   ```bash
   curl -X GET "https://graph.facebook.com/v19.0/oauth/access_token?grant_type=fb_exchange_token&client_id=TU_APP_ID&client_secret=TU_APP_SECRET&fb_exchange_token=TU_TOKEN"
   ```
6. Pegar el nuevo token en `auth.json` campo `access_token`
7. Verificar: `python3 instagram_auth.py`

---

## 4. `Faltan permisos: ['instagram_content_publish']`

**Causa**: tu app no pidió el permiso o Meta lo rechazó.

**Fix**:
1. Ir a developers.facebook.com → tu app → Instagram Graph API → Permissions
2. Solicitar `instagram_content_publish`
3. Si Meta pide App Review, completar el formulario explicando que vas a
   publicar contenido propio en tu propia cuenta (es automático, no tarda
   más de 24-48 hs)

---

## 5. `URL no accesible públicamente` al publicar

**Causa**: Cloudinary no está configurado o la subida falló.

**Fix**:
1. Crear cuenta en https://cloudinary.com (gratis)
2. Copiar Cloud Name, API Key, API Secret del Dashboard
3. Agregar a `auth.json`:
   ```json
   {
       "cloudinary": {
           "cloud_name": "tu_cloud",
           "api_key": "12345",
           "api_secret": "abcde"
       }
   }
   ```
4. Verificar: `python3 -c "from cloudinary_upload import CloudinaryUploader; print(CloudinaryUploader().configurado)"`

---

## 6. `Media processing failed`

**Causa**: la imagen es muy pesada (>8 MB) o tiene formato no soportado.

**Fix**:
```python
from PIL import Image
img = Image.open("imagen_origen.png")
img = img.convert("RGB")
img.save("imagen_destino.jpg", "JPEG", quality=85, optimize=True)
```

IG acepta JPEG y PNG de hasta 8 MB.

---

## 7. Caption con emojis rotos (`ðŸŒ¾` en vez de `🌾`)

**Causa**: el archivo se guardó con encoding incorrecto.

**Fix**: Asegurate de que todos los archivos `.py` y `.json` estén en UTF-8.
Si usás bash para editar:
```bash
file -i archivo.py    # debe decir charset=utf-8
```

Para forzar guardado en UTF-8:
```bash
iconv -f latin1 -t utf8 archivo.py > archivo_utf8.py
```

---

## 8. `Carrusel debe tener entre 2 y 10 imagenes`

**Causa**: IG no permite carruseles de 1 sola imagen ni de más de 10.

**Fix**:
```python
# Si tenés solo 1 imagen, publicar como foto
publisher.publicar_foto(...)

# Si tenés 11+, recortar a 10
imagenes = imagenes[:10]
publisher.publicar_carrusel(rutas_imagenes=imagenes, ...)
```

---

## 9. Hashtags con caracteres no-ASCII (`#chacras_en_cafuelas`)

**Causa**: municipio con acentos genera hashtags con errores en el slug.

**Fix**: el estudio ya sanitiza acentos (`_slug_municipio`), pero si ves el
problema, pasá el municipio sin acentos:
```python
# Antes: municipio="Cañuelas"  → hashtag "#cafuelasinmobiliaria"
# Después: municipio="Canuelas" → hashtag "#canuelasinmobiliaria" (limpio)
```

---

## 10. Fooocus no responde en `http://127.0.0.1:7865`

**Causa**: Fooocus no está corriendo.

**Fix**:
```bash
cd /home/fede/Desktop/Proyecto/Fooocus
source venv/bin/activate    # si usás venv
python launch.py --disable-offload-from-vram --preset default
```

Esperá 30-60 segundos a que carguen los modelos. Verificá:
```bash
curl http://127.0.0.1:7865/
```

Si seguís sin respuesta, revisá `troubleshoot.md` original de Fooocus.

---

## 11. Prompt generado en inglés en vez de español

**Causa**: por diseño. Los prompts SDXL rinden mejor en inglés (es donde
fue entrenado el modelo). El caption SÍ va en español.

**Fix**: no hay nada que arreglar. Si querés forzar español en el prompt,
agregá al final:
```python
req.prompt += ", landscape photography"
```

---

## 12. `calendar_editorial.py` no detecta el Día de la Madre

**Causa**: el algoritmo calcula el 3er domingo de octubre. Si tu semana
empieza en lunes pero el domingo cae fuera, no lo cuenta.

**Fix**: usá `fecha_inicio` para apuntar a la semana correcta:
```python
cal.generar_semana(
    semana_n=1,
    fecha_inicio="2026-10-12",  # lunes de la semana del Día de la Madre
)
```

El Día de la Madre 2026 cae el 18 de octubre (3er domingo).

---

## 13. La mejora de fotos no se ve "magazine"

**Causa**: la intensidad es muy baja o la foto original ya está sobreprocesada.

**Fix**: probá distintas combinaciones:
```python
# Look más fuerte
mejora.mejorar(foto, modo="magazine", intensidad="alta", upscale=2)

# Look más natural para fotos realistas
mejora.mejorar(foto, modo="natural", intensidad="alta", upscale=1)

# Look golden hour (más cálido, ideal para atardecer pampeano)
mejora.mejorar(foto, modo="golden_hour", intensidad="media", upscale=1)
```

---

## 14. Pipeline semanal termina con `0/5 publicaciones OK`

**Causa**: las imágenes todavía no se generaron. El pipeline corre en dry-run
correctamente pero no puede publicar sin imágenes reales.

**Fix**: dos caminos:
1. **Generar imágenes con Fooocus** (cuando esté activo) — abrir UI web y
   pegar los prompts que están en `inmuebles/.../prompts/*.json`
2. **Generar imágenes con IA externa** — copiar el prompt del JSON y usarlo
   en Midjourney/DALL-E/Flux, descargar el resultado a la misma carpeta

Después de tener las imágenes, re-ejecutar el pipeline.

---

## 15. `auth.json` queda expuesto en git por error

**Causa**: aunque está en `.gitignore`, a veces se commitea con `--force` o
antes de configurar el gitignore.

**Fix inmediato**:
1. Rotar el token YA en Graph API Explorer
2. Remover del repo: `git rm --cached auth.json`
3. Confirmar: `git status` no debe listarlo
4. Hacer commit del .gitignore

**Prevención**: nunca hagas `git add .` ni `git add auth.json`. Usá `git add
<archivos_específicos>`.

---

## Problemas no listados acá

Si tu problema no está en esta lista:

1. Probá `python3 -c "import <modulo>; help(<modulo>.<funcion>)"`
2. Activá debug agregando `print()` antes de la línea que falla
3. Buscá el mensaje exacto de error en Google
4. Abrí un issue en el repo con: comando ejecutado, output completo, sistema
   operativo, versión de Python (`python3 --version`)

---

## Comandos útiles para debug

```python
# Ver configuración actual
from realestate_studio import RealestateStudio
studio = RealestateStudio()
print("Municipios AMBA cargados:", list(studio.prompts_db.get("municipios_amba", {}).keys()))
print("Templates disponibles:", list(studio.prompts_db.get("plantillas_base", {}).keys()))

# Ver estado de auth
from instagram_auth import InstagramAuth
auth = InstagramAuth()
print("Configurado:", auth.configurado())
print("Token válido:", auth.validar_token())

# Ver estado de Fooocus
print("Fooocus activo:", studio.fooocus_activo())
```

---

## Soporte

- `README_INMOBILIARIO.md` — referencia
- `CHEATSHEET.md` — comandos rápidos
- `WORKFLOW_PRIMER_POST.md` — paso a paso guiado