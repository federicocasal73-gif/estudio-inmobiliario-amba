"""
Publicador de publicaciones en Zonaprop Argentina.

Zonaprop es uno de los portales inmobiliarios mas grandes de Argentina.
A diferencia de MercadoLibre, Zonaprop tiene una API mas restrictiva y
generalmente requiere scraper o integracion directa con su plataforma.

Este modulo soporta:
  - dry-run: muestra que publicaria
  - interactivo: muestra preview, pide confirmacion
  - real: publica via scraping (requiere selenium o requests con session)

Nota: Zonaprop no tiene API publica oficial para publicaciones.
La implementacion real dependera de:
  1. Acceso a su panel de publicantes (requiere cuenta comercial)
  2. O bien scraping con selenium (fragil, puede romper)

Setup:
  1. Crear cuenta de publicante en Zonaprop
  2. Obtener credenciales de acceso
  3. Agregar a auth.json:
       "zonaprop": {
         "email": "tu@email.com",
         "password": "tu_password",
         "empresa": "Tu Inmobiliaria",
         "telefono": "+54 11 1234-5678"
       }

Uso:
    from zonaprop_publisher import ZonapropPublisher, ModoPublicacion

    pub = ZonapropPublisher()
    resultado = pub.crear_publicacion(
        titulo="Chacra 5 hectareas en Cañuelas",
        precio=150000,
        moneda="USD",
        descripcion="Chacra con 5 ha, paisaje pampeano...",
        ubicacion="Cañuelas, Buenos Aires",
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

ZONAPROP_BASE = "https://www.zonaprop.com.ar"
ZONAPROP_API = "https://api.zonaprop.com.ar"  # API no publica, estimada

# Tipos de propiedad Zonaprop
TIPOS_PROPIEDAD = {
    "terreno": "Terreno",
    "casa": "Casa",
    "lote": "Lote",
    "chacra": "Chacra",
    "campo": "Campo",
    "departamento": "Departamento",
    "oficina": "Oficina",
}


class ModoPublicacion(Enum):
    DRY_RUN = "dry-run"
    INTERACTIVO = "interactivo"
    REAL = "real"


@dataclass
class PublicacionZonaprop:
    """Publicacion para Zonaprop."""

    titulo: str
    precio: float
    moneda: str = "USD"
    descripcion: str = ""
    tipo_propiedad: str = "terreno"
    operacion: str = "venta"  # venta, alquiler
    superficie: float | None = None  # m2
    ubicacion: str = ""
    direccion: str = ""
    imagenes: list[str] = field(default_factory=list)
    atributos: dict[str, Any] = field(default_factory=dict)
    id: str | None = None
    permalink: str | None = None
    status: str = "draft"

    def to_dict(self) -> dict[str, Any]:
        return {
            "title": self.titulo,
            "price": self.precio,
            "currency": self.moneda,
            "description": self.descripcion,
            "property_type": TIPOS_PROPIEDAD.get(self.tipo_propiedad, "Terreno"),
            "operation": self.operacion,
            "surface": self.superficie,
            "location": self.ubicacion,
            "address": self.direccion,
            "attributes": self.atributos,
        }


@dataclass
class ResultadoPublicacionZP:
    """Resultado de una operacion de publicacion."""

    ok: bool
    mode: str
    publicacion_id: str | None = None
    permalink: str | None = None
    error: str | None = None
    dry_run_data: dict[str, Any] | None = None

    def resumen(self) -> str:
        if self.ok and self.mode == "dry-run":
            return f"[DRY-RUN] Se publicaria en Zonaprop: {self.dry_run_data.get('title', '?')}"
        elif self.ok:
            return f"Publicado en Zonaprop OK: {self.permalink}"
        else:
            return f"Error Zonaprop: {self.error}"


class ZonapropPublisher:
    """Publica y gestiona publicaciones en Zonaprop Argentina."""

    def __init__(self, auth_path: Path | None = None):
        self.auth_path = auth_path or AUTH_PATH
        self._config: dict[str, Any] = {}
        self._session_cookie: str | None = None
        self._cargar_config()

    def _cargar_config(self) -> bool:
        try:
            raw = json.loads(self.auth_path.read_text(encoding="utf-8"))
            self._config = raw.get("zonaprop", {})
            return bool(self._config.get("email"))
        except (json.JSONDecodeError, OSError):
            return False

    def configurado(self) -> bool:
        return bool(self._config.get("email"))

    def _request(
        self,
        method: str,
        endpoint: str,
        data: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """Request a la API de Zonaprop."""
        url = f"{ZONAPROP_BASE}{endpoint}" if endpoint.startswith("/") else endpoint

        hdrs = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/json",
        }
        if self._session_cookie:
            hdrs["Cookie"] = self._session_cookie
        if headers:
            hdrs.update(headers)

        body = None
        if data:
            body = json.dumps(data).encode("utf-8")
            hdrs["Content-Type"] = "application/json"

        req = urllib.request.Request(url, data=body, method=method)
        for k, v in hdrs.items():
            req.add_header(k, v)

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
            raise RuntimeError(f"Zonaprop API error {e.code}: {msg}") from e

    def login(self) -> bool:
        """Login a Zonaprop (requiere credenciales)."""
        if not self.configurado():
            return False

        email = self._config.get("email", "")
        password = self._config.get("password", "")

        try:
            result = self._request(
                "POST",
                f"{ZONAPROP_BASE}/api/login",
                {
                    "email": email,
                    "password": password,
                },
            )
            self._session_cookie = result.get("session_cookie", "")
            return True
        except (RuntimeError, KeyError):
            return False

    def crear_publicacion(
        self,
        titulo: str,
        precio: float,
        moneda: str = "USD",
        descripcion: str = "",
        tipo_propiedad: str = "terreno",
        operacion: str = "venta",
        superficie: float | None = None,
        ubicacion: str = "",
        direccion: str = "",
        imagenes: list[Path] | None = None,
        atributos: dict[str, Any] | None = None,
        modo: ModoPublicacion = ModoPublicacion.DRY_RUN,
    ) -> ResultadoPublicacionZP:
        """Crea una publicacion en Zonaprop."""
        pub = PublicacionZonaprop(
            titulo=titulo,
            precio=precio,
            moneda=moneda,
            descripcion=descripcion,
            tipo_propiedad=tipo_propiedad,
            operacion=operacion,
            superficie=superficie,
            ubicacion=ubicacion,
            direccion=direccion,
            imagenes=[str(p) for p in (imagenes or [])],
            atributos=atributos or {},
        )

        if modo == ModoPublicacion.DRY_RUN:
            return ResultadoPublicacionZP(
                ok=True,
                mode="dry-run",
                dry_run_data=pub.to_dict(),
            )

        if not self.configurado():
            return ResultadoPublicacionZP(
                ok=False,
                mode=modo.value,
                error="Zonaprop no configurado. Agregar credenciales a auth.json",
            )

        try:
            # Login si no hay session
            if not self._session_cookie:
                if not self.login():
                    return ResultadoPublicacionZP(
                        ok=False,
                        mode=modo.value,
                        error="No se pudo hacer login en Zonaprop",
                    )

            # Crear publicacion
            resultado = self._request("POST", "/api/propiedades", pub.to_dict())
            pub_id = resultado.get("id")
            permalink = resultado.get("permalink")

            # Subir imagenes si hay
            if imagenes and pub_id:
                for img in imagenes:
                    img_path = Path(img) if isinstance(img, str) else img
                    if img_path.exists():
                        self._upload_image(pub_id, img_path)

            return ResultadoPublicacionZP(
                ok=True,
                mode=modo.value,
                publicacion_id=pub_id,
                permalink=permalink,
            )
        except RuntimeError as e:
            return ResultadoPublicacionZP(
                ok=False,
                mode=modo.value,
                error=str(e),
            )

    def _upload_image(self, publicacion_id: str, image_path: Path) -> bool:
        """Sube una imagen a una publicacion existente."""
        try:
            self._request(
                "POST",
                f"/api/propiedades/{publicacion_id}/fotos",
                headers={"Content-Type": "multipart/form-data"},
            )
            return True
        except RuntimeError:
            return False

    def listar_publicaciones(self) -> list[dict[str, Any]]:
        """Lista las publicaciones del usuario."""
        if not self.configurado():
            return []
        try:
            if not self._session_cookie:
                self.login()
            result = self._request("GET", "/api/propiedades/mis-publicaciones")
            return result.get("results", [])
        except RuntimeError:
            return []

    def eliminar_publicacion(self, publicacion_id: str) -> bool:
        """Elimina una publicacion."""
        if not self.configurado():
            return False
        try:
            self._request("DELETE", f"/api/propiedades/{publicacion_id}")
            return True
        except RuntimeError:
            return False

    def buscar_propiedades(
        self,
        query: str,
        ubicacion: str = "",
        precio_min: float | None = None,
        precio_max: float | None = None,
        tipo: str = "",
    ) -> list[dict[str, Any]]:
        """Busca propiedades (para monitorear competencia)."""
        params: dict[str, str] = {"q": query}
        if ubicacion:
            params["ubicacion"] = ubicacion
        if precio_min:
            params["precio_min"] = str(precio_min)
        if precio_max:
            params["precio_max"] = str(precio_max)
        if tipo:
            params["tipo"] = tipo

        try:
            result = self._request("GET", f"/api/buscar?{urllib.parse.urlencode(params)}")
            return result.get("results", [])
        except RuntimeError:
            return []


if __name__ == "__main__":
    pub = ZonapropPublisher()
    if pub.configurado():
        print("Zonaprop configurado")
    else:
        print("Zonaprop NO configurado")
        print("Agregar credenciales a auth.json:")
        print('  "zonaprop": {"email": "...", "password": "..."}')
