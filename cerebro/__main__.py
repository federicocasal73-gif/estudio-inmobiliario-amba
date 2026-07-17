"""CLI principal del Cerebro de Prompts.

Uso:
    python -m cerebro agregar --url="https://instagram.com/reel/xxx"
    python -m cerebro procesar --url="https://instagram.com/reel/xxx"
    python -m cerebro estadisticas
    python -m cerebro buscar --categoria=terreno
    python -m cerebro listar
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from cerebro.cerebro import Cerebro


def cmd_agregar(args: argparse.Namespace) -> int:
    """Agrega un video para procesar."""
    cerebro = Cerebro(
        api_provider=args.api,
        max_frames=args.frames,
    )

    resultado = cerebro.procesar_video(
        url=args.url,
        n_frames=args.frames,
        auto_aprobar=args.auto_aprobar,
        tags=args.tags.split(",") if args.tags else None,
    )

    print(f"\nResultado:")
    print(f"  Frames extraídos: {resultado.frames_extraidos}")
    print(f"  Frames analizados: {resultado.frames_analizados}")
    print(f"  Prompts guardados: {resultado.prompts_guardados}")

    if resultado.errores:
        print(f"\nErrores ({len(resultado.errores)}):")
        for e in resultado.errores:
            print(f"  - {e}")

    return 0 if not resultado.errores else 1


def cmd_procesar(args: argparse.Namespace) -> int:
    """Procesa múltiples videos."""
    cerebro = Cerebro(
        api_provider=args.api,
        max_frames=args.frames,
    )

    urls = [u.strip() for u in args.urls.split(",") if u.strip()]
    resultados = cerebro.procesar_lote(
        urls,
        n_frames=args.frames,
        auto_aprobar=args.auto_aprobar,
    )

    total_prompts = sum(r.prompts_guardados for r in resultados)
    total_errores = sum(len(r.errores) for r in resultados)

    print(f"\nLote completo:")
    print(f"  Videos procesados: {len(resultados)}")
    print(f"  Total prompts: {total_prompts}")
    print(f"  Total errores: {total_errores}")

    return 0 if total_errores == 0 else 1


def cmd_listar(args: argparse.Namespace) -> int:
    """Lista prompts del cerebro."""
    cerebro = Cerebro()
    prompts = cerebro.db.listar(limit=args.limit)

    if not prompts:
        print("No hay prompts en el cerebro.")
        return 0

    print(f"\n{'ID':<10} {'★':<6} {'Cat':<15} {'Estilo':<12} {'Prompt'}")
    print("-" * 90)

    for p in prompts:
        status = "✓" if p.aprobado else "○"
        print(
            f"{p.id:<10} {status}{p.rating:<4} {p.categoria:<15} "
            f"{p.estilo:<12} {p.prompt[:45]}..."
        )

    print(f"\nTotal: {len(prompts)} prompts")
    return 0


def cmd_estadisticas(args: argparse.Namespace) -> int:
    """Muestra estadísticas del cerebro."""
    cerebro = Cerebro()
    stats = cerebro.estadisticas()

    print(f"\n{'='*40}")
    print("CEREBRO DE PROMPTS - ESTADÍSTICAS")
    print(f"{'='*40}")
    print(f"Total prompts:      {stats['total']}")
    print(f"Aprobados:          {stats['aprobados']}")
    print(f"Pendientes:         {stats['pendientes']}")
    print(f"Rating promedio:    {stats['rating_promedio']}")
    print(f"\nPor categoría:")
    for cat, count in sorted(stats["por_categoria"].items()):
        print(f"  {cat:<20} {count}")
    print(f"\nPor estilo:")
    for est, count in sorted(stats["por_estilo"].items()):
        print(f"  {est:<20} {count}")
    print(f"{'='*40}\n")
    return 0


def cmd_buscar(args: argparse.Namespace) -> int:
    """Busca prompts."""
    cerebro = Cerebro()
    prompts = cerebro.obtener_prompts(
        categoria=args.categoria,
        estilo=args.estilo,
        n=args.limit,
    )

    if not prompts:
        print("No se encontraron prompts.")
        return 0

    print(f"\nResultados: {len(prompts)} prompts\n")
    for p in prompts:
        print(f"  {p.id} ★{p.rating} [{p.categoria}/{p.estilo}] {p.prompt[:60]}...")

    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Cerebro de Prompts - Sistema de extracción y gestión"
    )
    sub = parser.add_subparsers(dest="comando", required=True)

    # agregar
    p_agregar = sub.add_parser("agregar", help="Agrega y procesa un video")
    p_agregar.add_argument("--url", required=True)
    p_agregar.add_argument("--frames", type=int, default=5)
    p_agregar.add_argument("--api", choices=["openai", "anthropic", "local"], default="openai")
    p_agregar.add_argument("--auto-aprobar", action="store_true")
    p_agregar.add_argument("--tags", default=None)

    # procesar
    p_proc = sub.add_parser("procesar", help="Procesa múltiples videos")
    p_proc.add_argument("--urls", required=True, help="URLs separadas por coma")
    p_proc.add_argument("--frames", type=int, default=5)
    p_proc.add_argument("--api", choices=["openai", "anthropic", "local"], default="openai")
    p_proc.add_argument("--auto-aprobar", action="store_true")

    # listar
    p_list = sub.add_parser("listar", help="Lista prompts")
    p_list.add_argument("--limit", type=int, default=50)

    # estadisticas
    sub.add_parser("estadisticas", help="Muestra estadísticas")

    # buscar
    p_buscar = sub.add_parser("buscar", help="Busca prompts")
    p_buscar.add_argument("--categoria", default=None)
    p_buscar.add_argument("--estilo", default=None)
    p_buscar.add_argument("--limit", type=int, default=10)

    args = parser.parse_args()

    commands = {
        "agregar": cmd_agregar,
        "procesar": cmd_procesar,
        "listar": cmd_listar,
        "estadisticas": cmd_estadisticas,
        "buscar": cmd_buscar,
    }

    return commands[args.comando](args)


if __name__ == "__main__":
    sys.exit(main())
