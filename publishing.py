"""Pipeline de publicacion: scheduler, monitor, DM templates.

Componentes:
  - Scheduler: cola persistente de publicaciones programadas (JSON).
              Procesa items cuya fecha ya paso.
  - Monitor:   lee insights de Instagram Graph API, guarda en historial,
              genera reporte semanal (engagement por post).
  - DMTemplates: templates de respuesta a DMs frecuentes. Matching por
                 keywords. Listos para usar con ManyChat u otra herramienta.

Sin dependencias externas nuevas (solo stdlib + requests/urllib).

Setup de Meta Graph API:
  - Crear app en developers.facebook.com
  - Solicitar instagram_basic + instagram_content_publish + pages_show_list
  - Generar access token de 60 dias
  - Guardar en config/user.yaml (ver app_config.py)
"""

from __future__ import annotations

import json
import re
import sqlite3
import threading
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from app_config import get_config
from app_logging import get_logger

log = get_logger("studio.publishing")

DEFAULT_SCHEDULE_PATH = Path(".cache") / "scheduled_publications.json"
DEFAULT_INSIGHTS_PATH = Path(".cache") / "ig_insights.json"
DEFAULT_DB_PATH = Path(".cache") / "dm_history.db"

GRAPH_API_VERSION = "v19.0"
GRAPH_API_BASE = f"https://graph.facebook.com/{GRAPH_API_VERSION}"


# ============== SCHEDULER ==============


@dataclass
class ScheduledPost:
    """Un post programado para publicarse en el futuro."""

    id: str
    carrusel_path: str
    caption: str
    hashtags: list[str] = field(default_factory=list)
    scheduled_at: str = ""  # ISO 8601
    mode: str = "real"  # "dry-run" | "interactivo" | "real"
    status: str = "pending"  # pending | published | error | cancelled
    attempts: int = 0
    last_error: str | None = None
    published_at: str | None = None
    instagram_post_id: str | None = None
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class Scheduler:
    """Cola persistente de publicaciones programadas.

    Persistencia en JSON (atomic write). Thread-safe.
    """

    def __init__(self, schedule_path: Path = DEFAULT_SCHEDULE_PATH):
        self.schedule_path = schedule_path
        self._lock = threading.Lock()
        self._items: dict[str, ScheduledPost] = {}
        self._load()

    def _load(self) -> None:
        if not self.schedule_path.exists():
            return
        try:
            data = json.loads(self.schedule_path.read_text(encoding="utf-8"))
            items = data.get("items", [])
            self._items = {it["id"]: ScheduledPost(**it) for it in items}
            log.info(f"Scheduler cargados: {len(self._items)} posts")
        except (json.JSONDecodeError, KeyError, OSError) as e:
            log.warning(f"No pude cargar scheduler: {e}")
            self._items = {}

    def _save(self) -> None:
        try:
            self.schedule_path.parent.mkdir(parents=True, exist_ok=True)
            data = {
                "version": 1,
                "saved_at": datetime.now().isoformat(),
                "items": [it.to_dict() for it in self._items.values()],
            }
            tmp = self.schedule_path.with_suffix(".tmp")
            tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
            tmp.replace(self.schedule_path)
        except OSError as e:
            log.warning(f"No pude guardar scheduler: {e}")

    def programar(
        self,
        id: str,  # noqa: A002
        carrusel_path: str | Path,
        caption: str,
        hashtags: list[str],
        scheduled_at: str | datetime,
        mode: str = "real",
    ) -> ScheduledPost:
        """Programa un post para una fecha futura."""
        if isinstance(scheduled_at, datetime):
            scheduled_at = scheduled_at.isoformat()

        item = ScheduledPost(
            id=id,
            carrusel_path=str(Path(carrusel_path).resolve()),
            caption=caption,
            hashtags=hashtags,
            scheduled_at=scheduled_at,
            mode=mode,
        )
        with self._lock:
            self._items[id] = item
            self._save()
        log.info(f"Post programado: {id} para {scheduled_at}")
        return item

    def cancelar(self, id: str) -> bool:  # noqa: A002
        with self._lock:
            if id in self._items:
                self._items[id].status = "cancelled"
                self._save()
                log.info(f"Post cancelado: {id}")
                return True
        return False

    def eliminar(self, id: str) -> bool:  # noqa: A002
        with self._lock:
            if id in self._items:
                del self._items[id]
                self._save()
                return True
        return False

    def listar(self, status: str | None = None) -> list[ScheduledPost]:
        with self._lock:
            items = list(self._items.values())
        if status:
            items = [it for it in items if it.status == status]
        return sorted(items, key=lambda it: it.scheduled_at)

    def pendientes_a_procesar(self, ahora: datetime | None = None) -> list[ScheduledPost]:
        """Devuelve items cuya fecha ya paso y siguen pending."""
        ahora = ahora or datetime.now()
        result = []
        for it in self.listar(status="pending"):
            try:
                fecha = datetime.fromisoformat(it.scheduled_at)
                if fecha <= ahora:
                    result.append(it)
            except ValueError:
                continue
        return result

    def marcar_publicado(
        self,
        id: str,  # noqa: A002
        instagram_post_id: str | None = None,
    ) -> None:
        with self._lock:
            if id in self._items:
                self._items[id].status = "published"
                self._items[id].published_at = datetime.now().isoformat()
                self._items[id].instagram_post_id = instagram_post_id
                self._save()

    def marcar_error(self, id: str, error: str) -> None:  # noqa: A002
        with self._lock:
            if id in self._items:
                self._items[id].attempts += 1
                self._items[id].last_error = error
                if self._items[id].attempts >= 3:
                    self._items[id].status = "error"
                self._save()

    def stats(self) -> dict[str, int]:
        with self._lock:
            items = list(self._items.values())
        return {
            status: sum(1 for it in items if it.status == status)
            for status in {"pending", "published", "error", "cancelled"}
        }


