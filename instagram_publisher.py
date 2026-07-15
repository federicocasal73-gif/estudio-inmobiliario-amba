"""
Publicador de Instagram via Graph API.

Soporta 3 modos:
  - dry-run: muestra que publicaria pero no hace nada (default)
  - interactivo: muestra preview, pide confirmacion
  - real: publica de una

Uso:
    from instagram_auth import InstagramAuth
    from instagram_publisher import InstagramPublisher, ModoPublicacion

    auth = InstagramAuth()
    publisher = InstagramPublisher(auth)

    publisher.publicar_foto(
        ruta_imagen="imagen.jpg",
        caption="...",
        hashtags=[...],
        modo=ModoPublicacion.DRY_RUN,
    )
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

from cloudinary_upload import CloudinaryUploader
from instagram_auth import InstagramAuth

GRAPH_API_VERSION = "v19.0"
GRAPH_API_BASE = f"https://graph.facebook.com/{GRAPH_API_VERSION}"

ROOT = Path(__file__).resolve().parent
LOG_DIR = ROOT / "inmuebles" / "posts"
LOG_DIR.mkdir(parents=True, exist_ok=True)


class ModoPublicacion(Enum):
    DRY_RUN = "dry-run"
    INTERACTIVO = "interactivo"
    REAL = "real"


@dataclass
class PublicacionResultado:
    modo: str
    exito: bool
    tipo: str  # "foto" | "carrusel"
    caption_length: int
    n_imagenes: int
    media_ids: list[str] = field(default_factory=list)
    instagram_post_id: str | None = None
    permalink: str | None = None
    error: str | None = None
    fecha: str = field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class InstagramPublisher:
    """Wrapper para publicar fotos y carruseles en Instagram via Graph API."""

    def __init__(self, auth: InstagramAuth, uploader: CloudinaryUploader | None = None):
        self.auth = auth
        self.uploader = uploader or CloudinaryUploader(auth)

    def _request(
        self,
        endpoint: str,
        method: str = "GET",
        params: dict | None = None,
        json_body: dict | None = None,
    ) -> dict:
        """Hace un request a la Graph API."""
        if not self.auth.data:
            raise RuntimeError("auth.json no configurado")

        url = f"{GRAPH_API_BASE}/{endpoint}"

        if method == "GET":
            if params is None:
                params = {}
            params["access_token"] = self.auth.data.access_token
            url += "?" + urllib.parse.urlencode(params)
            req = urllib.request.Request(url, method="GET")
        else:
            # POST: access_token viaja en el body JSON (lo inyecta el caller)
            body = json.dumps(json_body or {}).encode("utf-8")
            req = urllib.request.Request(url, data=body, method="POST")
            req.add_header("Content-Type", "application/json")

        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="replace")
            try:
                err = json.loads(body)
            except json.JSONDecodeError:
                err = {"raw": body}
            # Sanitizar: remover access_token del mensaje de error
            if isinstance(err, dict):
                err.pop("access_token", None)
            raise RuntimeError(f"Graph API error {e.code}: {err}")

    def _check_public_url(self, url: str) -> bool:
        """Verifica que una URL sea accesible publicamente (requerido por IG)."""
        try:
            req = urllib.request.Request(url, method="HEAD")
            with urllib.request.urlopen(req, timeout=10) as resp:
                return resp.status == 200
        except Exception:
            return False

    # ---------------- Publicar foto ----------------

    def publicar_foto(
        self,
        ruta_imagen: str | Path,
        caption: str,
        hashtags: list[str] | None = None,
        modo: ModoPublicacion = ModoPublicacion.DRY_RUN,
    ) -> PublicacionResultado:
        ruta_imagen = Path(ruta_imagen)
        if not ruta_imagen.exists():
            return PublicacionResultado(
                modo=modo.value,
                exito=False,
                tipo="foto",
                caption_length=len(caption),
                n_imagenes=0,
                error=f"No existe: {ruta_imagen}",
            )

        caption_full = caption
        if hashtags:
            caption_full = caption + "\n\n" + " ".join(hashtags)

        if modo == ModoPublicacion.DRY_RUN:
            return self._dry_run_foto(ruta_imagen, caption_full)

        if modo == ModoPublicacion.INTERACTIVO:
            if not self._confirmar(f"Publicar foto {ruta_imagen.name}?"):
                return PublicacionResultado(
                    modo=modo.value,
                    exito=False,
                    tipo="foto",
                    caption_length=len(caption_full),
                    n_imagenes=1,
                    error="cancelado por el usuario",
                )

        return self._publicar_foto_real(ruta_imagen, caption_full, modo)

    def _dry_run_foto(self, ruta: Path, caption: str) -> PublicacionResultado:
        print("=" * 60)
        print("[DRY-RUN] Publicación que se realizaría:")
        print("=" * 60)
        print(f"Imagen: {ruta}")
        print(f"Tamaño archivo: {ruta.stat().st_size:,} bytes")
        print(f"Caption ({len(caption)} chars):")
        print("---")
        print(caption[:500] + ("..." if len(caption) > 500 else ""))
        print("---")
        print()
        print("⚠️  No se publicó nada. Para publicar de verdad usar --real o --interactivo")
        return PublicacionResultado(
            modo=ModoPublicacion.DRY_RUN.value,
            exito=False,
            tipo="foto",
            caption_length=len(caption),
            n_imagenes=1,
            metadata={"dry_run": True, "ruta": str(ruta)},
        )

    def _publicar_foto_real(
        self, ruta: Path, caption: str, modo: ModoPublicacion
    ) -> PublicacionResultado:
        if not self.auth.data:
            return PublicacionResultado(
                modo=modo.value,
                exito=False,
                tipo="foto",
                caption_length=len(caption),
                n_imagenes=1,
                error="auth.json no configurado",
            )

        image_url = self._upload_temp(ruta)
        if not image_url:
            return PublicacionResultado(
                modo=modo.value,
                exito=False,
                tipo="foto",
                caption_length=len(caption),
                n_imagenes=1,
                error="No se pudo subir la imagen a un host publico",
            )

        if not self._check_public_url(image_url):
            return PublicacionResultado(
                modo=modo.value,
                exito=False,
                tipo="foto",
                caption_length=len(caption),
                n_imagenes=1,
                error=f"URL no accesible publicamente: {image_url}",
            )

        try:
            container = self._request(
                f"{self.auth.data.instagram_user_id}/media",
                method="POST",
                json_body={
                    "image_url": image_url,
                    "caption": caption,
                    "access_token": self.auth.data.access_token,
                },
            )
            creation_id = container["id"]

            while True:
                status = self._request(
                    creation_id,
                    params={
                        "fields": "status_code,status",
                    },
                )
                code = status.get("status_code")
                if code == "FINISHED":
                    break
                if code == "ERROR":
                    return PublicacionResultado(
                        modo=modo.value,
                        exito=False,
                        tipo="foto",
                        caption_length=len(caption),
                        n_imagenes=1,
                        media_ids=[creation_id],
                        error=f"Media processing failed: {status}",
                    )
                time.sleep(2)

            publish = self._request(
                f"{self.auth.data.instagram_user_id}/media_publish",
                method="POST",
                json_body={"creation_id": creation_id, "access_token": self.auth.data.access_token},
            )
            ig_post_id = publish.get("id")
            permalink = self._obtener_permalink(ig_post_id) if ig_post_id else None

            return PublicacionResultado(
                modo=modo.value,
                exito=True,
                tipo="foto",
                caption_length=len(caption),
                n_imagenes=1,
                media_ids=[creation_id, ig_post_id] if ig_post_id else [creation_id],
                instagram_post_id=ig_post_id,
                permalink=permalink,
            )
        except Exception as e:
            return PublicacionResultado(
                modo=modo.value,
                exito=False,
                tipo="foto",
                caption_length=len(caption),
                n_imagenes=1,
                error=str(e),
            )

    # ---------------- Publicar carrusel ----------------

    def publicar_carrusel(
        self,
        rutas_imagenes: list[str | Path],
        caption: str,
        hashtags: list[str] | None = None,
        modo: ModoPublicacion = ModoPublicacion.DRY_RUN,
    ) -> PublicacionResultado:
        rutas = [Path(r) for r in rutas_imagenes]
        for r in rutas:
            if not r.exists():
                return PublicacionResultado(
                    modo=modo.value,
                    exito=False,
                    tipo="carrusel",
                    caption_length=len(caption),
                    n_imagenes=len(rutas),
                    error=f"No existe: {r}",
                )

        if not (2 <= len(rutas) <= 10):
            return PublicacionResultado(
                modo=modo.value,
                exito=False,
                tipo="carrusel",
                caption_length=len(caption),
                n_imagenes=len(rutas),
                error=f"Carrusel debe tener entre 2 y 10 imagenes (recibido: {len(rutas)})",
            )

        caption_full = caption
        if hashtags:
            caption_full = caption + "\n\n" + " ".join(hashtags)

        if modo == ModoPublicacion.DRY_RUN:
            return self._dry_run_carrusel(rutas, caption_full)

        if modo == ModoPublicacion.INTERACTIVO:
            if not self._confirmar(f"Publicar carrusel de {len(rutas)} imagenes?"):
                return PublicacionResultado(
                    modo=modo.value,
                    exito=False,
                    tipo="carrusel",
                    caption_length=len(caption_full),
                    n_imagenes=len(rutas),
                    error="cancelado por el usuario",
                )

        return self._publicar_carrusel_real(rutas, caption_full, modo)

    def _dry_run_carrusel(self, rutas: list[Path], caption: str) -> PublicacionResultado:
        print("=" * 60)
        print("[DRY-RUN] Carrusel que se publicaría:")
        print("=" * 60)
        for i, r in enumerate(rutas, 1):
            print(f"  {i}. {r.name} ({r.stat().st_size:,} bytes)")
        print(f"Caption ({len(caption)} chars):")
        print("---")
        print(caption[:500] + ("..." if len(caption) > 500 else ""))
        print("---")
        return PublicacionResultado(
            modo=ModoPublicacion.DRY_RUN.value,
            exito=False,
            tipo="carrusel",
            caption_length=len(caption),
            n_imagenes=len(rutas),
            metadata={"dry_run": True, "rutas": [str(r) for r in rutas]},
        )

    def _publicar_carrusel_real(
        self, rutas: list[Path], caption: str, modo: ModoPublicacion
    ) -> PublicacionResultado:
        if not self.auth.data:
            return PublicacionResultado(
                modo=modo.value,
                exito=False,
                tipo="carrusel",
                caption_length=len(caption),
                n_imagenes=len(rutas),
                error="auth.json no configurado",
            )

        try:
            children_ids: list[str] = []
            for ruta in rutas:
                image_url = self._upload_temp(ruta)
                if not image_url:
                    return PublicacionResultado(
                        modo=modo.value,
                        exito=False,
                        tipo="carrusel",
                        caption_length=len(caption),
                        n_imagenes=len(rutas),
                        error=f"No se pudo subir {ruta}",
                    )
                container = self._request(
                    f"{self.auth.data.instagram_user_id}/media",
                    method="POST",
                    json_body={
                        "image_url": image_url,
                        "is_carousel_item": True,
                        "access_token": self.auth.data.access_token,
                    },
                )
                children_ids.append(container["id"])

            carousel = self._request(
                f"{self.auth.data.instagram_user_id}/media",
                method="POST",
                json_body={
                    "media_type": "CAROUSEL",
                    "children": children_ids,
                    "caption": caption,
                    "access_token": self.auth.data.access_token,
                },
            )
            creation_id = carousel["id"]

            while True:
                status = self._request(
                    creation_id,
                    params={
                        "fields": "status_code,status",
                    },
                )
                if status.get("status_code") == "FINISHED":
                    break
                if status.get("status_code") == "ERROR":
                    return PublicacionResultado(
                        modo=modo.value,
                        exito=False,
                        tipo="carrusel",
                        caption_length=len(caption),
                        n_imagenes=len(rutas),
                        media_ids=children_ids,
                        error=f"Processing failed: {status}",
                    )
                time.sleep(2)

            publish = self._request(
                f"{self.auth.data.instagram_user_id}/media_publish",
                method="POST",
                json_body={"creation_id": creation_id, "access_token": self.auth.data.access_token},
            )
            ig_post_id = publish.get("id")
            permalink = self._obtener_permalink(ig_post_id) if ig_post_id else None

            return PublicacionResultado(
                modo=modo.value,
                exito=True,
                tipo="carrusel",
                caption_length=len(caption),
                n_imagenes=len(rutas),
                media_ids=[ig_post_id] if ig_post_id else [],
                instagram_post_id=ig_post_id,
                permalink=permalink,
            )
        except Exception as e:
            return PublicacionResultado(
                modo=modo.value,
                exito=False,
                tipo="carrusel",
                caption_length=len(caption),
                n_imagenes=len(rutas),
                error=str(e),
            )

    # ---------------- Helpers ----------------

    def _upload_temp(self, ruta: Path) -> str | None:
        """Sube imagen a Cloudinary para obtener URL publica."""
        if not self.uploader.configurado:
            print("⚠️  Cloudinary no configurado. Ver cloudinary_upload.py")
            return None
        return self.uploader.subir(ruta)

    def _obtener_permalink(self, ig_post_id: str) -> str | None:
        try:
            data = self._request(ig_post_id, params={"fields": "permalink"})
            return data.get("permalink")
        except Exception:
            return None

    @staticmethod
    def _confirmar(mensaje: str) -> bool:
        try:
            resp = input(f"{mensaje} [s/N]: ").strip().lower()
            return resp in ("s", "si", "y", "yes")
        except EOFError:
            return False

    def guardar_log(self, resultado: PublicacionResultado, nombre: str | None = None) -> Path:
        if not nombre:
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            nombre = f"publicacion_{ts}"
        ruta = LOG_DIR / f"{nombre}.json"
        ruta.write_text(
            json.dumps(resultado.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8"
        )
        return ruta


def demo() -> None:
    auth = InstagramAuth()
    if not auth.configurado():
        print("auth.json no existe. Crear siguiendo README_PUBLICACION_IG.md")
        return
    publisher = InstagramPublisher(auth)
    if not auth.validar_token():
        print("Token invalido o expirado")
        return
    print("Publisher listo. Modos disponibles:")
    print("  - dry-run      (default, no publica)")
    print("  - interactivo  (pide confirmacion)")
    print("  - real         (publica directamente, usar con cuidado)")


if __name__ == "__main__":
    demo()
