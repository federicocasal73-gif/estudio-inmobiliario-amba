# 03 - Instalacion paso a paso

## Requisitos

- **Python 3.10+** (probado en 3.14)
- **Pillow** >= 10.0.0 (para mejora de fotos)
- Opcional: **Fooocus local** (http://127.0.0.1:7865) para generar imagenes reales
- Opcional: **Meta for Developers** + **Cloudinary** para publicar de verdad
- ~50 MB libres para los JSONs + outputs
- Sin requisitos de GPU (la IA corre aparte, no en este codigo)

## Setup minimo (5 minutos)

```bash
# 1. Clonar o descargar el repo
cd /home/fede/Desktop
# Si tenes git:
git clone <url-del-repo>
# O bajar el ZIP y descomprimirlo

cd estudio-inmobiliario-amba

# 2. Instalar la unica dependencia obligatoria
pip install Pillow

# Si tu Python es de sistema y se queja:
pip install --break-system-packages Pillow

# 3. Verificar que funciona
python3 realestate_studio.py
```

Si ves un prompt generado y un caption con hashtags, todo esta OK.

## Setup completo (30 minutos)

Ademas del minimo:

```bash
# 4. Instalar Fooocus local (opcional pero recomendado)
#    Sigue las instrucciones en readme original de Fooocus:
#    https://github.com/lllyasviel/Fooocus
#    Basicamente:
#      cd /home/fede/Desktop
#      git clone https://github.com/lllyasviel/Fooocus.git
#      cd Fooocus
#      python launch.py --preset default
#
#    Fooocus arranca en http://127.0.0.1:7865/

# 5. (opcional) Para conectar el estudio con Fooocus real:
pip install gradio-client

# 6. Setup de Meta + Cloudinary para publicar de verdad
#    Sigue README_PUBLICACION_IG.md paso a paso (15-20 min)
#    Al final tendras un auth.json con tus credenciales
```

## Estructura de carpetas

```
estudio-inmobiliario-amba/
├── README.md                          ← este archivo (no existe, MANUAL.md es el principal)
├── MANUAL.md                          ← indice del manual
├── LICENSE                            ← MIT
├── requirements.txt                   ← dependencias
├── .gitignore                         ← exclusiones para git
├── setup_git_remote.py                ← script para subir a GitHub
│
├── realestate_studio.py               ← orquestador principal
├── carruseles.py                      ← 11 tipos de carruseles
├── calendario_editorial.py            ← planificacion semanal
├── antes_despues.py                   ← flujo antes/despues
├── mejora_fotos.py                    ← 5 looks
├── validators.py                      ← validacion centralizada
├── image_generator.py                 ← stub + cliente Fooocus
├── preview_html.py                    ← preview HTML
├── caption_variants.py                ← A/B testing
├── historial_publicaciones.py         ← rotacion
├── studio.py                          ← CLI + pipeline
│
├── instagram_auth.py                  ← auth IG
├── instagram_publisher.py             ← publicador IG
├── cloudinary_upload.py               ← upload a Cloudinary
│
├── prompts_inmobiliarios.json         ← 43 plantillas de prompts
├── captions_instagram.json            ← 24 tipos de caption
├── auth_instagram_example.json        ← plantilla para auth.json
│
├── README_INMOBILIARIO.md             ← referencia principal
├── README_PUBLICACION_IG.md           ← setup Meta + Cloudinary
├── CHEATSHEET.md                      ← 17 ejemplos copy-paste
├── TROUBLESHOOTING.md                 ← 15 errores con fix
├── WORKFLOW_PRIMER_POST.md            ← paso a paso del primer post
│
├── generar_proyecto_ejemplo.py        ← script de demo
├── generar_carruseles_ejemplo.py      ← script de demo
│
└── inmuebles/                         ← outputs generados
    ├── lotes/                          ← proyectos de lotes
    ├── obras/                          ← antes/despues
    ├── servicios/                      ← carruseles de servicios
    ├── inputs/                         ← tus fotos (no commitees)
    ├── outputs/                        ← imagenes generadas
    ├── posts/                          ← captions completos generados
    ├── pipelines/                      ← reportes de pipeline semanal
    └── calendarios/                    ← planes semanales (md, json, ics, csv)
```

## Verificacion final

Ejecuta estos 4 tests y verifica que todos pasen:

```bash
# Test 1: studio principal
python3 realestate_studio.py
# Esperado: prompt generado + caption con hashtags

# Test 2: proyecto completo de ejemplo
python3 generar_proyecto_ejemplo.py
# Esperado: 6 prompts + 3 posts en inmuebles/lotes/chacra-canuelas-5ha/

# Test 3: carruseles
python3 generar_carruseles_ejemplo.py
# Esperado: 4 carruseles (lote_premium, country_etapa, obra_avance, servicios)

# Test 4: pipeline end-to-end
python3 studio.py demo
# Esperado: resumen con N slots, carruseles generados, 0/5 publicaciones OK

# Test 5: calendario
python3 calendario_editorial.py
# Esperado: semana 1 con 5 slots + plan.md + plan.ics

# Test 6: mejora de fotos (crea imagen de prueba)
python3 mejora_fotos.py
# Esperado: imagen mejorada en inmuebles/_test_mejora/mejoras/
```

Si los 6 funcionan, todo esta OK.

## Setup minimo de Meta + Cloudinary (resumen)

Ver `README_PUBLICACION_IG.md` para el paso a paso completo.

Resumen:
1. Convertir tu IG a cuenta Business
2. Crear app en https://developers.facebook.com
3. Vincular IG + pedir permisos (`instagram_basic`, `instagram_content_publish`, `pages_show_list`)
4. Obtener access token de larga duración (60 dias)
5. Crear cuenta Cloudinary
6. Crear `auth.json` con todos los datos
7. Verificar con `python3 instagram_auth.py`

## Variables de entorno opcionales

- `FOOOCUS_URL`: URL de Fooocus (default: `http://127.0.0.1:7865`)
- `FOOOCUS_TIMEOUT`: timeout en segundos (default: 600)

Ejemplo:
```bash
export FOOOCUS_URL=http://192.168.1.100:7865
export FOOOCUS_TIMEOUT=900
```

## Primer post de prueba (10 minutos)

Ver `WORKFLOW_PRIMER_POST.md` para el paso a paso detallado desde cero.

Resumen ejecutivo:
```bash
# 1. Generar prompt
python3 -c "
from realestate_studio import RealestateStudio
s = RealestateStudio()
print(s.lotes.chacra_pampeana(hectareas=5, municipio='Cañuelas').prompt)
"

# 2. Pegar el prompt en Midjourney o Fooocus, guardar la imagen

# 3. Generar el post
python3 -c "
from realestate_studio import RealestateStudio
s = RealestateStudio()
post = s.post.post_lote_venta(
    tema='5 ha en Cañuelas', municipio='Cañuelas',
    hectareas='5 ha', distancia_caba='65 km', tono='emotivo',
)
print(post['caption_completo'])
"

# 4. Copiar el caption + la imagen en Instagram
```

Eso es todo lo que necesitas para empezar.

## Que sigue

- [04-casos-de-uso.md](04-casos-de-uso.md): 6 ejemplos practicos end-to-end
- [05-modulos.md](05-modulos.md): referencia de los 11 modulos
- [06-comandos-cli.md](06-comandos-cli.md): CLI completo
- `WORKFLOW_PRIMER_POST.md`: paso a paso del primer post