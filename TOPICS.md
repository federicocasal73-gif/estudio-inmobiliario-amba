# Configuracion del repo en GitHub (pasos manuales)

Este archivo documenta los pasos que necesitas hacer **una sola vez**
desde la UI web de GitHub para terminar la configuracion del repo.

> Por que este archivo existe: la API REST de GitHub necesita un token
> personal para hacer cambios en la metadata. Como automatizar eso desde
> aqui requiere configurar un PAT (Personal Access Token) y guardarlo en
> disco, preferi dejar estos pasos como instrucciones que vos podes hacer
> en 2 minutos desde tu navegador.

---

## 1. Description del repo (desde la UI web)

URL: https://github.com/federicocasal73-gif/estudio-inmobiliario-amba/settings

1. Click en **Settings** (boton del engranaje arriba a la derecha)
2. En la seccion **General**, encontrar el campo **Description**
3. Pegar esto (reemplaza la descripcion actual "Sistema para Nova"):

```
Sistema completo para crear contenido de Instagram enfocado en lotes, chacras,
campos, countries y servicios de construccion en la Zona Metropolitana de
Buenos Aires (Argentina). Genera prompts SDXL, captions rioplatenses,
carruseles, calendarios semanales y publica via Instagram Graph API.
```

4. Click **Save**

---

## 2. Topics (tags) del repo

Mismo lugar: https://github.com/federicocasal73-gif/estudio-inmobiliario-amba/settings

1. En **General**, encontrar el campo **Topics**
2. Click en **Add topic**
3. Pegar estos topics uno por uno (enter para confirmar cada uno):

```
instagram
real-estate
argentina
inmobiliaria
content-generation
stable-diffusion
sdxl
fooocus
social-media
automation
```

4. Cuando termines, click fuera del campo. Se guardan automaticamente.

Topics mejoran la descubribilidad: alguien que busque "instagram
automation" en GitHub va a encontrar el repo.

---

## 3. Website URL (opcional)

Mismo lugar: **Settings → General → Website**

Si queres agregar un link externo (tu portfolio, blog, etc):

```
https://tu-portfolio.example.com
```

Si no, dejar vacio.

---

## 4. About (sidebar derecho)

En la pagina principal del repo, hay un circulo "About" en la sidebar
derecha. Click en el engranaje al lado de "About" para editar:

- Description: la misma que pusiste arriba
- Website: igual
- Topics: ya estan en otra seccion, no se duplica

---

## 5. Pin el repo a tu perfil (opcional)

Si queres que aparezca destacado en tu perfil de GitHub:

1. Ir a tu perfil: https://github.com/federicocasal73-gif
2. Click **Customize your pins**
3. Selecciona `estudio-inmobiliario-amba`
4. Save

---

## 6. Releases (cuando tengas una version estable)

1. Ir a https://github.com/federicocasal73-gif/estudio-inmobiliario-amba/releases/new
2. Tag: `v1.0.0`
3. Title: "v1.0.0 - Initial release"
4. Description:

```
Primera version estable del estudio.

Incluye:
- 14 modulos Python
- 43 plantillas de prompts SDXL rurales pampeanas
- 24 tipos de caption rioplatenses
- 11 tipos de carruseles automaticos
- Calendario editorial con deteccion de fechas clave AR
- Cliente real de Fooocus (gradio-client)
- Publicacion automatica en Instagram via Graph API
- Manual completo de 11 archivos
```

5. Publish

---

## Comandos utiles despues

```bash
# Clone en otra maquina
git clone git@github.com:federicocasal73-gif/estudio-inmobiliario-amba.git

# Ver cambios que enviaste
cd estudio-inmobiliario-amba
git log --oneline
git remote -v

# Para futuros commits
git add .
git commit -m "..."
git push
```

El remote ya esta configurado en SSH. Si trabajas desde otra maquina, usa
HTTPS + Personal Access Token.

---

## Mantenimiento futuro

- **Tokens**: el `access_token` de Meta vence cada 60 dias. Renovar manualmente
- **Modelos**: si Fooocus agrega nuevos modelos/checksum, actualizar
  `prompts_inmobiliarios.json` y `captions_instagram.json`
- **Tags**: agregar nuevos municipios a la lista `MUNICIPIOS_AMBA` en
  `validators.py`
- **Carruseles**: agregar tipos nuevos siguiendo el patron en `carruseles.py`

Cualquier cambio = commit + push. El proyecto esta listo para evolucionar.
