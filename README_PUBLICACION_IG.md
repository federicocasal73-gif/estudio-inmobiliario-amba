# Publicación automática en Instagram — Setup paso a paso

Esta guía explica cómo configurar la publicación automática de fotos y
carruseles en Instagram usando el estudio. **Antes de poder publicar nada
tenés que hacer este setup una sola vez.** Sin este setup, el estudio
funciona en modo `--dry-run` y no publica nada.

## ¿Qué necesito?

1. Una cuenta de **Instagram Business** o **Creator** (no sirve Personal)
2. Una **página de Facebook** vinculada a esa cuenta de Instagram
3. Una **app de Meta for Developers** (gratis, 10 min de setup)
4. Una cuenta de **Cloudinary** gratis (25 GB de almacenamiento)
5. ~20 minutos para hacer todo el setup

## Paso 1: Convertir tu Instagram a cuenta Business

Si ya es Business, saltar este paso.

1. Abrir Instagram en el celular
2. Ir a **Perfil → Menú (☰) → Configuración → Cuenta**
3. **Cambiar tipo de cuenta → Cuenta profesional**
4. Elegir categoría (ej: "Agente inmobiliario", "Construcción", etc.)
5. Vincular a una **página de Facebook**:
   - Si no tenés, te deja crear una en el momento
   - La página es **obligatoria** — sin ella no podés usar la API

## Paso 2: Crear app en Meta for Developers

1. Ir a https://developers.facebook.com/
2. Click **"Mis Apps" → "Crear app"**
3. Tipo: **"Otro"** (no elegir Business, es otro flow)
4. Tipo de app: **"Business"**
5. Nombre: el que quieras (ej: "Real Estate Studio AMBA")
6. Email de contacto: el tuyo
7. Crear app

## Paso 3: Agregar producto Instagram

1. En el dashboard de tu app, buscar **"Instagram"** en la lista de productos
2. Click **"Configurar"** en "Instagram Graph API" (no Instagram Basic Display)
3. Te va a pedir vincular tu cuenta Business

## Paso 4: Configurar permisos y obtener token

1. En el menú izquierdo: **Instagram Graph API → Permissions**
2. Solicitar los permisos (Meta los aprueba casi instantáneamente si tu app
   es nueva):
   - `instagram_basic`
   - `instagram_content_publish`
   - `pages_show_list`
