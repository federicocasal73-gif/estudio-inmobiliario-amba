# 06 - Comandos CLI (`studio.py`)

El estudio expone un CLI con 7 subcomandos via `python3 studio.py <comando>`.

## Help general

```bash
python3 studio.py --help
```

Output:
```
usage: studio.py [-h] {demo,semana,duplicar,publicar,preview,generar,listar} ...

positional arguments:
  {demo,semana,duplicar,publicar,preview,generar,listar}
    demo                Corre el pipeline de demo
    semana              Genera calendario semanal completo
    duplicar            Duplica un proyecto
    publicar            Publica un carrusel existente
    preview             Genera preview HTML de un carrusel
    generar             Genera imagenes para un carrusel
    listar              Lista carruseles disponibles

options:
  -h, --help            show this help message and exit
```

---

## 1. `demo`

**Que hace**: corre el pipeline de ejemplo con el proyecto `chacra-canuelas-5ha`.

**Uso**:
```bash
python3 studio.py demo
```

**Output esperado**:
```
============================================================
PIPELINE SEMANA - RESULTADO
============================================================
Semana 1 (...): 5 slots, 1 carruseles generados, 0/5 publicaciones OK
```

**Cuando usarlo**: para verificar que todo funciona despues de instalar o
despues de cambios.

---

## 2. `semana`

**Que hace**: genera un calendario semanal completo: posts por slot + carruseles
faltantes + dry-run/publicacion.

**Uso**:
```bash
python3 studio.py semana \
  --n 1 \
  --proyectos chacra-canuelas-5ha country-pilar-ejemplo \
  --posts 5 \
  --municipio "Cañuelas" \
  --publicar dry-run
```

**Argumentos**:
- `--n N`: numero de semana (1 = esta semana, 2 = la que viene, etc)
- `--proyectos P1 P2 ...`: lista de proyectos a rotar
- `--posts N`: cantidad de posts por semana (1-7)
- `--municipio "X"`: municipio principal (afecta hashtags y nombres)
- `--fecha-inicio YYYY-MM-DD`: opcional, default lunes de la semana N
- `--publicar {dry-run|interactivo|real}`: modo de publicacion

**Cuando usarlo**: cada lunes para planificar la semana.

**Output**:
```
Semana 1 (2026-07-06 → 2026-07-12): 5 slots, 2 carruseles generados, 0/5 publicaciones OK
```

Ademas genera:
- `inmuebles/calendarios/semana_NN/plan.md` (tabla Markdown)
- `inmuebles/calendarios/semana_NN/plan.ics` (Google Calendar)
- `inmuebles/calendarios/semana_NN/plan.json` (datos completos)
- `inmuebles/calendarios/semana_NN/plan.csv` (Excel)
- `inmuebles/lotes/<proyecto>/carruseles/...` (carruseles faltantes)
- `inmuebles/pipelines/pipeline_semana_NN_*.json` (reporte completo)

---

## 3. `duplicar`

**Que hace**: clona un proyecto existente con cambios (hectareas, municipio, etc).

**Uso**:
```bash
python3 studio.py duplicar \
  --origen chacra-canuelas-5ha \
  --destino chacra-mercedes-3ha \
  --hectareas 3 \
  --municipio "Mercedes"
```

**Argumentos**:
- `--origen`: nombre del proyecto a clonar
- `--destino`: nombre del nuevo proyecto
- `--hectareas`: opcional, override
- `--municipio`: opcional, override

**Cuando usarlo**: cuando queres crear variantes rapidas de un mismo proyecto
(otra hectareaje, otra ubicacion).

**Limitaciones**: solo actualiza los prompts SDXL; los archivos JSON
especificos (como posts/captions) mantienen el contenido original.

---

## 4. `publicar`

**Que hace**: publica un carrusel.json existente en Instagram.

**Uso**:
```bash
python3 studio.py publicar \
  --carrusel inmuebles/lotes/chacra-canuelas-5ha/carruseles/lote_premium/carrusel.json \
  --modo dry-run
```

