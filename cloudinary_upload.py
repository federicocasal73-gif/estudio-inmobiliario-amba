"""
Upload de imagenes a Cloudinary para que Instagram Graph API pueda accederlas.

Cloudinary requiere que subas las imagenes a su CDN y devuelve una URL https
publica que IG puede consumir.

Setup:
  1. Crear cuenta gratuita en https://cloudinary.com (25 GB gratis)
  2. En el Dashboard copiar: Cloud Name, API Key, API Secret
  3. Agregar a auth_instagram_example.json:
       "cloudinary": {
         "cloud_name": "tu_cloud_name",
         "api_key": "123456789012345",
         "api_secret": "tu_api_secret"
       }

Uso:
    from cloudinary_upload import CloudinaryUploader
    uploader = CloudinaryUploader()
    url = uploader.subir(Path("imagen.jpg"))
    # url = "https://res.cloudinary.com/.../image.jpg"
"""

from __future__ import annotations

import hashlib
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from instagram_auth import InstagramAuth

CLOUDINARY_UPLOAD_URL = "https://api.cloudinary.com/v1_1/{cloud_name}/image/upload"


class CloudinaryUploader:
    """Sube imagenes a Cloudinary y devuelve URL publica."""

    def __init__(self, auth: InstagramAuth | None = None):
        self.auth = auth or InstagramAuth()
        self.configurado = self._cargar_config()

    def _cargar_config(self) -> bool:
        if not self.auth.configurado():
            return False
        data = self.auth.data
        if not data:
            return False
        # Cloudinary config esta en el mismo auth.json
        # pero el dataclass actual no lo tiene; leemos el JSON crudo
        try:
            raw = json.loads(self.auth.auth_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return False
        self.cloud_name = raw.get("cloudinary", {}).get("cloud_name", "")
        self.api_key = raw.get("cloudinary", {}).get("api_key", "")
        self.api_secret = raw.get("cloudinary", {}).get("api_secret", "")
        return bool(self.cloud_name and self.api_key and self.api_secret)

    def subir(
        self, ruta: Path, carpeta: str = "realestate_studio", public_id: str | None = None
    ) -> str | None:
        """Sube una imagen a Cloudinary y devuelve la URL segura."""
        if not self.configurado:
            print("⚠️  Cloudinary no configurado. Agregar credenciales a auth.json")
            return None

        ruta = Path(ruta)
        if not ruta.exists():
            print(f"⚠️  Archivo no existe: {ruta}")
            return None

        timestamp = int(time.time())
        if public_id is None:
            public_id = f"{carpeta}/{ruta.stem}_{timestamp}"

        # Construir firma
        params_to_sign = f"folder={carpeta}&public_id={public_id}&timestamp={timestamp}"
        signature = hashlib.sha1(f"{params_to_sign}{self.api_secret}".encode()).hexdigest()

        # Construir body multipart
        boundary = "----RealestateStudioBoundary"
        body = self._build_multipart(
            boundary=boundary,
            fields={
                "api_key": self.api_key,
                "timestamp": str(timestamp),
                "signature": signature,
                "folder": carpeta,
                "public_id": public_id,
            },
            file_path=ruta,
        )

        url = CLOUDINARY_UPLOAD_URL.format(cloud_name=self.cloud_name)
        req = urllib.request.Request(url, data=body, method="POST")
        req.add_header("Content-Type", f"multipart/form-data; boundary={boundary}")

        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return data.get("secure_url")
        except (urllib.error.URLError, urllib.error.HTTPError) as e:
            print(f"⚠️  Error subiendo a Cloudinary: {e}")
            return None

    @staticmethod
    def _build_multipart(boundary: str, fields: dict[str, str], file_path: Path) -> bytes:
        """Construye el body multipart/form-data manualmente."""
        crlf = b"\r\n"
        parts: list[bytes] = []

        for key, value in fields.items():
            parts.append(f"--{boundary}".encode())
            parts.append(f'Content-Disposition: form-data; name="{key}"'.encode())
            parts.append(b"")
            parts.append(value.encode("utf-8"))
            parts.append(crlf)

        parts.append(f"--{boundary}".encode())
        parts.append(
            f'Content-Disposition: form-data; name="file"; filename="{file_path.name}"'.encode()
        )
        parts.append(b"Content-Type: application/octet-stream")
        parts.append(b"")
        parts.append(file_path.read_bytes())
        parts.append(crlf)

        parts.append(f"--{boundary}--".encode())
        parts.append(crlf)

        return b"".join(parts)


if __name__ == "__main__":
    uploader = CloudinaryUploader()
    if uploader.configurado:
        print("Cloudinary configurado")
    else:
        print("Cloudinary NO configurado")
        print("Agregar credenciales a auth.json:")
        print('  "cloudinary": {"cloud_name": "...", "api_key": "...", "api_secret": "..."}')
