# 10 - Personalizacion del estudio

Como agregar tus propios templates, municipios, nichos y funciones.

---

## Agregar una nueva plantilla de prompt SDXL

Editas `prompts_inmobiliarios.json` y agregas una entrada en `plantillas_base`.

**Ejemplo**: agregar `pileta_quinta`:

```json
{
    "plantillas_base": {
        "pileta_quinta": "quinta with swimming pool, country house, manicured lawn, weekend retreat, Buenos Aires province, summer day, professional photography, sharp focus, 8k"
    }
}
```

Despues, agregar el metodo en `VerticalLotes` (o `VerticalConstruccion`):

```python
def pileta_quinta(self, hectareas: float = 2, municipio: str = "Escobar"):
    base = self.plantillas.get("pileta_quinta", "")
    prompt = f"quinta with swimming pool on {hectareas} hectares in {municipio}, {base}"
    return self._req(prompt, ASPECT_INSTAGRAM_LANDSCAPE, ...)
```

Y ya podes usarlo:
```python
req = studio.lotes.pileta_quinta(hectareas=2, municipio="Escobar")
```

---

## Agregar un nuevo tipo de caption

Editas `captions_instagram.json` y agregas:

```json
{
    "plantillas": {
        "mi_nuevo_tipo": [
            {
                "tono": "emotivo",
                "texto": "Template con {variable} que se completa al formatear."
            }
        ]
    }
}
```

Variables entre `{llaves}` se reemplazan cuando se usa. Despues agregar el
metodo en `CaptionFactory`:

```python
def post_mi_nuevo_tipo(self, variable: str, municipio: str = "Cañuelas"):
    caption = self.caption("mi_nuevo_tipo", "emotivo", variable=variable)
    hashtags = self.hashtags(["general"], municipio)
    return self._armar_post(f"Mi tema {variable}", "mi_nuevo_tipo", municipio,
                            "emotivo", caption, hashtags)
```

---

## Agregar un nuevo municipio

Editas `prompts_inmobiliarios.json`:

```json
{
    "municipios_amba": {
        "norte": ["Pilar", "Escobar", "MiNuevoMunicipio"]
    }
}
```

Y en `validators.py`, agregar a la lista `MUNICIPIOS_AMBA`:

```python
MUNICIPIOS_AMBA = {
    "Pilar", "Escobar", "MiNuevoMunicipio",
    # ... resto
}
```

---

## Agregar un nuevo nicho de hashtags

Editas `captions_instagram.json`:

```json
{
    "hashtags_por_nicho": {
        "mi_nicho": [
            "#hashtag1", "#hashtag2", "#hashtag3"
        ]
    }
}
```

Despues lo usas asi:

```python
tags = studio.post.hashtags(["mi_nicho"], "Cañuelas")
```

---

## Agregar una funcion a VerticalLotes o VerticalConstruccion

Abris `realestate_studio.py`, busca la clase correspondiente y agrega:

```python
def mi_nueva_funcion(self, parametro: str = "default",
                      municipio: str = "Cañuelas") -> GenerationRequest:
    """Descripcion de una linea de que hace."""
    base = self.plantillas.get("mi_prompt", "")
    prompt = f"{parametro} en {municipio}, {base}"
    return self._req(prompt, ASPECT_INSTAGRAM_LANDSCAPE, self.ESTILOS_FOTOS,
                     {"tipo": "mi_tipo", "parametro": parametro,
                      "municipio": municipio})
```

Y automaticamente queda accesible como `studio.lotes.mi_nueva_funcion()`.

---

## Agregar un nuevo tipo de carrusel

Abris `carruseles.py`, busca la clase `CarruselFactory` y agrega:

```python
def mi_nuevo_carrusel(self, tema: str, municipio: str = "Cañuelas",
                       n_slides: int = 6) -> Carrusel:
    """Descripcion de una linea."""
    if n_slides < 4:
        n_slides = 4

    # Generar los slides (con tus prompts especificos)
    slides: list[Slide] = []
    for i in range(1, n_slides + 1):
        req = self.studio.lotes.chacra_pampeana(
            hectareas=5, municipio=municipio)
        slides.append(Slide(
            numero=i, tipo="foto",
            descripcion=f"Slide {i} de mi carrusel",
            prompt=req.prompt,
            aspect_ratio=req.aspect_ratio,
            styles=req.styles,
            texto_overlay=f"Titulo slide {i}",
            metadata={"mi_metadata": "valor"},
        ))

    # Caption narrativo
    caption = f"Mi carrusel sobre {tema}"
    hashtags = self.studio.post.hashtags(["general", "campo"], municipio)
    return Carrusel(
        tema=f"Mi carrusel: {tema}",
        tipo="mi_nuevo_tipo", municipio=municipio,
        tono="emotivo",
        slides=slides, caption_narrativo=caption, hashtags=hashtags,
        metadata={"n_slides": n_slides},
    )
```

Y queda accesible como `factory.mi_nuevo_carrusel(...)`.

---

## Personalizar el CLI

Si queres agregar un subcomando nuevo al CLI de `studio.py`, agrega:

1. En la funcion `cli()`:

```python
# Definir el parser
p_mi = sub.add_parser("mi-comando", help="Mi nuevo comando")
p_mi.add_argument("--algo", required=True, help="...")

# Agregar el handler
elif args.comando == "mi-comando":
    studio.mi_metodo(args.algo)
```

2. En la clase `Studio`, agregar el metodo:

```python
def mi_metodo(self, algo: str) -> dict:
    """Doc."""
    return {"ok": True, "algo": algo}
```

---

## Crear un script custom

Podes crear un script en la raiz que use el estudio como libreria:

```python
#!/usr/bin/env python3
"""Mi script personalizado."""

from realestate_studio import RealestateStudio
from carruseles import CarruselFactory

studio = RealestateStudio()
factory = CarruselFactory(studio)

# Tu logica custom
for proyecto in ["chacra-canuelas-5ha", "country-pilar-ejemplo"]:
    post = studio.post.post_lote_venta(
        tema=f"Oferta en {proyecto}",
        municipio="Cañuelas",
        hectareas="5 ha",
        distancia_caba="65 km",
        tono="emotivo",
    )
    print(f"[{proyecto}] {post['caption'][:100]}...")
```

Guardo como `mi_script.py` en la raiz.

---

## Versionar tus cambios

Despues de hacer cambios:
```bash
git add .
git commit -m "feat: agregar template para pileta quinta"
git push
```

---

## Que sigue

- Volver al [indice](../MANUAL.md)
- Si algo falla, [TROUBLESHOOTING.md](../TROUBLESHOOTING.md) tiene los fixes
- Para ideas de mejora, revisar [09-limitaciones-y-workarounds.md](09-limitaciones-y-workarounds.md)