**Argumentos**:
- `--carrusel`: path al `carrusel.json`
- `--modo {dry-run|interactivo|real}`: modo de publicacion

**Cuando usarlo**: cuando ya tenes imagenes generadas y queres subir.

**Output**:
```
Modo: dry-run
Exito: False
Tipo: carrusel
Imagenes: 0
Caption length: 802
Error: Necesita >= 2 imagenes (encontradas: 0)
```

**Requisitos**:
- `auth.json` configurado (Meta + Cloudinary)
- Imagenes `.jpg`/`.png` en la carpeta `slides/` del carrusel
- Cambiar `--modo` a `real` para publicar de verdad

---

## 5. `preview`

**Que hace**: genera un HTML self-contained de un carrusel para previsualizar
sin generar las imagenes.

**Uso**:
```bash
python3 studio.py preview \
  --carrusel inmuebles/lotes/chacra-canuelas-5ha/carruseles/lote_premium/carrusel.json
```

**Output**:
```
Preview HTML generado en: inmuebles/lotes/chacra-canuelas-5ha/carruseles/lote_premium/preview.html
Abrilo con doble-click en tu navegador.
```

**Cuando usarlo**: para validar concepto de un carrusel antes de gastar tiempo
generando las 6 imagenes.

---

## 6. `generar`

**Que hace**: envia los prompts de cada slide al generador de imagenes
configurado (StubImageGenerator o FooocusImageGenerator).

**Uso**:
```bash
python3 studio.py generar \
  --carrusel inmuebles/lotes/chacra-canuelas-5ha/carruseles/lote_premium/carrusel.json
```

**Argumentos**:
- `--carrusel`: path al `carrusel.json`

**Output** (sin Fooocus activo):
```
Fooocus disponible: False
Slides procesados: 6
  slide 1: stub (imagen NO generada, ver mensaje en JSON al lado)
  ...
  slide 6: saltado (sin prompt)
```

**Output** (con Fooocus activo):
```
Fooocus disponible: True
Slides procesados: 6
  slide 1: generada en inmuebles/.../slides/slide_01_portada.jpg
  ...
```

**Cuando usarlo**: con Fooocus corriendo. Sin Fooocus, los prompts quedan
guardados como `.prompt.json` para que los pegues manualmente.

---

## 7. `listar`

**Que hace**: lista todos los carruseles generados en el proyecto o en todos.

**Uso**:
```bash
# Listar todos
python3 studio.py listar

# Filtrar por proyecto
python3 studio.py listar --proyecto chacra-canuelas-5ha
```

**Output**:
```
Encontrados 6 carruseles:
  - lote_premium (6 slides, Cañuelas, lote_premium)
  - country_etapa (5 slides, Pilar, country_etapa)
  - obra_avance (4 slides, Escobar, obra_avance)
  ...
```

**Cuando usarlo**: para ver que carruseles tenes disponibles antes de publicar.

---

## Combinaciones comunes

### Workflow semanal completo (recomendado)
```bash
# 1. Lunes: planificar la semana
python3 studio.py semana --n 1 --proyectos chacra-canuelas-5ha --publicar dry-run

# 2. Martes: revisar y publicar lo que se pueda
python3 studio.py listar
python3 studio.py publicar --carrusel inmuebles/.../carrusel.json --modo real
```

### Generar y publicar todo de una (solo con Fooocus activo)
```bash
python3 studio.py semana --n 1 --proyectos X --publicar real
```

### Debugging
```bash
# Ver que carruseles hay
python3 studio.py listar

# Ver preview HTML de uno
python3 studio.py preview --carrusel path

# Re-generar los prompts
python3 studio.py generar --carrusel path
```

---

## Que sigue

- [07-flujos-end-to-end.md](07-flujos-end-to-end.md): pipelines automaticos
- [08-publicacion-instagram.md](08-publicacion-instagram.md): setup Meta + Cloudinary
- [09-limitaciones-y-workarounds.md](09-limitaciones-y-workarounds.md): limitaciones conocidas