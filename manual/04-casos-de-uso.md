# 04 - Casos de uso practicos

6 ejemplos end-to-end. Todos usan como referencia el **proyecto Chacra 5 ha
en Cañuelas** que ya esta creado en `inmuebles/lotes/chacra-canuelas-5ha/`.

Para cada caso: contexto, codigo copy-paste, output esperado.

---

## Caso 1: Publicar un lote (el caso más comun)

**Contexto**: queres publicar una chacra de 5 ha en Cañuelas con un caption
emotivo.

**Codigo**:
```python
from realestate_studio import RealestateStudio

studio = RealestateStudio()
post = studio.post.post_lote_venta(
    tema="5 ha en Cañuelas",
    municipio="Cañuelas",
    hectareas="5 ha",
    distancia_caba="65 km",
    servicios_disponibles="luz electrica, alambrado perimetral, tranquera, molino",
    tono="emotivo",
)

print(post["caption_completo"])
```

**Output esperado**:
```
Imaginate esto todos los fines de semana 🌽

5 ha en Cañuelas

A 65 km de CABA, pero con la paz del campo. Donde tus hijos crecen sabiendo
de dónde viene lo que comen.

Escribime y te cuento.

#realestatecanuelas #lotes #chacras #tierrasenventa ...
```

**Que hacer con esto**:
1. Pegar el caption en Instagram
2. Acompanar con una imagen (foto real del lote o render generado)

**Variantes**: cambia `tono` por `"inversion"`, `"premium"` o `"practico"` para
diferentes angulos del mismo lote.

---

## Caso 2: Avance semanal de obra

**Contexto**: tu cliente esta construyendo una casa en Escobar, vas todos los
lunes a sacar foto y queres publicar el avance.

**Codigo**:
```python
from realestate_studio import RealestateStudio

studio = RealestateStudio()
post = studio.post.post_obra_avance_semanal(
    semana=3,
    municipio="Escobar",
    etapa="mamposteria",
    avance=40,
    tareas=[
        "Levantar paredes exteriores",
        "Instalar cañerias electricas",
        "Colocar dintel en ventanas",
    ],
    proxima_etapa="Losa",
    tono="practico",
)

print(post["caption_completo"])
```

**Output esperado**:
```
Semana 3 de obra en Escobar

Etapa actual: mamposteria
Avance: 40%

Esta semana:
- Levantar paredes exteriores
- Instalar cañerias electricas
- Colocar dintel en ventanas

Proxima semana: Losa

Te contamos como viene cada lunes
```

**Que hacer**:
1. Sacar foto de la obra
2. Pegar el caption + foto en Instagram
3. Repetir cada lunes (cambiar `semana=`, `etapa=`, `tareas=`)

---

## Caso 3: Carrusel de servicios de la constructora

**Contexto**: tu constructora hace movimiento de suelo, steel frame, terminaciones.
Queres un carrusel mostrando todos los servicios.

**Codigo**:
```python
from realestate_studio import RealestateStudio
from carruseles import CarruselFactory

studio = RealestateStudio()
factory = CarruselFactory(studio)

carrusel = factory.servicios(
    empresa="Construcciones Rurales",
    municipio="Cañuelas",
    n_slides=6,
)

factory.guardar(carrusel, "servicios_demo", proyecto="chacra-canuelas-5ha")
print(f"Carrusel con {carrusel.n_slides} slides guardado")
print()
print("Caption completo:")
print(carrusel.caption_completo)
```

**Output esperado**:
- 8 archivos en `inmuebles/lotes/chacra-canuelas-5ha/carruseles/servicios_demo/`
  - `carrusel.json`: metadata completa
  - `carrusel.md`: tabla con cada slide
  - `caption_instagram.txt`: caption copy-paste
  - `slides/slide_01_*.json` ... `slide_08_*.json`: prompts por slide
- Console: 8 slides guardado + caption completo

**Que hacer**:
1. Abrir `inmuebles/.../carruseles/servicios_demo/carrusel.md` para revisar
2. Generar las 8 imagenes (en Fooocus pegando cada prompt)
3. Subir como carrusel a Instagram con el caption

---

## Caso 4: Pipeline semanal completo

**Contexto**: queres planificar toda una semana de contenido de una, sin pensar.

**Codigo**:
```python
from studio import Studio
from instagram_publisher import ModoPublicacion

studio = Studio()
resultado = studio.pipeline_semana(
    semana_n=1,
    proyectos=["chacra-canuelas-5ha", "country-pilar-ejemplo"],
    posts_por_semana=5,
    municipio_principal="Cañuelas",
    modo_publicacion=ModoPublicacion.DRY_RUN,
)

print(resultado.resumen)
print()
for slot in resultado.slots:
    print(f"{slot.fecha} {slot.hora_sugerida} {slot.tipo_post}: {slot.tema}")
```

