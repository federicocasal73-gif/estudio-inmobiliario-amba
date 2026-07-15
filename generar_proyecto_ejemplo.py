"""
Genera el proyecto ejemplo completo: Chacra 5 ha en Canuelas.
Crea:
  - 6 prompts visuales (atmosfera, lote, render, vista aerea, etc.)
  - 3 posts de Instagram (venta emotivo, inversion, preventa)
"""

import json
from pathlib import Path

from realestate_studio import RealestateStudio

ROOT = Path(__file__).resolve().parent
PROYECTO = "chacra-canuelas-5ha"
MUNICIPIO = "Cañuelas"


def main() -> None:
    studio = RealestateStudio()
    proyecto_dir = ROOT / "inmuebles" / "lotes" / PROYECTO
    prompts_dir = proyecto_dir / "prompts"
    posts_dir = proyecto_dir / "posts"
    prompts_dir.mkdir(parents=True, exist_ok=True)
    posts_dir.mkdir(parents=True, exist_ok=True)

    # ----- 1) Prompts visuales del lote -----
    prompts = {
        "01_chacra_atardecer": studio.lotes.chacra_pampeana(
            hectareas=5, municipio=MUNICIPIO, momento="atardecer"
        ),
        "02_vista_aerea_loteo": studio.lotes.vista_aerea_loteo(n_lotes=24, municipio=MUNICIPIO),
        "03_amanecer_pampa": studio.lotes.amanecer_pampa(municipio=MUNICIPIO),
        "04_tranquera_entrada": studio.lotes.tranquera_argentina(municipio=MUNICIPIO),
        "05_molino_tanque": studio.lotes.molino_tanque_australiano(municipio="Roque Pérez"),
        "06_render_proyecto": studio.construccion.render_proyecto(
            estilo="casa de campo tradicional argentina con galería",
            hectareas=5,
            municipio=MUNICIPIO,
        ),
    }
    for nombre, req in prompts.items():
        ruta = studio.guardar_prompt(req, nombre, subcarpeta=f"lotes/{PROYECTO}/prompts")
        print(f"[prompt] {nombre}: {ruta.name}")

    # ----- 2) Posts de Instagram -----
    posts = {
        "post_01_venta_emotivo": studio.post.post_lote_venta(
            tema="5 ha en Cañuelas, a 65 km de CABA",
            municipio=MUNICIPIO,
            hectareas="5 hectáreas",
            distancia_caba="65 km",
            servicios_disponibles=(
                "luz eléctrica, alambrado perimetral nuevo, calle de tierra mejorada, "
                "molino y tanque australiano funcionando"
            ),
            tono="emotivo",
            nichos=["general", "campo", "inversion"],
        ),
        "post_02_inversion": studio.post.post_lote_venta(
            tema="5 ha en Cañuelas — oportunidad de inversión",
            municipio=MUNICIPIO,
            hectareas="5 hectáreas",
            distancia_caba="65 km",
            servicios_disponibles="todos los servicios rurales",
            tono="inversion",
            nichos=["inversion", "campo"],
        ),
        "post_03_premium": studio.post.post_lote_venta(
            tema="5 ha en Cañuelas — última disponible",
            municipio=MUNICIPIO,
            hectareas="5 hectáreas",
            distancia_caba="65 km",
            servicios_disponibles="alambrado perimetral, casa de casero, galpón",
            tono="premium",
            nichos=["country", "inversion"],
        ),
    }
    for nombre, post in posts.items():
        ruta = studio.guardar_post(post, nombre, proyecto=PROYECTO)
        print(f"[post]   {nombre}: {ruta.name}")

    # ----- 3) Resumen del proyecto -----
    resumen = {
        "proyecto": PROYECTO,
        "municipio": MUNICIPIO,
        "ubicacion": "Cañuelas, Buenos Aires",
        "distancia_caba_km": 65,
        "hectareas": 5,
        "precio_referencia_usd": "USD 12.000/ha",
        "total_estimado_usd": "USD 60.000",
        "servicios_incluidos": [
            "luz eléctrica",
            "alambrado perimetral nuevo (7 hilos)",
            "calle de tierra mejorada (400 m)",
            "molino y tanque australiano",
            "tranquera de madera",
        ],
        "prompts_generados": list(prompts.keys()),
        "posts_generados": list(posts.keys()),
        "carpeta": str(proyecto_dir.relative_to(ROOT)),
    }
    ruta_resumen = proyecto_dir / "resumen.json"
    ruta_resumen.write_text(json.dumps(resumen, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\n[resumen] {ruta_resumen.name}")
    print(f"\nProyecto completo en: {proyecto_dir.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
