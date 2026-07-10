"""
Historial de publicaciones + rotacion inteligente de proyectos.

Guarda un JSON con todas las publicaciones hechas por el estudio, con:
  - fecha
  - tipo (lote_venta, country, campo, carrusel, etc)
  - proyecto
  - municipio
  - instagram_post_id (si se publico)

Esto permite que el calendario editorial evite publicar el mismo proyecto
dos veces en pocos dias, o priorice los que llevan mas tiempo sin
publicar.

Uso:
    from historial_publicaciones import HistorialPublicaciones, RotadorProyectos

    historial = HistorialPublicaciones()
    historial.registrar(
        tipo="lote_venta",
        proyecto="chacra-canuelas-5ha",
        municipio="Cañuelas",
    )

    rotador = RotadorProyectos(historial)
    orden = rotador.ordenar_por_antiguedad(
        ["chacra-canuelas-5ha", "country-pilar-ejemplo", "campo-brandsen-30ha"])
    # Devuelve los proyectos ordenados del menos reciente al mas reciente
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
HISTORIAL_PATH = ROOT / "inmuebles" / "_historial_publicaciones.json"


@dataclass
class Publicacion:
    fecha: str
    tipo: str
    proyecto: str | None
    municipio: str
    instagram_post_id: str | None = None
    permalink: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class HistorialPublicaciones:
    """Persistencia del historial de publicaciones."""

    def __init__(self, ruta: Path = HISTORIAL_PATH):
        self.ruta = ruta
        self._publicaciones: list[Publicacion] = []
        self._cargar()

    def _cargar(self) -> None:
        if not self.ruta.exists():
            return
        try:
            data = json.loads(self.ruta.read_text(encoding="utf-8"))
            self._publicaciones = [Publicacion(**p) for p in data.get("publicaciones", [])]
        except (json.JSONDecodeError, TypeError):
            self._publicaciones = []

    def _guardar(self) -> None:
        self.ruta.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "version": "1.0",
            "total": len(self._publicaciones),
            "ultima_actualizacion": datetime.now().isoformat(timespec="seconds"),
            "publicaciones": [p.to_dict() for p in self._publicaciones],
        }
        self.ruta.write_text(json.dumps(data, indent=2, ensure_ascii=False),
                             encoding="utf-8")

    def registrar(self, tipo: str, municipio: str,
                  proyecto: str | None = None,
                  instagram_post_id: str | None = None,
                  permalink: str | None = None,
                  metadata: dict[str, Any] | None = None) -> Publicacion:
        pub = Publicacion(
            fecha=datetime.now().isoformat(timespec="seconds"),
            tipo=tipo, municipio=municipio, proyecto=proyecto,
            instagram_post_id=instagram_post_id, permalink=permalink,
            metadata=metadata or {},
        )
        self._publicaciones.append(pub)
        self._guardar()
        return pub

    def publicaciones_de_proyecto(self, proyecto: str,
                                    limite_dias: int = 30) -> list[Publicacion]:
        """Devuelve las publicaciones de un proyecto en los ultimos N dias."""
        from datetime import timedelta
        cutoff = datetime.now() - timedelta(days=limite_dias)
        resultados = []
        for pub in self._publicaciones:
            if pub.proyecto != proyecto:
                continue
            try:
                fecha = datetime.fromisoformat(pub.fecha)
                if fecha >= cutoff:
                    resultados.append(pub)
            except ValueError:
                continue
        return resultados

    def ultima_publicacion_proyecto(self, proyecto: str) -> Publicacion | None:
        pubs = [p for p in self._publicaciones if p.proyecto == proyecto]
        if not pubs:
            return None
        return max(pubs, key=lambda p: p.fecha)

    def dias_desde_ultima(self, proyecto: str) -> int | None:
        ultima = self.ultima_publicacion_proyecto(proyecto)
        if ultima is None:
            return None
        try:
            fecha = datetime.fromisoformat(ultima.fecha)
            return (datetime.now() - fecha).days
        except ValueError:
            return None

    def limpiar(self) -> None:
        self._publicaciones = []
        self._guardar()

    def todas(self) -> list[Publicacion]:
        return list(self._publicaciones)


class RotadorProyectos:
    """Logica de rotacion inteligente de proyectos para el calendario."""

    def __init__(self, historial: HistorialPublicaciones | None = None):
        self.historial = historial or HistorialPublicaciones()

    def ordenar_por_antiguedad(self, proyectos: list[str]) -> list[str]:
        """Ordena los proyectos por antiguedad de ultima publicacion.

        Los que llevan mas tiempo sin publicar van primero.
        Si nunca se publicaron, van al principio.
        """
        def key(proyecto: str) -> tuple[int, int, str]:
            dias = self.historial.dias_desde_ultima(proyecto)
            # None (nunca publicado) -> 0 (va primero al ser menor)
            # False (publicado) -> 1 (va despues)
            # Truco: dias = -1 si nunca publicado (asi -dias = 1, maximo)
            dias_val = dias if dias is not None else 99999
            return (1 if dias is not None else 0, -dias_val, proyecto)

        return sorted(proyectos, key=key, reverse=False)

    def proyectos_disponibles_esta_semana(self, proyectos: list[str],
                                          dias_minimos_entre_posts: int = 3
                                          ) -> list[str]:
        """Filtra proyectos que aun no deberian ser publicados esta semana."""
        disponibles = []
        for p in proyectos:
            dias = self.historial.dias_desde_ultima(p)
            if dias is None or dias >= dias_minimos_entre_posts:
                disponibles.append(p)
        return disponibles

    def sugerir_proyecto_para_slot(self, proyectos: list[str],
                                    tipo_post: str | None = None) -> str | None:
        """Sugiere el mejor proyecto para un slot dado."""
        if not proyectos:
            return None
        if tipo_post == "country":
            disponibles = [p for p in proyectos if "country" in p.lower()]
            candidatos = disponibles or proyectos
        elif tipo_post == "campo":
            disponibles = [p for p in proyectos if "campo" in p.lower()]
            candidatos = disponibles or proyectos
        else:
            candidatos = proyectos
        ordenados = self.ordenar_por_antiguedad(candidatos)
        return ordenados[0] if ordenados else None

    def resumen_rotacion(self, proyectos: list[str]) -> dict[str, Any]:
        """Devuelve un resumen del estado de rotacion."""
        resumen: dict[str, Any] = {}
        for p in proyectos:
            dias = self.historial.dias_desde_ultima(p)
            pubs = self.historial.publicaciones_de_proyecto(p, limite_dias=30)
            resumen[p] = {
                "dias_desde_ultima": dias,
                "publicaciones_ultimo_mes": len(pubs),
            }
        return resumen


def demo() -> None:
    historial = HistorialPublicaciones()
    historial.limpiar()

    # Registrar algunas publicaciones
    historial.registrar("lote_venta", "Cañuelas", proyecto="chacra-canuelas-5ha")
    historial.registrar("country", "Pilar", proyecto="country-pilar-ejemplo")

    proyectos = ["chacra-canuelas-5ha", "country-pilar-ejemplo",
                 "campo-brandsen-30ha"]

    rotador = RotadorProyectos(historial)
    orden = rotador.ordenar_por_antiguedad(proyectos)
    print("Orden por antiguedad:")
    for p in orden:
        print(f"  - {p} (dias desde ultima: "
              f"{rotador.historial.dias_desde_ultima(p)})")

    sugerido = rotador.sugerir_proyecto_para_slot(proyectos, "country")
    print(f"\nSugerido para slot country: {sugerido}")

    resumen = rotador.resumen_rotacion(proyectos)
    print(f"\nResumen: {resumen}")


if __name__ == "__main__":
    demo()