**Output esperado**:
```
Semana 1 (2026-07-06 → 2026-07-12): 5 slots, 2 carruseles generados, 0/5 publicaciones OK
```

**Que hacer**:
1. Revisar `inmuebles/calendarios/semana_01/plan.md` (tabla con toda la semana)
2. Revisar `plan.ics` (importable a Google Calendar)
3. Si tenes Meta + Cloudinary configurados, cambiar `modo_publicacion` a
   `REAL` para publicar directamente (NO recomendado la primera vez)

---

## Caso 5: Mejorar foto + generar post

**Contexto**: tenes una foto real de un lote tomada con el celular. Queres
mejorarla y publicarla con un caption.

**Codigo**:
```python
from mejora_fotos import MejoraFotos
from realestate_studio import RealestateStudio

# 1. Mejorar la foto
mejora = MejoraFotos()
resultado = mejora.mejorar(
    foto_path="mis_fotos/lote_original.jpg",
    modo="magazine",   # natural, magazine, instagram, golden_hour, pampa
    intensidad="media",  # baja, media, alta
    upscale=2,           # 1, 2, 3, 4
)

print(f"Foto mejorada: {resultado.foto_destino}")

# 2. Generar post para esa foto
studio = RealestateStudio()
post = studio.post.post_lote_venta(
    tema="Chacra en Cañuelas",
    municipio="Cañuelas",
    hectareas="5 ha",
    distancia_caba="65 km",
    tono="aspiracional",
)

# 3. Imprimir todo listo para subir a IG
print()
print("Caption para Instagram:")
print(post["caption_completo"])
print()
print(f"Sube esta imagen: {resultado.foto_destino}")
```

**Output esperado**:
- Foto mejorada en `mis_fotos/lote_original_mejorada/mejoras/...`
- Caption completo con hashtags

**Que hacer**:
1. Verificar la foto mejorada
2. Subir foto + caption a Instagram

**Variaciones** del modo:
- `natural`: preserva la foto, ajustes suaves
- `magazine`: look de inmobiliaria de lujo
- `instagram`: listo para subir
- `golden_hour`: calido, ideal para atardecer pampeano
- `pampa`: mas verde y cielo mas azul

---

## Caso 6: A/B testing de captions

**Contexto**: queres probar 3 tonos distintos del mismo post y ver cual
funciona mejor.

**Codigo**:
```python
from realestate_studio import RealestateStudio
from caption_variants import CaptionVariants

studio = RealestateStudio()
cv = CaptionVariants(studio)

variantes = cv.generar(
    tipo="lote_venta",
    n=3,
    tema="5 ha en Cañuelas",
    municipio="Cañuelas",
    hectareas="5 ha",
    distancia_caba="65 km",
    tonos=["emotivo", "inversion", "premium"],
)

# Imprimir las 3 variantes
for i, v in enumerate(variantes, 1):
    print(f"--- Variante {i} ({v.tono}) ---")
    print(v.caption_completo[:200] + "...")
    print()

# Elegir la "mejor" segun criterios
mejor = cv.mejor_caption_para_publicar(
    variantes,
    criterios={"tono_preferido": ["emotivo", "inversion", "premium"]},
)
print(f"Recomendado segun criterios: {mejor.variante_id}")

# Guardar en disco para comparar visualmente
cv.guardar(variantes, "variantes_demo", proyecto="chacra-canuelas-5ha")
```

**Output esperado**:
- 3 variantes con diferentes tonos
- Cada una con su caption completo
- Archivo `variantes_demo.txt` con las 3 lado a lado
- Archivo `variantes_demo.json` con metadata

**Que hacer**:
1. Abrir `inmuebles/lotes/chacra-canuelas-5ha/variantes/variantes_demo.txt`
2. Leer las 3 variantes
3. Publicar la que más te guste
4. Después de 1 semana, comparar engagement en Instagram Insights
5. Publicar la próxima semana con la otra variante
6. A los 2-3 ciclos ya tenés data para saber que tono funciona mejor con tu audiencia

---

## Que sigue

- [05-modulos.md](05-modulos.md): referencia de los 11 modulos (1 parrafo c/u)
- [06-comandos-cli.md](06-comandos-cli.md): el CLI completo
- [07-flujos-end-to-end.md](07-flujos-end-to-end.md): pipelines automaticos