# ============== MONITOR ==============


@dataclass
class PostInsights:
    """Insights de un post publicados en Instagram."""

    post_id: str  # instagram_post_id
    permalink: str
    timestamp: str  # cuando se leyo
    impressions: int = 0
    reach: int = 0
    likes: int = 0
    comments: int = 0
    saves: int = 0
    shares: int = 0
    engagement_rate: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> PostInsights:
        return cls(**d)


class InstagramInsightsClient:
    """Cliente para Instagram Graph API (insights + cuenta)."""

    def __init__(self, access_token: str, instagram_user_id: str):
        self.access_token = access_token
        self.instagram_user_id = instagram_user_id

    def _request(self, endpoint: str, params: dict | None = None) -> dict:
        url = f"{GRAPH_API_BASE}/{endpoint}"
        params = params or {}
        params["access_token"] = self.access_token
        url += "?" + urllib.parse.urlencode(params)
        try:
            with urllib.request.urlopen(url, timeout=15) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except (urllib.error.URLError, urllib.error.HTTPError) as e:
            raise RuntimeError(f"Graph API error: {e}") from e

    def get_account_info(self) -> dict[str, Any]:
        """Devuelve info basica de la cuenta."""
        return self._request(
            self.instagram_user_id,
            {"fields": "id,username,name,followers_count,media_count"},
        )

    def get_media_list(self, limit: int = 25) -> list[dict[str, Any]]:
        """Devuelve los ultimos N posts."""
        data = self._request(
            f"{self.instagram_user_id}/media",
            {
                "fields": "id,permalink,caption,media_type,timestamp,like_count,comments_count",
                "limit": str(limit),
            },
        )
        return data.get("data", [])

    def get_insights(self, media_id: str) -> dict[str, Any]:
        """Insights de un post especifico."""
        return self._request(
            f"{media_id}/insights",
            {"metric": "impressions,reach,saved,shares"},
        )


