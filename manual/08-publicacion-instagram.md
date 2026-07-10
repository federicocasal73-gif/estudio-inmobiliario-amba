# 08 - Publicacion en Instagram

Setup de Meta for Developers + Cloudinary para publicar de verdad en IG.
**Si solo queres generar contenido (sin publicar) podes saltearte este paso**.

Ver `README_PUBLICACION_IG.md` para el setup paso a paso completo (15-20 min).
Aca solo resumo lo esencial.

## Que necesitás

1. Cuenta de Instagram **Business** o **Creator** (no sirve Personal)
2. Facebook Page vinculada a esa cuenta IG
3. App en developers.facebook.com
4. Cuenta Cloudinary (gratis hasta 25 GB)
5. ~15-20 minutos para setup

## Setup rapido

1. **Convertir IG a Business**: Perfil → Menu → Configuracion → Cuenta →
   Cambiar tipo de cuenta → Cuenta profesional
2. **Crear app en Meta**: https://developers.facebook.com → Mis Apps →
   Crear app → Otro → Business
3. **Agregar Instagram Graph API**: Dashboard → Productos → Configurar Instagram
4. **Obtener token**: Herramientas → Graph API Explorer → seleccionar tu app →
   tildar permisos → Generate Access Token
5. **Extender token a 60 dias**: usar el curl en `README_PUBLICACION_IG.md`
6. **Crear cuenta Cloudinary**: https://cloudinary.com → signup
7. **Crear `auth.json`** en la raiz del estudio con todos los datos

## Estructura de `auth.json`

```json
{
    "access_token": "EAAxxxxx_tu_token_de_60_dias",
    "instagram_user_id": "17841234567890123",
    "username": "tu_cuenta_ig",
    "app_id": "1234567890",
    "expires_at": "2026-12-31T23:59:59",
    "cloudinary": {
        "cloud_name": "tu_cloud",
        "api_key": "12345",
        "api_secret": "abcde"
    }
}
```

## Verificar setup

```bash
python3 instagram_auth.py
```

Salida esperada:
```
OK: es un repo git valido
✓ Token válido
✓ Permisos OK
✓ Cuenta: @tu_cuenta (XXX seguidores)
```

Si falla, ver `TROUBLESHOOTING.md` seccion 3-5.

## Los 3 modos de publicacion

```python
from instagram_publisher import InstagramPublisher, ModoPublicacion
from instagram_auth import InstagramAuth

publisher = InstagramPublisher(InstagramAuth())

# 1. DRY_RUN (default, no publica)
resultado = publisher.publicar_foto(
    ruta_imagen="imagen.jpg",
    caption="Mi caption",
    hashtags=["#lotes", "#chacras"],
    modo=ModoPublicacion.DRY_RUN,
)
# Muestra preview de lo que se publicaria

# 2. INTERACTIVO (pide confirmacion)
resultado = publisher.publicar_foto(
    ruta_imagen="imagen.jpg",
    caption="Mi caption",
    hashtags=["#lotes"],
    modo=ModoPublicacion.INTERACTIVO,
)
# Te pregunta "Publicar foto imagen.jpg? [s/N]"

# 3. REAL (publica directamente)
resultado = publisher.publicar_foto(
    ruta_imagen="imagen.jpg",
    caption="Mi caption",
    hashtags=["#lotes"],
    modo=ModoPublicacion.REAL,
)
# Sube a Instagram. Devuelve el post ID y permalink
```

## Rate limits de Instagram

- **25 posts por dia** por cuenta
- **5 carruseles por dia** por cuenta
- Esperar **5-10 minutos entre posts** para no parecer bot
- Si excedes: error 429 que IG devuelve, esperar 1 hora

## Como elegir el modo

- **DRY_RUN**: usar SIEMPRE la primera vez que publiques algo
- **INTERACTIVO**: cuando ya estes seguro pero queres aprobacion manual
- **REAL**: solo para publicaciones programadas o scripts automatizados

## Renovacion del token

Cada 60 dias tu access_token vence. Para renovarlo:

1. Ir a https://developers.facebook.com/tools/explorer/
2. Regenerar token con los mismos permisos
3. Re-extender con el curl en `README_PUBLICACION_IG.md`
4. Pegar el nuevo token en `auth.json`

## Que hacer si algo falla

Ver `TROUBLESHOOTING.md` secciones:
- #2: `FileNotFoundError: auth.json`
- #3: Token invalido o expirado
- #4: Faltan permisos
- #5: URL no accesible (problema con Cloudinary)
- #6: Media processing failed (imagen muy pesada)

## Que sigue

- [09-limitaciones-y-workarounds.md](09-limitaciones-y-workarounds.md): 15 limitaciones conocidas
- [10-personalizacion.md](10-personalizacion.md): como agregar tus propios templates
- `README_PUBLICACION_IG.md`: setup paso a paso completo