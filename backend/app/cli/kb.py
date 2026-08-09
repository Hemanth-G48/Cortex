"""Second Brain CLI (Phase 2 + Phase 3).

Usage:
    python -m app.cli.kb reindex [--source <id>] [--user <id>]  # Phase 2 dirty-flag reindex
    python -m app.cli.kb backfill [--source <id>] [--user <id>]  # Phase 2 full reindex
    python -m app.cli.kb stats [--user <id>]                     # Phase 2 per-user stats
    python -m app.cli.kb rebuild-fts          # rebuild the FTS5 index
    python -m app.cli.kb eval [--mode hybrid] # run retrieval evaluation

Phase 2 commands (reindex/backfill/stats) live here; Phase 3 commands share
this module additively.
"""

from __future__ import annotations

import argparse
import sys

from app.database import SessionLocal, engine


def cmd_reindex(source_id: int | None, user_id: int | None) -> int:
    """Run the Phase 2 incremental reindex coordinator (phrase 91)."""
    from app.services.kb import reindex as reindex_service

    db = SessionLocal()
    try:
        uid = user_id or 1
        summary = reindex_service.reindex_documents(
            db, uid, source_id=source_id
        )
        print(
            f"reindex user={uid} source={source_id or 'all'}  "
            f"docs={summary['documents']} embedded={summary['embedded']} "
            f"tags={summary['tags']} concepts={summary['concepts']} "
            f"edges={summary['edges']} neardup={summary['neardup_pairs']} "
            f"vectors={summary['synced_vectors']} dirty_left={summary['dirty_remaining']}"
        )
        return 0
    finally:
        db.close()


def cmd_backfill(source_id: int | None, user_id: int | None) -> int:
    """Mark everything dirty and run a full reindex (phrase 92/99)."""
    from app.services.kb import reindex as reindex_service

    db = SessionLocal()
    try:
        uid = user_id or 1
        summary = reindex_service.backfill(db, uid, source_id=source_id)
        print(
            f"backfill user={uid} source={source_id or 'all'}  "
            f"marked={summary['marked_dirty']} docs={summary['documents']} "
            f"embedded={summary['embedded']} neardup={summary['neardup_pairs']} "
            f"vectors={summary['synced_vectors']} dirty_left={summary['dirty_remaining']}"
        )
        return 0
    finally:
        db.close()


def cmd_stats(user_id: int | None) -> int:
    """Print per-user Knowledge Core statistics (phrase 20)."""
    from app.services.kb.embedder import stats

    db = SessionLocal()
    try:
        uid = user_id or 1
        data = stats(db, uid)
        for key, value in data.items():
            print(f"{key:<22} {value}")
        return 0
    finally:
        db.close()


def rebuild_fts() -> int:
    """Rebuild the FTS5 index from kb_chunks (Idea 21, phrase 10)."""
    from app.services.kb import fts

    fts.ensure_fts_schema(engine)
    backend = fts.get_fts_backend()
    count = backend.rebuild(engine)
    print(f"FTS index rebuilt: {count} rows")
    return 0


def run_eval(mode: str, user_id: int | None) -> int:
    """Run retrieval evaluation over the golden sets (Idea 26, phrase 53)."""
    from app.services.kb.eval_harness import DEFAULT_FIXTURE_DIR, run_eval

    db = SessionLocal()
    try:
        uid = user_id or 1
        runs = run_eval(db, uid, mode=mode)
        if not runs:
            print(f"No golden sets found under {DEFAULT_FIXTURE_DIR}")
            return 1
        print(f"mode={mode}  golden sets={len(runs)}")
        for run in runs:
            print(
                f"  {run['golden_set']:<20} "
                f"recall={run['recall@k']:.3f} precision={run['precision@k']:.3f} "
                f"mrr={run['mrr']:.3f}"
            )
        return 0
    finally:
        db.close()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m app.cli.kb")
    sub = parser.add_subparsers(dest="command", required=True)

    # ── Phase 2: reindex / backfill / stats (Idea 20) ──
    reindex_p = sub.add_parser("reindex", help="Incremental reindex (dirty docs)")
    reindex_p.add_argument("--source", type=int, default=None, help="Source id to scope")
    reindex_p.add_argument("--user-id", type=int, default=None, dest="user_id")

    backfill_p = sub.add_parser("backfill", help="Mark all docs dirty + full reindex")
    backfill_p.add_argument("--source", type=int, default=None, help="Source id to scope")
    backfill_p.add_argument("--user-id", type=int, default=None, dest="user_id")

    stats_p = sub.add_parser("stats", help="Print per-user Knowledge Core stats")
    stats_p.add_argument("--user-id", type=int, default=None, dest="user_id")

    # ── Phase 3 ──
    sub.add_parser("rebuild-fts", help="Rebuild the FTS5 index")

    eval_p = sub.add_parser("eval", help="Run retrieval evaluation")
    eval_p.add_argument("--mode", default="hybrid",
                        choices=["keyword", "semantic", "hybrid"])
    eval_p.add_argument("--user-id", type=int, default=None)

    args = parser.parse_args(argv)
    if args.command == "reindex":
        return cmd_reindex(args.source, args.user_id)
    if args.command == "backfill":
        return cmd_backfill(args.source, args.user_id)
    if args.command == "stats":
        return cmd_stats(args.user_id)
    if args.command == "rebuild-fts":
        return rebuild_fts()
    if args.command == "eval":
        return run_eval(args.mode, args.user_id)
    return 1


if __name__ == "__main__":
    sys.exit(main())
