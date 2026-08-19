"""Hard-delete a knowledge source and all its index rows (leftover duplicates).

Deletes the source, its documents/chunks/versions/tags, chunk embeddings, graph
edges, folders + saved gap analyses, per-document FK rows (summaries, citations,
quiz links, flashcard candidates, categorize suggestions, outdated notes,
quality suggestions), micro sessions, and detaches linked courses.

Usage (from the backend directory):
    .venv/bin/python scripts/purge_source.py --source 2 [--dry-run]
"""

from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal  # noqa: E402
from app.services.kb.migrate import purge_source  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=int, required=True, help="kb_sources.id to delete")
    parser.add_argument("--dry-run", action="store_true", help="report only, delete nothing")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        report = purge_source(db, args.source, dry_run=args.dry_run)
    finally:
        db.close()
    print(json.dumps(report, indent=2, default=str))


if __name__ == "__main__":
    main()
