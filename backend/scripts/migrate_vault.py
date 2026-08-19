"""One-time Second Brain vault migration runner (notes/ + daily-life/).

Moves top-level knowledge folders + extractable files into ``notes/``, creates
``daily-life/``, repoints ``kb_sources`` roots at ``notes/``, disables leftover
cross-user duplicate sources, then re-scans to prove zero re-embedding.

Usage (from the backend directory):
    .venv/bin/python scripts/migrate_vault.py [--vault /path/to/second_brain]
        [--dry-run] [--no-backup] [--no-scan]
"""

from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal, migrate_schema  # noqa: E402
from app.services.kb.migrate import run_migration  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vault", default="/home/hemanth/productivity_app/second_brain")
    parser.add_argument("--dry-run", action="store_true", help="plan only, move nothing")
    parser.add_argument("--no-backup", action="store_true", help="skip vault/DB backups")
    parser.add_argument("--no-scan", action="store_true", help="skip the post-migration scan")
    args = parser.parse_args()

    migrate_schema()  # idempotent; ensures sync_source_path exists
    db = SessionLocal()
    try:
        report = run_migration(
            db,
            args.vault,
            backup=not args.no_backup,
            scan=not args.no_scan,
            dry_run=args.dry_run,
        )
    finally:
        db.close()
    print(json.dumps(report, indent=2, default=str))


if __name__ == "__main__":
    main()
