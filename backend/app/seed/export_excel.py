"""Regenerate examples/sample-plan.xlsx from the seeded demo plan.

Usage (from backend/ with venv active):
  python -m app.seed.export_excel
  python -m app.seed.export_excel --out ../examples/sample-plan.xlsx
"""

from __future__ import annotations

import argparse
from pathlib import Path

from app.db.session import SessionLocal, init_db
from app.excel.service import export_xlsx
from app.repositories import PlanRepository
from app.seed import seed_demo_plan
from app.services.plan_service import PlanService

# repo root / examples / sample-plan.xlsx
DEFAULT_OUT = Path(__file__).resolve().parents[3] / "examples" / "sample-plan.xlsx"


def export_sample_excel(out: Path, *, force_seed: bool = True) -> Path:
    init_db()
    session = SessionLocal()
    try:
        seed_demo_plan(session, force=force_seed)
        plan = PlanService(PlanRepository(session)).get_active_plan()
        blob = export_xlsx(plan)
    finally:
        session.close()

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(blob)
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description="Export seed plan to sample Excel")
    parser.add_argument(
        "--out",
        type=Path,
        default=DEFAULT_OUT,
        help=f"Output path (default: {DEFAULT_OUT})",
    )
    parser.add_argument(
        "--no-reseed",
        action="store_true",
        help="Do not force-reseed; export active plan as-is",
    )
    args = parser.parse_args()
    path = export_sample_excel(args.out, force_seed=not args.no_reseed)
    print(f"Wrote {path} ({path.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