class Monitor:
    """Lee insights de IG y los guarda en historial JSON. Genera reportes."""

    def __init__(
        self,
        insights_path: Path = DEFAULT_INSIGHTS_PATH,
        client: InstagramInsightsClient | None = None,
    ):
        self.insights_path = insights_path
        self._client = client
        self._insights: dict[str, PostInsights] = {}
        self._lock = threading.Lock()
        self._load()

    def set_client(self, client: InstagramInsightsClient) -> None:
        self._client = client

    def _load(self) -> None:
        if not self.insights_path.exists():
            return
        try:
            data = json.loads(self.insights_path.read_text(encoding="utf-8"))
            self._insights = {
                k: PostInsights.from_dict(v) for k, v in data.get("insights", {}).items()
            }
            log.info(f"Insights cargados: {len(self._insights)} posts")
        except (json.JSONDecodeError, OSError) as e:
            log.warning(f"No pude cargar insights: {e}")

    def _save(self) -> None:
        try:
            self.insights_path.parent.mkdir(parents=True, exist_ok=True)
            data = {
                "version": 1,
                "saved_at": datetime.now().isoformat(),
                "insights": {k: v.to_dict() for k, v in self._insights.items()},
            }
            tmp = self.insights_path.with_suffix(".tmp")
            tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
            tmp.replace(self.insights_path)
        except OSError as e:
            log.warning(f"No pude guardar insights: {e}")

    def fetch_and_store(self, post_id: str, permalink: str = "") -> PostInsights | None:
        """Lee insights de IG para un post y los guarda."""
        if not self._client:
            log.warning("Monitor sin cliente de IG, no puedo leer insights")
            return None

        try:
            insights_raw = self._client.get_insights(post_id)
            likes = 0
            comments = 0
            saves = 0
            shares = 0
            impressions = 0
            reach = 0
            for entry in insights_raw.get("data", []):
                metric = entry.get("name", "")
                value = entry.get("values", [{}])[0].get("value", 0)
                if metric == "impressions":
                    impressions = value
                elif metric == "reach":
                    reach = value
                elif metric == "saved":
                    saves = value
                elif metric == "shares":
                    shares = value
            # Para likes y comments, usamos media_list porque insights no los incluye
            media_data = self._client.get_media_list(limit=50)
            for m in media_data.get("data", []):
                if m.get("id") == post_id:
                    likes = m.get("like_count", 0)
                    comments = m.get("comments_count", 0)
                    break

            engagement_rate = 0.0
            if impressions > 0:
                engagement_rate = round((likes + comments + saves + shares) / impressions * 100, 2)

            insights = PostInsights(
                post_id=post_id,
                permalink=permalink,
                timestamp=datetime.now().isoformat(),
                impressions=impressions,
                reach=reach,
                likes=likes,
                comments=comments,
                saves=saves,
                shares=shares,
                engagement_rate=engagement_rate,
            )
            with self._lock:
                self._insights[post_id] = insights
                self._save()
            log.info(f"Insights guardados: {post_id} (engagement {engagement_rate}%)")
            return insights
        except Exception as e:
            log.warning(f"Error leyendo insights de {post_id}: {e}")
            return None

    def weekly_report(self, days: int = 7) -> dict[str, Any]:
        """Genera reporte agregado de los ultimos N dias."""
        cutoff = datetime.now() - timedelta(days=days)
        recent = []
        with self._lock:
            for ins in self._insights.values():
                try:
                    ts = datetime.fromisoformat(ins.timestamp)
                    if ts >= cutoff:
                        recent.append(ins)
                except ValueError:
                    continue

        if not recent:
            return {
                "periodo_dias": days,
                "posts_analizados": 0,
                "impresiones_totales": 0,
                "engagement_promedio": 0.0,
                "top_posts": [],
                "mejor_tipo_contenido": None,
            }

        total_impressions = sum(i.impressions for i in recent)
        avg_engagement = sum(i.engagement_rate for i in recent) / len(recent)
        top = sorted(recent, key=lambda i: i.engagement_rate, reverse=True)[:3]

        return {
            "periodo_dias": days,
            "posts_analizados": len(recent),
            "impresiones_totales": total_impressions,
            "alcance_total": sum(i.reach for i in recent),
            "engagement_promedio": round(avg_engagement, 2),
            "total_likes": sum(i.likes for i in recent),
            "total_comments": sum(i.comments for i in recent),
            "total_saves": sum(i.saves for i in recent),
            "top_posts": [
                {
                    "post_id": i.post_id,
                    "permalink": i.permalink,
                    "engagement_rate": i.engagement_rate,
                    "likes": i.likes,
                    "comments": i.comments,
                    "saves": i.saves,
                    "shares": i.shares,
                }
                for i in top
            ],
        }

    def render_markdown(self, report: dict[str, Any]) -> str:
        """Renderiza el reporte semanal como Markdown."""
        lines = [
            f"# Reporte semanal de Instagram ({report['periodo_dias']} dias)",
            "",
            f"**Posts analizados:** {report['posts_analizados']}",
            f"**Impresiones totales:** {report['impresiones_totales']:,}",
            f"**Alcance total:** {report.get('alcance_total', 0):,}",
            f"**Engagement promedio:** {report['engagement_promedio']}%",
            "",
            "## Engagement",
            f"- Likes: {report.get('total_likes', 0):,}",
            f"- Comentarios: {report.get('total_comments', 0):,}",
            f"- Saves: {report.get('total_saves', 0):,}",
            "",
            "## Top 3 posts por engagement",
            "",
        ]
        if report["top_posts"]:
            for i, p in enumerate(report["top_posts"], 1):
                lines.append(f"### {i}. {p['permalink'] or p['post_id']}")
                lines.append(f"- Engagement: **{p['engagement_rate']}%**")
                lines.append(
                    f"- Likes: {p['likes']}, "
                    f"Comentarios: {p['comments']}, "
                    f"Saves: {p['saves']}, "
                    f"Shares: {p['shares']}"
                )
                lines.append("")
        else:
            lines.append("Sin posts analizados en este periodo.")
            lines.append("")
        return "\n".join(lines)


