"""
Modulo de autenticacion con Instagram Graph API.

NO implementa OAuth completo en Python. En su lugar, lee el access token
desde auth.json (ignorado por git) que vos generas manualmente siguiendo
las instrucciones en README_PUBLICACION_IG.md.

Uso:
    from instagram_auth import InstagramAuth

    auth = InstagramAuth()
    if auth.configurado():
        print(f"User ID: {auth.user_id}")
        print(f"Cuenta: @{auth.username}")
    else:
        print("Seguir instrucciones en README_PUBLICACION_IG.md")

    # Validar que el token sigue vigente
    if auth.validar_token():
        print("Token OK")
    else:
        print("Token expirado, regenerar")
"""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent
AUTH_FILE = ROOT / "auth.json"
AUTH_EXAMPLE = ROOT / "auth-example.json"

GRAPH_API_VERSION = "v19.0"
GRAPH_API_BASE = f"https://graph.facebook.com/{GRAPH_API_VERSION}"


@dataclass
class AuthData:
    access_token: str
    instagram_user_id: str
    username: str = ""
    app_id: str = ""
    expires_at: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


class InstagramAuth:
    """Wrapper para el access token de Instagram Graph API."""

    def __init__(self, auth_path: Path = AUTH_FILE):
        self.auth_path = auth_path
        self._data: AuthData | None = None

    def configurado(self) -> bool:
        return self.auth_path.exists()

    def cargar(self) -> AuthData | None:
        if not self.configurado():
            return None
        try:
            data = json.loads(self.auth_path.read_text(encoding="utf-8"))
            self._data = AuthData(**data)
            return self._data
        except (json.JSONDecodeError, TypeError) as e:
            print(f"ERROR: auth.json mal formado: {e}")
            return None

    def guardar(self, auth: AuthData) -> None:
        """Guarda auth.json con permisos 600 (solo vos lo leeis)."""
        self.auth_path.write_text(json.dumps(auth.to_dict(), indent=2), encoding="utf-8")
        try:
            self.auth_path.chmod(0o600)
        except OSError:
            pass

    @property
    def data(self) -> AuthData | None:
        if self._data is None:
            self.cargar()
        return self._data

    def validar_token(self) -> bool:
        """Llama a /me para verificar que el token sirve."""
        if not self.data:
            return False
        url = f"{GRAPH_API_BASE}/me?access_token={self.data.access_token}"
        try:
            with urllib.request.urlopen(url, timeout=10) as resp:
                return resp.status == 200
        except (urllib.error.URLError, urllib.error.HTTPError):
            return False

    def validar_permisos_instagram(self) -> tuple[bool, list[str]]:
        """Verifica que los permisos necesarios esten concedidos."""
        if not self.data:
            return False, []
        url = f"{GRAPH_API_BASE}/me/permissions?access_token={self.data.access_token}"
        try:
            with urllib.request.urlopen(url, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                permisos = [
                    p["permission"] for p in data.get("data", []) if p.get("status") == "granted"
                ]
                necesarios = [
                    "instagram_basic",
                    "instagram_content_publish",
                    "pages_show_list",
                ]
                faltan = [p for p in necesarios if p not in permisos]
                return len(faltan) == 0, faltan
        except (urllib.error.URLError, urllib.error.HTTPError) as e:
            return False, [f"HTTP error: {e}"]

    def info_cuenta(self) -> dict | None:
        """Devuelve info de la cuenta IG vinculada."""
        if not self.data:
            return None
        url = (
            f"{GRAPH_API_BASE}/{self.data.instagram_user_id}"
            f"?fields=id,username,name,biography,website,followers_count,"
            f"media_count,profile_picture_url"
            f"&access_token={self.data.access_token}"
        )
        try:
            with urllib.request.urlopen(url, timeout=10) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except (urllib.error.URLError, urllib.error.HTTPError):
            return None


def crear_auth_example_si_no_existe() -> None:
    """Copia auth-example.json a auth.json si este ultimo no existe."""
    if not AUTH_FILE.exists() and AUTH_EXAMPLE.exists():
        print(
            f"INFO: No existe {AUTH_FILE.name}. Sigue las instrucciones en "
            "README_PUBLICACION_IG.md para generarlo."
        )
        print(f"      Hay un ejemplo en {AUTH_EXAMPLE.name} con la estructura esperada.")


if __name__ == "__main__":
    crear_auth_example_si_no_existe()
    auth = InstagramAuth()
    if auth.configurado():
        if auth.validar_token():
            print("✓ Token válido")
            ok, faltan = auth.validar_permisos_instagram()
            if ok:
                print("✓ Permisos OK")
                info = auth.info_cuenta()
                if info:
                    print(
                        f"✓ Cuenta: @{info.get('username')} "
                        f"({info.get('followers_count', '?')} seguidores)"
                    )
            else:
                print(f"✗ Faltan permisos: {faltan}")
        else:
            print("✗ Token inválido o expirado")
    else:
        print("✗ auth.json no existe")
        print("  Seguir instrucciones en README_PUBLICACION_IG.md")
