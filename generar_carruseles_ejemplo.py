"""
Genera los 4 tipos de carrusel como ejemplos completos en el proyecto
"chacra-canuelas-5ha" para tener material de demo y referencia visual.
"""
from pathlib import Path

from carruseles import CarruselFactory
from realestate_studio import RealestateStudio

ROOT = Path(__file__).resolve().parent
PROYECTO = "chacra-canuelas-5ha"


def main() -> None:
    studio = RealestateStudio()
    factory = CarruselFactory(studio)

    print("=" * 60)
    print(f"GENERANDO CARRUSELES EN: {PROYECTO}")
    print("=" * 60)

    # 1) Lote premium (6 slides)
    c1 = factory.lote_premium(
        tema="5 ha en Cañuelas, a 65 km de CABA",
        municipio="Cañuelas", hectareas=5,
        precio_usd="USD 60.000", distancia_caba="65 km",
        tono="emotivo", n_slides=6)
    r1 = factory.guardar(c1, "lote_premium", proyecto=PROYECTO)
    print(f"[1/4] lote_premium: {c1.n_slides} slides -> {r1.relative_to(ROOT)}")

    # 2) Country etapa (5 slides)
    c2 = factory.country_etapa(
        nombre_country="El Tala", municipio="Pilar",
        etapa="2", n_lotes=12,
        precio_desde="USD 85.000",
        distancia_caba="45 km",
        tono="premium", n_slides=5)
    r2 = factory.guardar(c2, "country_etapa", proyecto=PROYECTO)
    print(f"[2/4] country_etapa: {c2.n_slides} slides -> {r2.relative_to(ROOT)}")

    # 3) Obra avance (4 slides)
    c3 = factory.obra_avance(
        nombre_obra="Casa López", municipio="Escobar",
        semana=3, etapa="mampostería",
        estilo_render="casa moderna minimalista",
        hectareas=1, tono="practico", n_slides=4)
    r3 = factory.guardar(c3, "obra_avance", proyecto=PROYECTO)
    print(f"[3/4] obra_avance: {c3.n_slides} slides -> {r3.relative_to(ROOT)}")

    # 4) Servicios (8 slides, fijo)
    c4 = factory.servicios(
        empresa="Construcciones Pampeanas",
        municipio="Cañuelas", n_slides=6)
    r4 = factory.guardar(c4, "servicios", proyecto=PROYECTO,
                        vertical="servicios")
    print(f"[4/4] servicios: {c4.n_slides} slides -> {r4.relative_to(ROOT)}")

    print()
    print(f"Total: 4 carruseles · "
          f"{c1.n_slides + c2.n_slides + c3.n_slides + c4.n_slides} slides")


if __name__ == "__main__":
    main()
