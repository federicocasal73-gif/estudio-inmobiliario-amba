"""
Publicador de publicaciones en MercadoLibre Argentina.

Soporta 3 modos (igual que Instagram):
  - dry-run: muestra que publicaria pero no hace nada
  - interactivo: muestra preview, pide confirmacion
  - real: publica de una

MercadoLibre API v1:
  - Auth: OAuth2 (access_token + refresh_token)
  - Endpoints: /sites/MLA/listings (crear), /items/{id} (gestionar)
  - Fotos: se suben via multipart al mismo endpoint
  - Categorias: terrenos = MLA1459, casas = MLA1472, etc.

Setup:
  1. Crear app en https://developers.mercadolibre.com.ar
  2. Obtener client_id y client_secret
  3. Obtener access_token via OAuth flow
  4. Agregar a auth.json:
       "mercadolibre": {
         "client_id": "...",
         "client_secret": "...",
         "access_token": "...",
         "refresh_token": "..."
       }

Uso:
    from mercadolibre_publisher import MercadoLibrePublisher, ModoPublicacion

    pub = MercadoLibrePublisher()
    resultado = pub.crear_publicacion(
        titulo="Chacra 5 hectareas en Cañuelas",
        precio=150000,
        moneda="USD",
        descripcion="Chacra con 5 ha, paisaje pampeano...",
        ubicacion={"state": "Buenos Aires", "city": "Cañuelas"},
        imagenes=[Path("foto1.jpg"), Path("foto2.jpg")],
        modo=ModoPublicacion.DRY_RUN,
    )
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
AUTH_PATH = ROOT / "auth.json"

MELI_API_BASE = "https://api.mercadolibre.com"
MELI_AUTH_URL = "https://api.mercadolibre.com/oauth/token"

# Categorias MercadoLibre Argentina
CATEGORIAS = {
    "terreno": "MLA1459",  # Terrenos y parcelas
    "casa": "MLA1472",  # Casas
    "campo": "MLA1459",  # Campo/terreno
    "chacra": "MLA1459",  # Chacra = terreno
    "lote": "MLA1459",  # Lote = terreno
    "construccion": "MLA1472",  # Casa en construccion
}


class ModoPublicacion(Enum):
    DRY_RUN = "dry-run"
    INTERACTIVO = "interactivo"
    REAL = "real"


@dataclass
class PublicacionML:
    """Publicacion para MercadoLibre."""

    titulo: str
    precio: float
    moneda: str = "USD"
    descripcion: str = ""
    categoria: str = "terreno"
    estado: str = "used"  # used, new
    ubicacion: dict[str, str] = field(default_factory=dict)
    imagenes: list[str] = field(default_factory=list)
    atributos: dict[str, Any] = field(default_factory=dict)
    id: str | None = None
    permalink: str | None = None
    status: str = "draft"

    def to_dict(self) -> dict[str, Any]:
        d = {
            "title": self.titulo,
            "price": self.precio,
            "currency_id": self.moneda,
            "description": self.descripcion,
            "category_id": CATEGORIAS.get(self.categoria, CATEGORIAS["terreno"]),
            "condition": self.estado,
            "listing_type_id": "free",  # publicacion gratuita
        }
        if self.ubicacion:
            d["location"] = self.ubicacion
        if self.atributos:
            d["attributes"] = [{"id": k, "value_name": v} for k, v in self.atributos.items()]
        return d


@dataclass
class ResultadoPublicacionML:
    """Resultado de una operacion de publicacion."""

    ok: bool
    mode: str
    item_id: str | None = None
    permalink: str | None = None
    error: str | None = None
    dry_run_data: dict[str, Any] | None = None

    def resumen(self) -> str:
        if self.ok and self.mode == "dry-run":
            return f"[DRY-RUN] Se publicaria: {self.dry_run_data.get('title', '?')}"
        elif self.ok:
            return f"Publicado OK: {self.permalink}"
        else:
            return f"Error: {self.error}"


class MercadoLibrePublisher:
    """Publica y gestiona publicaciones en MercadoLibre Argentina."""

    def __init__(self, auth_path: Path | None = None):
        self.auth_path = auth_path or AUTH_PATH
        self._config: dict[str, Any] = {}
        self._cargar_config()

    def _cargar_config(self) -> bool:
        try:
            raw = json.loads(self.auth_path.read_text(encoding="utf-8"))
            self._config = raw.get("mercadolibre", {})
            return bool(self._config.get("access_token"))
        except (json.JSONDecodeError, OSError):
            return False

    def configurado(self) -> bool:
        return bool(self._config.get("access_token"))

    def _request(
        self,
        method: str,
        endpoint: str,
        data: dict[str, Any] | None = None,
        files: list[tuple[str, Path]] | None = None,
    ) -> dict[str, Any]:
        """Request autenticado a la API de MercadoLibre."""
        url = f"{MELI_API_BASE}{endpoint}"
        token = self._config.get("access_token", "")

        body = None
        content_type = "application/json"

        if files:
            # Multipart upload
            boundary = "----MercadoLibreBoundary"
            content_type = f"multipart/form-data; boundary={boundary}"
            body = self._build_multipart(boundary, data or {}, files)
        elif data:
            body = json.dumps(data).encode("utf-8")

        req = urllib.request.Request(url, data=body, method=method)
        req.add_header("Authorization", f"Bearer {token}")
        req.add_header("Content-Type", content_type)

        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            error_body = e.read().decode("utf-8", errors="replace")
            try:
                error_data = json.loads(error_body)
                msg = error_data.get("message", str(e))
            except json.JSONDecodeError:
                msg = error_body[:200]
            raise RuntimeError(f"ML API error {e.code}: {msg}") from e

    @staticmethod
    def _build_multipart(
        boundary: str,
        fields: dict[str, str],
        files: list[tuple[str, Path]],
    ) -> bytes:
        """Construye body multipart/form-data."""
        crlf = b"\r\n"
        parts: list[bytes] = []

        for key, value in fields.items():
            parts.append(f"--{boundary}".encode())
            parts.append(f'Content-Disposition: form-data; name="{key}"'.encode())
            parts.append(b"")
            parts.append(value.encode("utf-8"))
            parts.append(crlf)

        for field_name, file_path in files:
            parts.append(f"--{boundary}".encode())
            parts.append(
                f'Content-Disposition: form-data; name="{field_name}"; '
                f'filename="{file_path.name}"'.encode()
            )
            parts.append(b"Content-Type: application/octet-stream")
            parts.append(b"")
            parts.append(file_path.read_bytes())
            parts.append(crlf)

        parts.append(f"--{boundary}--".encode())
        parts.append(crlf)
        return b"".join(parts)

    def _refresh_token(self) -> bool:
        """Refresca el access_token usando el refresh_token."""
        client_id = self._config.get("client_id", "")
        client_secret = self._config.get("client_secret", "")
        refresh_token = self._config.get("refresh_token", "")

        if not all([client_id, client_secret, refresh_token]):
            return False

        data = {
            "grant_type": "refresh_token",
            "client_id": client_id,
            "client_secret": client_secret,
            "refresh_token": refresh_token,
        }

        req = urllib.request.Request(
            MELI_AUTH_URL,
            data=json.dumps(data).encode("utf-8"),
            method="POST",
        )
        req.add_header("Content-Type", "application/json")

        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                result = json.loads(resp.read().decode("utf-8"))
                self._config["access_token"] = result["access_token"]
                if "refresh_token" in result:
                    self._config["refresh_token"] = result["refresh_token"]
                return True
        except (urllib.error.URLError, KeyError):
            return False

    def crear_publicacion(
        self,
        titulo: str,
        precio: float,
        moneda: str = "USD",
        descripcion: str = "",
        categoria: str = "terreno",
        ubicacion: dict[str, str] | None = None,
        imagenes: list[Path] | None = None,
        atributos: dict[str, Any] | None = None,
        modo: ModoPublicacion = ModoPublicacion.DRY_RUN,
    ) -> ResultadoPublicacionML:
        """Crea una publicacion en MercadoLibre."""
        pub = PublicacionML(
            titulo=titulo,
            precio=precio,
            moneda=moneda,
            descripcion=descripcion,
            categoria=categoria,
            ubicacion=ubicacion or {},
            imagenes=[str(p) for p in (imagenes or [])],
            atributos=atributos or {},
        )

        if modo == ModoPublicacion.DRY_RUN:
            return ResultadoPublicacionML(
                ok=True,
                mode="dry-run",
                dry_run_data=pub.to_dict(),
            )

        if not self.configurado():
            return ResultadoPublicacionML(
                ok=False,
                mode=modo.value,
                error="MercadoLibre no configurado. Agregar credenciales a auth.json",
            )

        try:
            # Crear publicacion
            resultado = self._request("POST", "/sites/MLA/items", pub.to_dict())
            item_id = resultado.get("id")
            permalink = resultado.get("permalink")

            # Subir imagenes si hay
            if imagenes and item_id:
                for img in imagenes:
                    img_path = Path(img) if isinstance(img, str) else img
                    if img_path.exists():
                        self._upload_image(item_id, img_path)

            # Publicar (cambiar estado a active)
            if item_id and modo == ModoPublicacion.REAL:
                self._request("PUT", f"/items/{item_id}", {"status": "active"})

            return ResultadoPublicacionML(
                ok=True,
                mode=modo.value,
                item_id=item_id,
                permalink=permalink,
            )
        except RuntimeError as e:
            return ResultadoPublicacionML(
                ok=False,
                mode=modo.value,
                error=str(e),
            )

    def _upload_image(self, item_id: str, image_path: Path) -> bool:
        """Sube una imagen a una publicacion existente."""
        try:
            self._request(
                "POST",
                f"/items/{item_id}/pictures",
                files=[("file", image_path)],
            )
            return True
        except RuntimeError:
            return False

    def listar_publicaciones(self, estado: str = "active") -> list[dict[str, Any]]:
        """Lista las publicaciones del usuario."""
        if not self.configurado():
            return []
        try:
            result = self._request("GET", f"/users/me/items?status={estado}")
            return result.get("results", [])
        except RuntimeError:
            return []

    def eliminar_publicacion(self, item_id: str) -> bool:
        """Elimina (desactiva) una publicacion."""
        if not self.configurado():
            return False
        try:
            self._request("PUT", f"/items/{item_id}", {"status": "closed"})
            return True
        except RuntimeError:
            return False

    def buscar_publicaciones(
        self,
        query: str,
        ubicacion: str = "",
        precio_min: float | None = None,
        precio_max: float | None = None,
    ) -> list[dict[str, Any]]:
        """Busca publicaciones (para monitorear competencia)."""
        params = {"q": query, "limit": 20}
        if ubicacion:
            params["state"] = ubicacion
        if precio_min:
            params["price"] = f"{precio_min}-{precio_max or ''}"

        try:
            result = self._request("GET", f"/sites/MLA/search?{urllib.parse.urlencode(params)}")
            return result.get("results", [])
        except RuntimeError:
            return []


if __name__ == "__main__":
    pub = MercadoLibrePublisher()
    if pub.configurado():
        print("MercadoLibre configurado")
    else:
        print("MercadoLibre NO configurado")
        print("Agregar credenciales a auth.json:")
        print(
            '  "mercadolibre": {"client_id": "...", "client_secret": "...", "access_token": "..."}'
        )