# ============== DM TEMPLATES ==============


@dataclass
class DMTemplate:
    """Template de respuesta automatica a un DM."""

    id: str
    keywords: list[str]
    title: str
    body: str
    requires_data: list[str] = field(default_factory=list)
    priority: int = 5  # 1 (alta) a 10 (baja)

    def matches(self, message: str) -> bool:
        """True si el mensaje del cliente contiene alguna keyword."""
        msg_lower = message.lower()
        return any(kw.lower() in msg_lower for kw in self.keywords)

    def render(self, data: dict[str, Any] | None = None) -> str:
        """Renderiza el template con variables del dict data."""
        data = data or {}
        try:
            return self.body.format(**data)
        except KeyError as e:
            return f"{self.body}\n\n[Falta variable: {e}]"


class DMTemplates:
    """Coleccion de templates para DMs frecuentes."""

    TEMPLATES = [
        DMTemplate(
            id="precio",
            keywords=["precio", "cuanto", "vale", "cuesta", "costo"],
            title="Consulta de precio",
            body=(
                "Hola! Gracias por tu interes en {lote_nombre} 😊\n\n"
                "El precio es de {precio}. Aceptamos:\n"
                "• Pago al contado (5% descuento)\n"
                "• Financiacion en {cuotas} cuotas\n\n"
                "Te interesa agendar una visita?"
            ),
            requires_data=["lote_nombre", "precio", "cuotas"],
            priority=2,
        ),
        DMTemplate(
            id="ubicacion",
            keywords=["donde", "ubicado", "ubicacion", "direccion", "lugar"],
            title="Consulta de ubicacion",
            body=(
                "Hola! El lote esta en {municipio}, Buenos Aires. "
                "A {distancia_caba} de CABA.\n\n"
                "Te paso la ubicacion exacta por este medio. "
                "Queres coordinar una visita?"
            ),
            requires_data=["municipio", "distancia_caba"],
            priority=3,
        ),
        DMTemplate(
            id="financiacion",
            keywords=["financiacion", "cuotas", "credito", "hipoteca", "pago"],
            title="Consulta de financiacion",
            body=(
                "Hola! Si, tenemos opciones de financiacion:\n"
                "• Hasta {cuotas_max} cuotas\n"
                "• Anticipo del {anticipo_pct}%\n"
                "• Ajustable por indice o fijo en pesos\n\n"
                "Queres que te llame un asesor para explicarte mejor?"
            ),
            requires_data=["cuotas_max", "anticipo_pct"],
            priority=3,
        ),
        DMTemplate(
            id="visita",
            keywords=["visita", "ver", "conocer", "conocerlo", "ir"],
            title="Solicitud de visita",
            body=(
                "Genial! Coordinamos una visita esta semana?\n\n"
                "Tenemos disponibilidad:\n"
                "• Sabado por la manana\n"
                "• Domingo por la tarde\n\n"
                "Que dia te queda mejor?"
            ),
            priority=4,
        ),
        DMTemplate(
            id="mas_info",
            keywords=["info", "informacion", "mas", "detalles", "datos"],
            title="Mas informacion",
            body=(
                "Te cuento mas sobre {lote_nombre}:\n"
                "• {hectareas}\n"
                "• Servicios: {servicios}\n"
                "• A {distancia_caba} de CABA\n\n"
                "Queres ver fotos, planos o un render?"
            ),
            requires_data=["lote_nombre", "hectareas", "servicios", "distancia_caba"],
            priority=5,
        ),
        DMTemplate(
            id="gracias",
            keywords=["gracias", "genial", "perfecto", "buenisimo", "ok"],
            title="Agradecimiento",
            body=("Gracias a vos! Si surge alguna otra duda, escribime sin problema. Saludos! 👋"),
            priority=8,
        ),
    ]

    def __init__(self, db_path: Path = DEFAULT_DB_PATH):
        self.db_path = db_path
        self._init_db()

    def _init_db(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS dm_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    cliente TEXT NOT NULL,
                    mensaje TEXT NOT NULL,
                    template_id TEXT,
                    respuesta TEXT,
                    timestamp TEXT NOT NULL,
                    respondido INTEGER DEFAULT 0
                )
            """)
            conn.commit()

    def match(self, message: str) -> DMTemplate | None:
        """Devuelve el template que mejor matchea el mensaje."""
        candidatos = [t for t in self.TEMPLATES if t.matches(message)]
        if not candidatos:
            return None
        # Ordenar por prioridad (menor = mas alta)
        return sorted(candidatos, key=lambda t: t.priority)[0]

    def responder(
        self, cliente: str, mensaje: str, data: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Encuentra el template apropiado, lo renderiza, y guarda el historial."""
        template = self.match(mensaje)
        if template is None:
            respuesta = (
                "Gracias por tu mensaje. Te respondemos a la brevedad. "
                "Si es urgente, escribinos al whatsapp."
            )
            template_id = None
        else:
            respuesta = template.render(data)
            template_id = template.id

        with sqlite3.connect(str(self.db_path)) as conn:
            conn.execute(
                "INSERT INTO dm_history (cliente, mensaje, template_id, "
                "respuesta, timestamp, respondido) VALUES (?, ?, ?, ?, ?, ?)",
                (
                    cliente,
                    mensaje,
                    template_id,
                    respuesta,
                    datetime.now().isoformat(),
                    1 if template_id else 0,
                ),
            )
            conn.commit()

        log.info(f"DM respondido a {cliente} (template={template_id or 'ninguno'})")
        return {
            "cliente": cliente,
            "mensaje": mensaje,
            "template_id": template_id,
            "respuesta": respuesta,
            "timestamp": datetime.now().isoformat(),
        }

    def history(self, limit: int = 100) -> list[dict[str, Any]]:
        """Devuelve el historial de respuestas."""
        with sqlite3.connect(str(self.db_path)) as conn:
            rows = conn.execute(
                "SELECT cliente, mensaje, template_id, respuesta, timestamp, "
                "respondido FROM dm_history ORDER BY id DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [
            {
                "cliente": r[0],
                "mensaje": r[1],
                "template_id": r[2],
                "respuesta": r[3],
                "timestamp": r[4],
                "respondido": bool(r[5]),
            }
            for r in rows
        ]

    def listar_templates(self) -> list[DMTemplate]:
        """Devuelve todos los templates."""
        return sorted(self.TEMPLATES, key=lambda t: (t.priority, t.id))


