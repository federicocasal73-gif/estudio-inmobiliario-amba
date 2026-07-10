# 01 - Vision y alcance

## Que problema resuelve

Si vendes lotes, chacras, countries o servicios de construccion en el AMBA
y queres mantener una cuenta de Instagram activa, este estudio te resuelve
tres problemas concretos:

1. **Generar prompts visuales** en formato optimizado para SDXL/Fooocus o
   para cualquier IA externa (Midjourney, DALL-E, Flux), con vocabulario
   especifico del mercado inmobiliario rural de Buenos Aires.

2. **Generar captions** en espanol rioplatense (no espanol de Espana) con
   tonos que funcionan en el nicho: emotivo, inversion, premium, practico,
   familiar, profesional, etc.

3. **Planificar la publicacion semanal** con deteccion automatica de fechas
   clave argentinas (Dia de la Madre, Padre, Black Friday, Navidad, etc) y
   distribucion inteligente por tipo de contenido.

## Que hace

- Genera **prompts SDXL** listos para Fooocus, Midjourney, DALL-E o Flux
- Genera **captions en espanol rioplatense** con hashtags zonales
- Crea **carruseles** de 4-10 slides con caption narrativo y prompts por slide
- Crea **stories** y **reels** (con prompts 9:16 y caption corto)
- Genera **calendario semanal** con posts completos por slot
- Genera **antes/despues** para obras en curso (3 modos: real, ia, mixto)
- **Mejora fotos** existentes con 5 looks diferentes (magazine, golden hour, etc)
- Publica **directo a Instagram** via Graph API (3 modos: dry-run, interactivo, real)
- Rota inteligentemente entre proyectos segun historial de publicaciones
- Valida que captions y hashtags cumplan los limites de Instagram
- Genera **preview HTML** de carruseles antes de producir las imagenes
- Hace **A/B testing** de captions (N variantes del mismo post)
- Lleva **historial** de publicaciones con metricas basicas

## Que NO hace

Para que no te lleves sorpresas:

- **No genera imagenes** sin tener Fooocus corriendo. Te da los prompts
  para que los pegues en cualquier IA externa o en la UI web de Fooocus.

- **No se conecta automaticamente** con tu cuenta de Instagram. Necesitas
  hacer un setup manual de 15-20 min (ver `README_PUBLICACION_IG.md`).

- **No mide metricas** (engagement, reach, clicks). Para eso necesitas
  Instagram Insights o un tool externo.

- **No tiene A/B testing automatico** en Instagram. El estudio genera
  las variantes, vos publicas y medis manualmente.

- **No incluye video/reel real**, solo la imagen y el caption. Para reels
  con video, subi el video manualmente y usas el caption generado.

- **No traduce** a otros idiomas. Las plantillas estan en espanol rioplatense.

- **No se integra** con portales como MercadoLibre, Zonaprop, RE/MAX, etc.
  Es solo para Instagram.

- **No tiene OAuth automatico** para Instagram. El token se genera manual
  en Graph API Explorer y se pega en `auth.json`.

- **No incluye IA para elegir el mejor horario** de publicacion. Los horarios
  son heuristicos basados en buenas practicas generales.

## A quien esta dirigido

### Caso ideal

- Corredor inmobiliario con foco en AMBA
- Constructora de casas rurales / countries / chacras
- Loteo / desarrollador de barrios cerrados en AMBA
- Martillero publico + equipos de marketing

### Caso no ideal

- Quien vende propiedades en CABA puro (departamentos, PHs): el estudio esta
  enfocado en rural + AMBA periurbano. Podrias adaptarlo pero vas a tener
  que agregar prompts urbanos.
- Quien necesita publicar en muchas cuentas simultaneamente: el estudio esta
  pensado para 1 cuenta por vez.
- Quien quiere automatizar 100% la publicacion sin supervision: por
  seguridad siempre hay un modo dry-run y/o interactivo.

## Que tipo de contenido podes generar

### Posts individuales (1 imagen)
- Venta de lote
- Venta de country
- Venta de campo
- Preventa de loteo
- Lote periurbano
- Servicios de empresa
- Testimonial de cliente
- Preguntas frecuentes (FAQ)
- Avance semanal de obra
- Reel hook (caption corto)

### Carruseles (2-10 imagenes)
- **Lote premium** (6 slides): portada + aerea + tranquera + molino + render + CTA
- **Country etapa** (5 slides): portada + masterplan + amenity + obra + CTA
- **Obra avance** (4 slides): portada + foto real + render objetivo + CTA
- **Etapas de construccion** (8 slides): replanteo, fundaciones, estructura, etc
- **Steel frame completo** (6 slides): diseno, estructura, cerramiento, etc
- **Llave en mano** (8 slides): diseno, estudio, permisos, obra, etc
- **Terminaciones** (6 slides): revoques, aberturas, pisos, etc
- **Obra completa** (8 slides): before/during/after de una obra
- **Servicios** (8 slides): portada + 6 servicios + CTA
- **Story** (3 slides): 9:16 vertical
- **Reel** (1 slide): 9:16 con caption corto

### Calendario semanal
- 1-7 posts por semana (configurable)
- Distribucion automatica por dia
- Deteccion de fechas clave argentinas
- Posts completos generados por slot

## Frecuencia recomendada

| Contenido | Frecuencia optima | Por que |
|---|---|---|
| Posts (feed) | 3-5 por semana | Mantiene cuenta activa sin saturar |
| Stories | 1-3 por dia | Visibilidad diaria |
| Carruseles | 2-3 por semana | Mayor alcance que fotos individuales |
| Reels | 1-2 por semana | Crece la cuenta rapidamente |

Con el estudio podes producir todo esto en ~30 minutos de trabajo semanal.

## Que sigue

- [02-arquitectura.md](02-arquitectura.md): como estan organizados los modulos
- [03-instalacion.md](03-instalacion.md): setup paso a paso
- [04-casos-de-uso.md](04-casos-de-uso.md): ejemplos practicos end-to-end