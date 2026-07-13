#!/usr/bin/env python3
"""
Script para subir el estudio a GitHub.

Pasos:
  1. Crear el repo en GitHub (via web o gh CLI)
  2. Agregar el remote: git remote add origin URL
  3. Push: git push -u origin main

Uso:
  python setup_git_remote.py [--url URL]

Si no se pasa --url, el script imprime las instrucciones para hacerlo manual.
"""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def run(cmd: str, cwd: Path = ROOT) -> tuple[int, str, str]:
    r = subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True, text=True)
    return r.returncode, r.stdout, r.stderr


def check_git() -> bool:
    rc, out, err = run("git status")
    if rc != 0:
        print("ERROR: este directorio no es un repo git. cd al directorio del estudio.")
        return False
    print("OK: es un repo git valido")
    return True


def check_remote() -> bool:
    rc, out, err = run("git remote -v")
    if rc != 0 or not out.strip():
        print("INFO: no hay remote configurado")
        return False
    print(f"Remote actual:\n{out}")
    return True


def add_remote(url: str) -> bool:
    rc, out, err = run(f"git remote add origin {url}")
    if rc != 0:
        print(f"ERROR agregando remote: {err}")
        return False
    print(f"OK: remote 'origin' agregado: {url}")
    return True


def push() -> bool:
    rc, out, err = run("git push -u origin main")
    if rc != 0:
        print(f"ERROR en push:\n{out}\n{err}")
        return False
    print(f"OK: push exitoso:\n{out}")
    return True


def main() -> int:
    print("=" * 60)
    print("SETUP GIT REMOTE - Estudio Inmobiliario AMBA")
    print("=" * 60)

    if not check_git():
        return 1

    url = None
    if len(sys.argv) > 2 and sys.argv[1] == "--url":
        url = sys.argv[2]

    if check_remote():
        print("Ya hay remote. Para pushear: git push -u origin main")
        return 0

    if not url:
        print()
        print("Pasos para subir el repo a GitHub:")
        print()
        print("1. Crear repo en https://github.com/new")
        print("   - Nombre sugerido: estudio-inmobiliario-amba")
        print("   - Visibility: Public o Private")
        print("   - NO inicializar con README/license/.gitignore (ya tenemos)")
        print()
        print("2. Copiar la URL del repo (HTTPS o SSH)")
        print()
        print("3. Ejecutar este script con la URL:")
        print("   python setup_git_remote.py --url https://github.com/TU_USUARIO/estudio-inmobiliario-amba.git")
        print()
        print("Alternativa con SSH:")
        print("   python setup_git_remote.py --url git@github.com:TU_USUARIO/estudio-inmobiliario-amba.git")
        print()
        print("O manualmente:")
        print("   git remote add origin URL")
        print("   git push -u origin main")
        return 0

    if not add_remote(url):
        return 1
    if not push():
        return 1

    print()
    print("=" * 60)
    print("LISTO! Repo en: " + url)
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