# ============== WORKER DE SCHEDULER ==============


def procesar_programadas(
    scheduler: Scheduler, publisher_factory: Callable | None = None
) -> dict[str, Any]:
    """Procesa items pendientes y las publica.

    publisher_factory: callable que toma (carrusel_path, mode) y devuelve
    un PublicacionResultado. Default usa instagram_publisher.
    """
    from instagram_auth import InstagramAuth
    from instagram_publisher import InstagramPublisher, ModoPublicacion

    items = scheduler.pendientes_a_procesar()
    if not items:
        return {"procesados": 0, "publicados": 0, "errores": 0}

    publicados = 0
    errores = 0
    if publisher_factory is None:
        # Default: usa instagram_publisher
        try:
            publisher = InstagramPublisher(InstagramAuth())
        except Exception as e:
            log.warning(f"No pude crear publisher, saltando: {e}")
            publisher = None

        def factory(carrusel_path, mode):
            if publisher is None:
                return None
            return publisher.publicar_carrusel_existente(carrusel_path, ModoPublicacion(mode))

    for item in items:
        log.info(f"Procesando programado: {item.id} ({item.scheduled_at})")
        try:
            resultado = publisher_factory(item.carrusel_path, item.mode)
            if resultado is None:
                scheduler.marcar_error(item.id, "publisher no disponible")
                errores += 1
            elif getattr(resultado, "exito", False):
                scheduler.marcar_publicado(item.id, getattr(resultado, "instagram_post_id", None))
                publicados += 1
            else:
                scheduler.marcar_error(item.id, getattr(resultado, "error", "unknown"))
                errores += 1
        except Exception as e:
            scheduler.marcar_error(item.id, str(e))
            errores += 1

    return {"procesados": len(items), "publicados": publicados, "errores": errores}
