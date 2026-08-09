#!/usr/bin/env python3
"""Benchmark SQLite optimizations for embedding."""
import time
from sqlalchemy import text as sql_text
from app.database import SessionLocal, engine
from app.models import KbDocument, KbChunk, KbSource, KbEmbedding
from app.services.kb.embedder import embed_dirty_batch


def benchmark_sqlite_optimizations():
    """Benchmark with SQLite-specific optimizations."""
    # Enable SQLite optimizations
    with engine.connect() as conn:
        conn.execute(sql_text("PRAGMA journal_mode=WAL"))
        conn.execute(sql_text("PRAGMA synchronous=NORMAL"))
        conn.execute(sql_text("PRAGMA cache_size=-64000"))  # 64MB cache
        conn.execute(sql_text("PRAGMA temp_store=MEMORY"))
    
    db = SessionLocal()
    try:
        user_id = 1
        
        # Clean up
        db.query(KbEmbedding).filter(KbEmbedding.user_id == user_id).delete()
        db.query(KbChunk).filter(KbChunk.user_id == user_id).delete()
        db.query(KbDocument).filter(KbDocument.user_id == user_id).delete()
        db.query(KbSource).filter(KbSource.name == "SQLite Benchmark").delete()
        db.commit()
        
        source = KbSource(
            user_id=user_id,
            name="SQLite Benchmark",
            source_type="local_dir",
            root_path="/tmp/sqlite_benchmark",
        )
        db.add(source)
        db.commit()
        db.refresh(source)

        # Create large dataset
        print("Creating test documents (2000 docs)...")
        test_texts = [
            "This is a test document about machine learning. " * 20,
            "Another document about deep learning and neural networks. " * 20,
            "A third document about natural language processing. " * 20,
        ] * 667  # ~2000 documents

        for i, text in enumerate(test_texts):
            doc = KbDocument(
                user_id=user_id,
                source_id=source.id,
                title=f"SQLite Doc {i+1}",
                path_rel=f"sqlite_doc_{i+1}.md",
                embedding_dirty=True,
            )
            db.add(doc)
            db.commit()
            db.refresh(doc)

            chunk = KbChunk(
                user_id=user_id,
                document_id=doc.id,
                seq=1,
                content=text,
                token_estimate=len(text.split()),
            )
            db.add(chunk)
            db.commit()

        print(f"Created {len(test_texts)} documents with chunks")

        # Benchmark with SQLite optimizations
        print("\n=== SQLite Optimizations Benchmark ===")
        start = time.time()
        result = embed_dirty_batch(db, user_id, batch_size=512)
        elapsed = time.time() - start
        
        print(f"  Embedded {result['embedded']} chunks in {elapsed:.3f}s")
        print(f"  Speed: {result['embedded']/elapsed:.2f} chunks/second")
        print(f"  Batches: {result['batches']}")
        print(f"  Docs processed: {result['docs']}")

        # Cleanup
        print("\nCleaning up...")
        db.query(KbChunk).filter(KbChunk.user_id == user_id).delete()
        db.query(KbDocument).filter(KbDocument.user_id == user_id).delete()
        db.query(KbSource).filter(KbSource.id == source.id).delete()
        db.commit()
        print("Done!")

    finally:
        db.close()


if __name__ == "__main__":
    benchmark_sqlite_optimizations()