3. Ir a **Herramientas → Graph API Explorer** (https://developers.facebook.com/tools/explorer/)
4. Seleccionar tu app en el dropdown
5. En "Permissions" tildar los 3 permisos de arriba
6. Click **"Generate Access Token"**
7. Se abre popup de Facebook → autorizar todo
8. **Copiar el token que aparece** (es largo, empieza con `EAA...`)

## Paso 5: Obtener tu Instagram User ID

El token solo no alcanza; necesitás el **ID numérico** de tu cuenta IG.

Con el token ya generado en el Explorer:

1. En el campo de URL del Explorer, reemplazar por:
   ```
   me/accounts?fields=instagram_business_account
   ```
2. Click **Submit**
3. Te devuelve algo como:
   ```json
   {
     "data": [{
       "instagram_business_account": {
         "id": "17841234567890123"
       }
     }]
   }
   ```
4. **Copiar ese número** (es el `instagram_user_id`)

## Paso 6: Extender el token a 60 días

Los tokens de corta duración vencen en 1-2 horas. Para extenderlo:

```bash
curl -X GET "https://graph.facebook.com/v19.0/oauth/access_token?grant_type=fb_exchange_token&client_id=TU_APP_ID&client_secret=TU_APP_SECRET&fb_exchange_token=TU_TOKEN_DE_CORTA"
```

Te devuelve un nuevo token que vence en 60 días. **Copialo**.

(Para 60 días renovables automáticamente necesitarías implementar refresh
tokens, eso es para v2.)

## Paso 7: Crear cuenta en Cloudinary

1. Ir a https://cloudinary.com/ y registrarse gratis
2. En el **Dashboard** copiar:
   - Cloud Name
   - API Key
   - API Secret

## Paso 8: Crear auth.json

En la raíz del proyecto, crear `auth.json` (NO se commitea a git):

```json
{
    "access_token": "EAAxxxxx_tu_token_de_60_dias",
    "instagram_user_id": "17841234567890123",
    "username": "tu_cuenta_ig",
    "app_id": "1234567890",
    "expires_at": "2026-09-30T00:00:00",
    "cloudinary": {
        "cloud_name": "tu_cloud_name",
        "api_key": "123456789012345",
        "api_secret": "tu_api_secret"
    }
}
```

Después de crearlo:

```bash
chmod 600 auth.json    # solo vos podés leerlo
```

## Paso 9: Verificar setup

```bash
python3 instagram_auth.py
```

Debería decir:
```
✓ Token válido
✓ Permisos OK
✓ Cuenta: @tu_cuenta (XXX seguidores)
```

Si algún check falla, revisar qué falta.

## Uso del estudio

### Dry-run (no publica nada, solo muestra qué haría):

```bash
python3 -c "
from instagram_publisher import InstagramPublisher, ModoPublicacion
from instagram_auth import InstagramAuth
publisher = InstagramPublisher(InstagramAuth())
publisher.publicar_foto(
    ruta_imagen='imagen.jpg',
    caption='Mi primer post',
    hashtags=['#lotes', '#chacras'],
    modo=ModoPublicacion.DRY_RUN,
)
"
```

### Interactivo (pide confirmación antes de publicar):

```python
publisher.publicar_foto(..., modo=ModoPublicacion.INTERACTIVO)
```

### Real (publica directamente):

⚠️ **Cuidado**, esto publica de verdad:

```python
publisher.publicar_foto(..., modo=ModoPublicacion.REAL)
```

### Publicar un carrusel completo:

```python
publisher.publicar_carrusel(
    rutas_imagenes=['slide1.jpg', 'slide2.jpg', 'slide3.jpg'],
    caption='...',
    hashtags=['#lotes'],
    modo=ModoPublicacion.DRY_RUN,
)
```

## Rate limits

Instagram Graph API permite:
- **25 posts por día** por cuenta
- **5 carruseles por día** por cuenta
- Respetar delay de **5-10 minutos entre posts** para no parecer bot

## Renovar el token

Cada 60 días tu token vence. Para renovarlo:
1. Volver al Graph API Explorer
2. Regenerar token con los mismos permisos
3. Re-extender con el curl del paso 6
4. Actualizar `auth.json`

## Troubleshooting

### "Token inválido o expirado"
Renovar el token (paso 6).

### "Faltan permisos: ['instagram_content_publish']"
Volver al paso 4 y solicitar el permiso. Si Meta lo rechazó, completar
el formulario de App Review explicando que vas a publicar contenido propio.

### "URL no accesible públicamente"
Cloudinary no configurado o la subida falló. Verificar credenciales.

### "Media processing failed"
La imagen puede ser muy pesada o tener formato no soportado. IG acepta
JPEG/PNG de hasta 8 MB. Convertir con:
```bash
python3 -c "from PIL import Image; img=Image.open('origen.png'); img.save('destino.jpg', 'JPEG', quality=92)"
```

### Las imágenes tardan mucho en procesarse
IG puede tardar 30-60 segundos en procesar después del POST. El publisher
espera automáticamente hasta que `status_code = FINISHED`.

## Sobre `auth.json`: IG + Cloudinary en el mismo archivo

Por simplicidad, `auth.json` agrupa dos cosas distintas:

- **Sección Instagram** (raíz del JSON): access_token, instagram_user_id, app_id, etc.
- **Sección Cloudinary** (sub-objeto `"cloudinary"`): cloud_name, api_key, api_secret.

Conceptualmente son servicios independientes. Si querés separarlos por
seguridad o por organización, podés:

1. Crear `cloudinary.json` con solo la sección cloudinary.
2. Modificar `cloudinary_upload.py:_cargar_config()` para que lea de
   `cloudinary.json` en vez de `auth.json`.

Mientras tanto, `auth.json` se guarda con `chmod 600` y está en `.gitignore`,
así que la seguridad no se ve afectada.

---

## Seguridad

- `auth.json` está en `.gitignore` — **no commitearlo nunca**
- Si se filtra, regenerar token inmediatamente en Graph API Explorer
- El token de larga duración da acceso a publicar en tu cuenta, tratar
  como una password