"""CLI para curar, editar y gestionar prompts del cerebro.

Uso:
    python -m cerebro.curator listar [--status=pending|approved|all]
    python -m cerebro.curator ver --id=xxx
    python -m cerebro.curator editar --id=xxx --prompt="nuevo prompt"
    python -m cerebro.curator aprobar --id=xxx --rating=5
    python -m cerebro.curator rechazar --id=xxx
    python -m cerebro.curator buscar --categoria=terreno
    python -m cerebro.curator exportar --min-rating=4
    python -m cerebro.curator estadisticas
    python -m cerebro.curator importar --file=prompts.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from cerebro.prompt_database import PromptDatabase


def cmd_listar(args: argparse.Namespace) -> int:
    """Lista prompts."""
    db = PromptDatabase()

    if args.status == "pending":
        prompts = db.buscar(aprobado=False)
    elif args.status == "approved":
        prompts = db.buscar(aprobado=True)
    else:
        prompts = db.listar(limit=args.limit)

    if not prompts:
        print("No hay prompts para mostrar.")
        return 0

    print(f"\n{'ID':<10} {'Rating':<8} {'Cat':<15} {'Estilo':<12} {'Prompt (primeros 50)'}")
    print("-" * 90)

    for p in prompts:
        status = "✓" if p.aprobado else "○"
        prompt_preview = p.prompt[:50] + "..." if len(p.prompt) > 50 else p.prompt
        print(
            f"{p.id:<10} {status}{p.rating:<6} {p.categoria:<15} "
            f"{p.estilo:<12} {prompt_preview}"
        )

    print(f"\nTotal: {len(prompts)} prompts")
    return 0


def cmd_ver(args: argparse.Namespace) -> int:
    """Muestra detalle de un prompt."""
    db = PromptDatabase()
    prompt = db.obtener(args.id)

    if not prompt:
        print(f"Prompt {args.id} no encontrado.")
        return 1

    print(f"\n{'='*60}")
    print(f"ID: {prompt.id}")
    print(f"Creado: {prompt.created_at}")
    print(f"Actualizado: {prompt.updated_at}")
    print(f"Aprobado: {'Sí' if prompt.aprobado else 'No'}")
    print(f"Rating: {'★' * prompt.rating}{'☆' * (5 - prompt.rating)}")
    print(f"\nPrompt:")
    print(f"  {prompt.prompt}")
    print(f"\nNegative Prompt:")
    print(f"  {prompt.negative_prompt}")
    print(f"\nAspect Ratio: {prompt.aspect_ratio}")
    print(f"Styles: {', '.join(prompt.styles)}")
    print(f"\nMetadata:")
    for k, v in prompt.metadata.items():
        print(f"  {k}: {v}")
    if prompt.tags:
        print(f"\nTags: {', '.join(prompt.tags)}")
    if prompt.notas:
        print(f"\nNotas: {prompt.notas}")
    print(f"{'='*60}\n")
    return 0


def cmd_editar(args: argparse.Namespace) -> int:
    """Edita un prompt."""
    db = PromptDatabase()
    updates = {}

    if args.prompt:
        updates["prompt"] = args.prompt
    if args.negative:
        updates["negative_prompt"] = args.negative
    if args.aspect:
        updates["aspect_ratio"] = args.aspect
    if args.notas:
        updates["notas"] = args.notas

    if not updates:
        print("No se especificaron cambios.")
        return 1

    result = db.actualizar(args.id, **updates)
    if result:
        print(f"Prompt {args.id} actualizado.")
        return 0
    else:
        print(f"Prompt {args.id} no encontrado.")
        return 1


def cmd_aprobar(args: argparse.Namespace) -> int:
    """Aprueba un prompt."""
    db = PromptDatabase()
    result = db.actualizar(
        args.id,
        aprobado=True,
        rating=args.rating,
    )
    if result:
        print(f"Prompt {args.id} aprobado con rating {args.rating}.")
        return 0
    else:
        print(f"Prompt {args.id} no encontrado.")
        return 1


def cmd_rechazar(args: argparse.Namespace) -> int:
    """Rechaza un prompt."""
    db = PromptDatabase()
    result = db.actualizar(
        args.id,
        aprobado=False,
        rating=0,
        notas=args.motivo or "Rechazado",
    )
    if result:
        print(f"Prompt {args.id} rechazado.")
        return 0
    else:
        print(f"Prompt {args.id} no encontrado.")
        return 1


def cmd_buscar(args: argparse.Namespace) -> int:
    """Busca prompts con filtros."""
    db = PromptDatabase()
    prompts = db.buscar(
        categoria=args.categoria,
        estilo=args.estilo,
        momento_dia=args.momento,
        ubicacion=args.ubicacion,
        texto=args.texto,
        min_rating=args.min_rating or 0,
    )

    if not prompts:
        print("No se encontraron prompts con esos filtros.")
        return 0

    print(f"\nResultados: {len(prompts)} prompts\n")
    for p in prompts:
        status = "✓" if p.aprobado else "○"
        print(f"  {p.id} {status}★{p.rating} [{p.categoria}/{p.estilo}] {p.prompt[:60]}...")

    return 0


def cmd_exportar(args: argparse.Namespace) -> int:
    """Exporta prompts aprobados."""
    db = PromptDatabase()
    aprobados = db.exportar_aprobados(min_rating=args.min_rating or 1)

    if not aprobados:
        print("No hay prompts aprobados para exportar.")
        return 0

    output = Path(args.output) if args.output else Path("prompts_exportados.json")
    output.write_text(
        json.dumps(aprobados, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"Exportados {len(aprobados)} prompts a {output}")
    return 0


def cmd_estadisticas(args: argparse.Namespace) -> int:
    """Muestra estadísticas."""
    db = PromptDatabase()
    stats = db.estadisticas()

    print(f"\n{'='*40}")
    print("ESTADÍSTICAS DEL CEREBRO")
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


def cmd_importar(args: argparse.Namespace) -> int:
    """Importa prompts desde JSON."""
    db = PromptDatabase()
    count = db.importar_desde_json(args.file)
    print(f"Importados {count} prompts nuevos desde {args.file}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Cerebro de Prompts - Gestión de prompts para IA"
    )
    sub = parser.add_subparsers(dest="comando", required=True)

    # listar
    p_list = sub.add_parser("listar", help="Lista prompts")
    p_list.add_argument(
        "--status", choices=["pending", "approved", "all"], default="all"
    )
    p_list.add_argument("--limit", type=int, default=50)

    # ver
    p_ver = sub.add_parser("ver", help="Detalle de un prompt")
    p_ver.add_argument("--id", required=True)

    # editar
    p_edit = sub.add_parser("editar", help="Edita un prompt")
    p_edit.add_argument("--id", required=True)
    p_edit.add_argument("--prompt", default=None)
    p_edit.add_argument("--negative", default=None)
    p_edit.add_argument("--aspect", default=None)
    p_edit.add_argument("--notas", default=None)

    # aprobar
    p_aprob = sub.add_parser("aprobar", help="Aprueba un prompt")
    p_aprob.add_argument("--id", required=True)
    p_aprob.add_argument("--rating", type=int, default=5, choices=range(1, 6))

    # rechazar
    p_rech = sub.add_parser("rechazar", help="Rechaza un prompt")
    p_rech.add_argument("--id", required=True)
    p_rech.add_argument("--motivo", default="")

    # buscar
    p_buscar = sub.add_parser("buscar", help="Busca prompts")
    p_buscar.add_argument("--categoria", default=None)
    p_buscar.add_argument("--estilo", default=None)
    p_buscar.add_argument("--momento", default=None)
    p_buscar.add_argument("--ubicacion", default=None)
    p_buscar.add_argument("--texto", default=None)
    p_buscar.add_argument("--min-rating", type=int, default=None)

    # exportar
    p_export = sub.add_parser("exportar", help="Exporta prompts aprobados")
    p_export.add_argument("--min-rating", type=int, default=1)
    p_export.add_argument("--output", default=None)

    # estadisticas
    sub.add_parser("estadisticas", help="Muestra estadísticas")

    # importar
    p_import = sub.add_parser("importar", help="Importa desde JSON")
    p_import.add_argument("--file", required=True)

    args = parser.parse_args()

    commands = {
        "listar": cmd_listar,
        "ver": cmd_ver,
        "editar": cmd_editar,
        "aprobar": cmd_aprobar,
        "rechazar": cmd_rechazar,
        "buscar": cmd_buscar,
        "exportar": cmd_exportar,
        "estadisticas": cmd_estadisticas,
        "importar": cmd_importar,
    }

    return commands[args.comando](args)


if __name__ == "__main__":
    sys.exit(main())
