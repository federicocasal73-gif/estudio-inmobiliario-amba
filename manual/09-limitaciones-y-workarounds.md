# 09 - Limitaciones y como resolverlas

15 limitaciones conocidas del estudio, con el workaround concreto para cada una.

---

## Limitaciones del estudio

### 1. No genera imagenes sin Fooocus corriendo
- **Impacto**: medio
- **Cuando pasa**: si no arrancaste Fooocus local
- **Workaround**: usar Midjourney, DALL-E o Flux con el prompt generado.
  Abrir el archivo `inmuebles/lotes/<proyecto>/prompts/*.json`,
  copiar el campo `prompt` en la IA externa.

### 2. Token de Instagram vence cada 60 dias
- **Impacto**: medio
- **Cuando pasa**: cuando intentas publicar y dice "token invalido"
- **Workaround**: renovar el token en Graph API Explorer cada 60 dias.
  Ver `TROUBLESHOOTING.md` seccion 3.

### 3. Sin OAuth automatico de Instagram
- **Impacto**: bajo (es setup inicial, no recurrente)
- **Cuando pasa**: la primera vez que configuras publicacion
- **Workaround**: seguir `README_PUBLICACION_IG.md` paso a paso (15-20 min
  la primera vez, despues es transparente).

### 4. Sin A/B testing automatico en Instagram
- **Impacto**: bajo
- **Cuando pasa**: queres saber que tono de caption funciona mejor
- **Workaround**: usar `caption_variants.py` para generar 3 variantes,
  publicarlas a lo largo de 2-3 semanas, medir en Instagram Insights cual
  tuvo mejor engagement. Usar el mejor como template.

### 5. Sin generacion de reels con video
- **Impacto**: medio
- **Cuando pasa**: queres un reel real (con video, no solo imagen)
- **Workaround**: el estudio genera el caption del reel + la imagen de portada.
  Para video: grabar en el celular, editar en CapCut o similar, subir
  manualmente a IG con el caption generado.

### 6. Sin integracion con portales (MercadoLibre, Zonaprop, RE/MAX)
- **Impacto**: medio (si vendes tambien en portales)
- **Cuando pasa**: queres publicar el mismo lote en multiples canales
- **Workaround**: copiar manualmente la descripcion a cada portal. El
  estudio podria extenderse para generar descripciones de portales pero
  hoy no lo hace.

### 7. Sin traduccion a otros idiomas
- **Impacto**: bajo (si solo vendes en Argentina)
- **Cuando pasa**: queres publicar en espanol neutro, portugues, ingles
- **Workaround**: usar DeepL o Google Translate para traducir los captions.
  Los hashtags hay que reemplazarlos por los del nicho del pais destino.

### 8. Sin metricas automaticas de Instagram
- **Impacto**: bajo
- **Cuando pasa**: queres saber likes, reach, saves de cada post
- **Workaround**: Instagram Insights (web o app) te da todo. Para
  automatizar, herramientas externas como Later, Metricool, Hootsuite.

### 9. Sin video transcoding
- **Impacto**: bajo
- **Cuando pasa**: queres subir un reel largo a IG (limite 90s)
- **Workaround**: exportar el video en formato IG-compatible (H.264, 1080x1920)
  con cualquier editor (CapCut, DaVinci, FFmpeg directo).

### 10. Carruseles maximo 10 imagenes
- **Impacto**: bajo (IG tampoco permite mas de 10)
- **Cuando pasa**: queres un carrusel con 15 imagenes
- **Workaround**: partir en 2 carruseles. El primero termina con "Continua
  en parte 2" en el caption.

### 11. Sin deteccion automatica de duplicados
- **Impacto**: bajo
- **Cuando pasa**: queres asegurarte de no publicar el mismo prompt 2 veces
- **Workaround**: `python3 studio.py listar` para ver que ya generaste.
  El `historial_publicaciones.py` lleva registro pero solo para
  publicaciones REALES.

### 12. Sin publicacion programada (scheduling)
- **Impacto**: medio
- **Cuando pasa**: queres programar el post para las 19:00 del viernes
- **Workaround**: publicar manualmente a la hora, o usar herramientas como
  Later, Buffer o Meta Business Suite (gratis para cuentas Business).

### 13. Sin comentarios automaticos / respuestas
- **Impacto**: bajo
- **Cuando pasa**: queres auto-responder comentarios
- **Workaround**: ManyChat o similar para bots de IG. Meta Graph API no
  permite publicar comentarios directamente.

### 14. Sin stories scheduling
- **Impacto**: bajo
- **Cuando pasa**: queres programar stories
- **Workaround**: el estudio genera el contenido del story (imagen + caption).
  Subi manualmente a IG cuando quieras, o usa Later/Meta Business Suite.

### 15. Sin soporte para multiple cuentas
- **Impacto**: bajo (si solo tenes 1 cuenta)
- **Cuando pasa**: si manejas varias cuentas IG
- **Workaround**: cada cuenta necesita su propio `auth.json`. Podes tener
  varios archivos (`auth_cuenta1.json`, `auth_cuenta2.json`) y un script
  propio que elija cual segun el proyecto.

---

## Limitaciones conocidas de Instagram (no del estudio)

Estas las pone IG, no las podes cambiar:

- **Carruseles**: 2-10 imagenes, maximo
- **Captions**: 2200 caracteres
- **Hashtags**: 30 maximo, IG solo muestra los primeros en preview
- **Mentions**: maximo 20 por post
- **Reels**: maximo 90 segundos (IGTV va por separado)
- **Stories**: 24 horas visibles (despues quedan en archivo)
- **Publicaciones por hora**: IG no tiene limite oficial pero > 5 posts por
  hora puede parecer spam

---

## Que sigue

- [10-personalizacion.md](10-personalizacion.md): como agregar tus propios templates
- `TROUBLESHOOTING.md`: 15 errores comunes con fix
- `README_PUBLICACION_IG.md`: setup Meta + Cloudinary