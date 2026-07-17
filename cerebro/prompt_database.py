"""Base de datos de prompts en JSON estructurado.

Almacena prompts extraídos de videos con metadata rica para búsqueda
y filtrado por categoría, estilo, ubicación, etc.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any


# ============ Data Models ============

CATEGORIAS = [
    "terreno",
    "lote",
    "desarrollo",
    "construccion",
    "casa_terminada",
    "servicio",
    "vista_aerea",
    "render",
    "otro",
]

ESTILOS = [
    "campestre",
    "moderno",
    "rustico",
    "premium",
    "minimalista",
    "industrial",
    "colonial",
    "otro",
]

MOMENTOS_DIA = [
    "amanecer",
    "manana",
    "mediodia",
    "tarde",
    "atardecer",
    "noche",
    "blue_hour",
    "golden_hour",
]

ASPECT_RATIOS = {
    "post": "896*1152",
    "story": "768*1344",
    "square": "1024*1024",
    "landscape": "1152*896",
    "wide": "1344*768",
}

DEFAULT_NEGATIVE = (
    "blurry, low quality, distorted, deformed, watermark, text, logo, "
    "oversaturated, underexposed, overexposed, noise, grain, cartoon, "
    "drawing, painting, illustration, 3d render, unrealistic, "
    "modern skyscrapers in background, tropical vegetation, beach"
)

DEFAULT_STYLES = ["Fooocus V2", "Fooocus Enhance"]


@dataclass
class PromptEntry:
    """Un prompt almacenado en el cerebro."""

    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    prompt: str = ""
    negative_prompt: str = ""
    aspect_ratio: str = "896*1152"
    styles: list[str] = field(default_factory=lambda: DEFAULT_STYLES.copy())
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())

    # Campos de curación
    aprobado: bool = False
    rating: int = 0  # 0-5
    notas: str = ""
    tags: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> PromptEntry:
        valid_fields = {f.name for f in cls.__dataclass_fields__.values()}
        filtered = {k: v for k, v in d.items() if k in valid_fields}
        return cls(**filtered)

    @property
    def categoria(self) -> str:
        return self.metadata.get("categoria", "otro")

    @property
    def estilo(self) -> str:
        return self.metadata.get("estilo", "otro")

    @property
    def momento_dia(self) -> str:
        return self.metadata.get("momento_dia", "")

    @property
    def fuente(self) -> str:
        return self.metadata.get("fuente", "")

    @property
    def ubicacion(self) -> str:
        return self.metadata.get("ubicacion", "")


# ============ Database ============


class PromptDatabase:
    """Base de datos de prompts en JSON."""

    def __init__(self, db_path: Path | str | None = None):
        if db_path is None:
            db_path = Path(__file__).parent / "data" / "prompts.json"
        self.db_path = Path(db_path)
        self._prompts: dict[str, PromptEntry] = {}
        self._load()

    def _load(self) -> None:
        if not self.db_path.exists():
            return
        try:
            data = json.loads(self.db_path.read_text(encoding="utf-8"))
            for item in data.get("prompts", []):
                entry = PromptEntry.from_dict(item)
                self._prompts[entry.id] = entry
        except (json.JSONDecodeError, OSError):
            self._prompts = {}

    def _save(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "version": "1.0",
            "updated_at": datetime.now().isoformat(),
            "total": len(self._prompts),
            "prompts": [p.to_dict() for p in self._prompts.values()],
        }
        tmp = self.db_path.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        tmp.replace(self.db_path)

    def agregar(
        self,
        prompt: str,
        negative_prompt: str = "",
        aspect_ratio: str = "896*1152",
        styles: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
        tags: list[str] | None = None,
    ) -> PromptEntry:
        """Agrega un nuevo prompt a la base de datos."""
        entry = PromptEntry(
            prompt=prompt,
            negative_prompt=negative_prompt or DEFAULT_NEGATIVE,
            aspect_ratio=aspect_ratio,
            styles=styles or DEFAULT_STYLES.copy(),
            metadata=metadata or {},
            tags=tags or [],
        )
        self._prompts[entry.id] = entry
        self._save()
        return entry

    def obtener(self, id: str) -> PromptEntry | None:
        """Obtiene un prompt por ID."""
        return self._prompts.get(id)

    def actualizar(self, id: str, **kwargs: Any) -> PromptEntry | None:
        """Actualiza campos de un prompt."""
        entry = self._prompts.get(id)
        if not entry:
            return None
        for key, value in kwargs.items():
            if hasattr(entry, key):
                setattr(entry, key, value)
        entry.updated_at = datetime.now().isoformat()
        self._save()
        return entry

    def eliminar(self, id: str) -> bool:
        """Elimina un prompt."""
        if id in self._prompts:
            del self._prompts[id]
            self._save()
            return True
        return False

    def listar(self, limit: int = 100) -> list[PromptEntry]:
        """Lista todos los prompts ordenados por fecha."""
        items = sorted(self._prompts.values(), key=lambda p: p.created_at, reverse=True)
        return items[:limit]

    def buscar(
        self,
        categoria: str | None = None,
        estilo: str | None = None,
        momento_dia: str | None = None,
        ubicacion: str | None = None,
        aprobado: bool | None = None,
        min_rating: int = 0,
        tags: list[str] | None = None,
        texto: str | None = None,
        limit: int = 50,
    ) -> list[PromptEntry]:
        """Busca prompts con filtros."""
        results = list(self._prompts.values())

        if categoria:
            results = [p for p in results if p.categoria == categoria]
        if estilo:
            results = [p for p in results if p.estilo == estilo]
        if momento_dia:
            results = [p for p in results if p.momento_dia == momento_dia]
        if ubicacion:
            results = [p for p in results if ubicacion.lower() in p.ubicacion.lower()]
        if aprobado is not None:
            results = [p for p in results if p.aprobado == aprobado]
        if min_rating > 0:
            results = [p for p in results if p.rating >= min_rating]
        if tags:
            results = [
                p for p in results if any(t in p.tags for t in tags)
            ]
        if texto:
            texto_lower = texto.lower()
            results = [
                p for p in results
                if texto_lower in p.prompt.lower()
                or texto_lower in p.notas.lower()
                or any(texto_lower in t for t in p.tags)
            ]

        results.sort(key=lambda p: (p.rating, p.created_at), reverse=True)
        return results[:limit]

    def estadisticas(self) -> dict[str, Any]:
        """Devuelve estadísticas de la base de datos."""
        total = len(self._prompts)
        aprobados = sum(1 for p in self._prompts.values() if p.aprobado)
        ratings = [p.rating for p in self._prompts.values() if p.rating > 0]

        por_categoria = {}
        for p in self._prompts.values():
            cat = p.categoria
            por_categoria[cat] = por_categoria.get(cat, 0) + 1

        por_estilo = {}
        for p in self._prompts.values():
            est = p.estilo
            por_estilo[est] = por_estilo.get(est, 0) + 1

        return {
            "total": total,
            "aprobados": aprobados,
            "pendientes": total - aprobados,
            "rating_promedio": round(sum(ratings) / len(ratings), 1) if ratings else 0,
            "por_categoria": por_categoria,
            "por_estilo": por_estilo,
        }

    def exportar_aprobados(self, min_rating: int = 1) -> list[dict[str, Any]]:
        """Exporta prompts aprobados para usar en realestate_studio."""
        aprobados = [
            p for p in self._prompts.values()
            if p.aprobado and p.rating >= min_rating
        ]
        aprobados.sort(key=lambda p: p.rating, reverse=True)
        return [
            {
                "id": p.id,
                "prompt": p.prompt,
                "negative_prompt": p.negative_prompt,
                "aspect_ratio": p.aspect_ratio,
                "styles": p.styles,
                "categoria": p.categoria,
                "estilo": p.estilo,
                "rating": p.rating,
            }
            for p in aprobados
        ]

    def importar_desde_json(self, path: Path | str) -> int:
        """Importa prompts desde un archivo JSON externo."""
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        items = data if isinstance(data, list) else data.get("prompts", [])
        count = 0
        for item in items:
            entry = PromptEntry.from_dict(item)
            if not any(p.prompt == entry.prompt for p in self._prompts.values()):
                self._prompts[entry.id] = entry
                count += 1
        self._save()
        return count
