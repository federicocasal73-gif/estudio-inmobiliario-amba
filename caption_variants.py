"""
Generador de variantes de caption para A/B testing.

Genera N captions alternativos para un mismo post, utiles para testear
que tono / estilo funciona mejor con tu audiencia.

Uso:
    from caption_variants import CaptionVariants

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
    for i, v in enumerate(variantes, 1):
        print(f"--- Variante {i} ({v['tono']}) ---")
        print(v["caption_completo"])
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from realestate_studio import RealestateStudio

ROOT = Path(__file__).resolve().parent


@dataclass
class VarianteCaption:
    variante_id: str
    tipo: str
    tono: str
    nicho: list[str]
    tema: str
    caption: str
    hashtags: list[str]
    caption_completo: str
    metadata: dict[str, Any] = field(default_factory=dict)
    fecha_creacion: str = field(
        default_factory=lambda: datetime.now().isoformat(timespec="seconds")
    )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class CaptionVariants:
    """Genera N variantes de un mismo post."""

    def __init__(self, studio: RealestateStudio):
        self.studio = studio

    def generar(
        self,
        tipo: str,
        n: int = 3,
        tonos: list[str] | None = None,
        nichos: list[str] | None = None,
        municipio: str = "Cañuelas",
        **kwargs,
    ) -> list[VarianteCaption]:
        """Genera N variantes del mismo tipo de post con tonos distintos."""
        if tonos is None:
            tonos = self._tonos_por_tipo(tipo)[:n]
        if len(tonos) < n:
            tonos = tonos + [tonos[-1]] * (n - len(tonos))
        tonos = tonos[:n]

        nichos_por_variante = self._nichos_por_tipo(tipo) if nichos is None else nichos

        variantes: list[VarianteCaption] = []
        for i, tono in enumerate(tonos):
            nichos = (
                nichos_por_variante
                if isinstance(nichos_por_variante, list)
                else [nichos_por_variante]
            )
            try:
                post = self._generar_post(tipo, tono, municipio, nichos, **kwargs)
            except Exception as e:
                post = {
                    "caption": f"ERROR generando variante {i}: {e}",
                    "hashtags": [],
                    "caption_completo": f"ERROR: {e}",
                    "tema": kwargs.get("tema", tipo),
                }
            v = VarianteCaption(
                variante_id=f"v{i + 1}_{tono}",
                tipo=tipo,
                tono=tono,
                nicho=nichos,
                tema=post.get("tema", kwargs.get("tema", "")),
                caption=post.get("caption", ""),
                hashtags=post.get("hashtags", []),
                caption_completo=post.get("caption_completo", ""),
                metadata={
                    "kwargs": {k: v for k, v in kwargs.items() if isinstance(v, (str, int, float))},
                    "nicho": nichos,
                },
            )
            variantes.append(v)

        return variantes

    def _tonos_por_tipo(self, tipo: str) -> list[str]:
        """Devuelve los tonos disponibles para cada tipo de post."""
        return {
            "lote_venta": ["emotivo", "practico", "inversion", "premium"],
            "country": ["premium", "familia", "inversion"],
            "campo": ["inversion", "productor"],
            "preventa_loteo": ["oportunidad", "urgencia"],
            "lote_periurbano": ["practico"],
            "testimonial_cliente": ["emotivo", "profesional"],
            "preguntas_frecuentes": ["practico", "emotivo"],
            "campo_productivo": ["inversion"],
            "obra_avance_semanal": ["practico"],
            "reel_hook_corto": ["emotivo", "premium"],
        }.get(tipo, ["emotivo"])

    def _nichos_por_tipo(self, tipo: str) -> list[str]:
        """Devuelve nichos sugeridos para cada tipo."""
        return {
            "lote_venta": ["general", "campo", "inversion"],
            "country": ["country", "inversion"],
            "campo": ["campo", "inversion"],
            "preventa_loteo": ["general", "inversion"],
            "lote_periurbano": ["general"],
            "testimonial_cliente": ["casas", "construccion", "general"],
            "preguntas_frecuentes": ["general"],
            "campo_productivo": ["campo", "inversion", "lote_rentado"],
            "obra_avance_semanal": ["construccion", "casas"],
            "reel_hook_corto": ["general"],
        }.get(tipo, ["general"])

    def _generar_post(
        self, tipo: str, tono: str, municipio: str, nichos: list[str], **kwargs
    ) -> dict[str, Any]:
        """Llama al factory apropiado segun tipo."""
        factory_map = {
            "lote_venta": self.studio.post.post_lote_venta,
            "country": self.studio.post.post_country,
            "campo": self.studio.post.post_campo,
            "preventa_loteo": self.studio.post.post_preventa,
            "lote_periurbano": self.studio.post.post_lote_periurbano,
            "testimonial_cliente": self.studio.post.post_testimonial_cliente,
            "preguntas_frecuentes": self.studio.post.post_preguntas_frecuentes,
            "campo_productivo": self.studio.post.post_campo,
            "obra_avance_semanal": self.studio.post.post_obra_avance_semanal,
            "reel_hook_corto": self.studio.post.post_reel_hook,
        }
        factory = factory_map.get(tipo)
        if factory is None:
            raise ValueError(f"Tipo no soportado: {tipo}")

        # Preparar kwargs segun tipo
        call_kwargs = {"municipio": municipio, "tono": tono, "nichos": nichos}
        call_kwargs.update(kwargs)
        return factory(**call_kwargs)

    def guardar(
        self,
        variantes: list[VarianteCaption],
        nombre: str | None = None,
        proyecto: str | None = None,
    ) -> Path:
        """Guarda las variantes en JSON + un txt con todas para comparar."""
        if proyecto:
            carpeta = ROOT / "inmuebles" / "lotes" / proyecto / "variantes"
        else:
            carpeta = ROOT / "inmuebles" / "_variantes"
        carpeta.mkdir(parents=True, exist_ok=True)

        if not nombre:
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            tipo = variantes[0].tipo if variantes else "post"
            nombre = f"variantes_{tipo}_{ts}"

        # JSON con todas las variantes
        json_path = carpeta / f"{nombre}.json"
        data = {
            "tipo": variantes[0].tipo if variantes else "",
            "tema": variantes[0].tema if variantes else "",
            "n_variantes": len(variantes),
            "variantes": [v.to_dict() for v in variantes],
            "fecha": datetime.now().isoformat(timespec="seconds"),
        }
        json_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

        # TXT para comparar visualmente
        txt_path = carpeta / f"{nombre}.txt"
        lineas: list[str] = [
            f"# Variantes de {data['tipo']}: {data['tema']}",
            f"# {data['n_variantes']} variantes generadas",
            "",
        ]
        for v in variantes:
            lineas.append("=" * 60)
            lineas.append(f"VARIANTE {v.variante_id} (tono: {v.tono})")
            lineas.append("=" * 60)
            lineas.append(v.caption_completo)
            lineas.append("")
        txt_path.write_text("\n".join(lineas), encoding="utf-8")

        return carpeta

    def mejor_caption_para_publicar(
        self, variantes: list[VarianteCaption], criterios: dict[str, Any] | None = None
    ) -> VarianteCaption:
        """Elige la 'mejor' variante segun criterios simples.

        criterios disponibles:
          - tono_preferido: list de tonos ordenados por preferencia
          - max_caracteres: int, descarta las que excedan
          - nicho_preferido: str
        """
        criterios = criterios or {}
        candidatos = list(variantes)

        if "max_caracteres" in criterios:
            mx = criterios["max_caracteres"]
            candidatos = [v for v in candidatos if len(v.caption_completo) <= mx]

        if "tono_preferido" in criterios:
            tonos_orden = criterios["tono_preferido"]
            candidatos.sort(
                key=lambda v: tonos_orden.index(v.tono) if v.tono in tonos_orden else 999
            )

        if "nicho_preferido" in criterios:
            nicho = criterios["nicho_preferido"]
            candidatos.sort(key=lambda v: 0 if nicho in v.nicho else 1)

        return candidatos[0] if candidatos else variantes[0]


def demo() -> None:
    from realestate_studio import RealestateStudio

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

    print(f"Generadas {len(variantes)} variantes")
    for v in variantes:
        print(f"\n--- {v.variante_id} ({v.tono}) ---")
        print(v.caption_completo[:200] + "...")

    carpeta = cv.guardar(variantes, proyecto="chacra-canuelas-5ha")
    print(f"\nGuardado en: {carpeta.relative_to(ROOT)}")

    mejor = cv.mejor_caption_para_publicar(
        variantes, criterios={"tono_preferido": ["emotivo", "inversion"]}
    )
    print(f"\nMejor variante segun criterios: {mejor.variante_id}")


if __name__ == "__main__":
    demo()
