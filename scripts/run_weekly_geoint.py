#!/usr/bin/env python3
"""
CLI runner for the weekly geopolitical intelligence report.

Usage:
  python scripts/run_weekly_geoint.py
  python scripts/run_weekly_geoint.py --days 14 --classification CONFIDENTIAL
  python scripts/run_weekly_geoint.py --categories economics security
  python scripts/run_weekly_geoint.py --regions latam eu
"""

from __future__ import annotations

import asyncio
import sys
import os

# Allow running from the project root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

import argparse
from datetime import datetime, timezone


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Genera informe semanal de inteligencia geopolítica"
    )
    parser.add_argument(
        "--days",
        type=int,
        default=7,
        metavar="N",
        help="Número de días hacia atrás a recopilar (default: 7)",
    )
    parser.add_argument(
        "--categories",
        nargs="+",
        choices=["economics", "security", "defense", "intelligence"],
        default=None,
        help="Categorías a analizar (default: todas)",
    )
    parser.add_argument(
        "--regions",
        nargs="+",
        default=None,
        help="Filtrar fuentes por región (ej: latam eu global mena)",
    )
    parser.add_argument(
        "--classification",
        choices=["UNCLASSIFIED", "CUI", "CONFIDENTIAL", "SECRET"],
        default="UNCLASSIFIED",
        help="Nivel de clasificación del informe (default: UNCLASSIFIED)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Ruta de salida del informe (default: data/reports/geoint/)",
    )
    parser.add_argument(
        "--provider",
        type=str,
        default=None,
        help="LLM provider a usar (default: del .env o 'ollama')",
    )
    parser.add_argument(
        "--model",
        type=str,
        default=None,
        help="Modelo LLM a usar (default: del .env o 'gemma4:4b')",
    )
    return parser.parse_args()


async def main() -> None:
    args = parse_args()

    # Override settings via env if flags provided
    if args.provider:
        os.environ["GEOINT_LLM_PROVIDER"] = args.provider
    if args.model:
        os.environ["GEOINT_LLM_MODEL"] = args.model

    # Force reload settings after env overrides
    from app.core.config import get_settings  # noqa: PLC0415
    get_settings.cache_clear()

    from app.intelligence.geoint_weekly import WeeklyGeointPipeline  # noqa: PLC0415

    print("\n" + "=" * 60)
    print("  ATALAYA — INFORME DE INTELIGENCIA GEOPOLÍTICA SEMANAL")
    print("=" * 60)
    print(f"  Período:        últimos {args.days} días")
    print(f"  Categorías:     {args.categories or 'todas'}")
    print(f"  Regiones:       {args.regions or 'global'}")
    print(f"  Clasificación:  {args.classification}")
    print(f"  Inicio:         {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print("=" * 60 + "\n")

    pipeline = WeeklyGeointPipeline()

    try:
        report = await pipeline.run(
            days_back=args.days,
            category_filter=args.categories,
            region_filter=args.regions,
            classification=args.classification,
        )
    except KeyboardInterrupt:
        print("\n[!] Generación interrumpida por el operador.")
        sys.exit(1)
    except Exception as exc:
        print(f"\n[ERROR CRÍTICO] {exc}")
        sys.exit(2)

    print("\n" + "=" * 60)
    print("  INFORME GENERADO EXITOSAMENTE")
    print("=" * 60)
    print(f"  Archivo:        {report.file_path}")
    print(f"  Fuentes totales:{report.total_sources}")
    print(f"  Modelo:         {report.model_used}")
    print(f"  Clasificación:  {report.classification}")
    print("=" * 60)

    if args.output and report.file_path:
        import shutil  # noqa: PLC0415
        shutil.copy2(report.file_path, args.output)
        print(f"\n  Copia exportada a: {args.output}")

    print("\n[OK] Pipeline completado.\n")


if __name__ == "__main__":
    asyncio.run(main())
