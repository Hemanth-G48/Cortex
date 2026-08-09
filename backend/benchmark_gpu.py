#!/usr/bin/env python3
"""GPU benchmark for reindex with fastembed."""
import time
from app.database import SessionLocal
from app.models import KbDocument, KbChunk, KbSource, KbEmbedding
from app.services.kb.embedder import embed_dirty_batch
from app.services.embeddings import backend_embed


def benchmark_gpu():
    """Benchmark reindex with GPU fastembed."""
    db = SessionLocal()
    try:
        # Create test data
        user_id = 1
        
        # Clean up any existing test data first
        db.query(KbEmbedding).filter(KbEmbedding.user_id == user_id).delete()
        db.query(KbChunk).filter(KbChunk.user_id == user_id).delete()
        db.query(KbDocument).filter(KbDocument.user_id == user_id).delete()
        db.query(KbSource).filter(KbSource.name == "GPU Benchmark Source").delete()
        db.commit()
        
        source = KbSource(
            user_id=user_id,
            name="GPU Benchmark Source",
            source_type="local_dir",
            root_path="/tmp/gpu_benchmark",
        )
        db.add(source)
        db.commit()
        db.refresh(source)

        # Create test documents with chunks
        print("Creating test documents...")
        test_texts = [
            "This is a test document about machine learning. " * 20,
            "Another document about deep learning and neural networks. " * 20,
            "A third document about natural language processing. " * 20,
            "Document four about computer vision and image recognition. " * 20,
            "Document five about reinforcement learning and agents. " * 20,
        ] * 20  # Multiply to create more documents for better GPU utilization

        for i, text in enumerate(test_texts):
            doc = KbDocument(
                user_id=user_id,
                source_id=source.id,
                title=f"GPU Benchmark Doc {i+1}",
                path_rel=f"gpu_benchmark_doc_{i+1}.md",
                embedding_dirty=True,
                tags_dirty=True,
                graph_dirty=True,
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

        # Benchmark embed_dirty_batch with GPU
        print("\nBenchmarking embed_dirty_batch with GPU...")
        start = time.time()
        result = embed_dirty_batch(db, user_id, batch_size=256)
        elapsed = time.time() - start
        
        print(f"  Embedded {result['embedded']} chunks in {elapsed:.3f}s")
        print(f"  Skipped {result['skipped']} cached chunks")
        print(f"  Processed {result['docs']} documents in {result['batches']} batches")
        print(f"  Speed: {result['embedded']/elapsed:.2f} chunks/second")

        # Benchmark direct backend_embed with GPU
        print("\nBenchmarking direct backend_embed with GPU...")
        test_batch = ["Test text for GPU benchmarking. " * 50] * 100
        start = time.time()
        vectors, model = backend_embed(test_batch, db=db, user_id=user_id, budget_check=False, force_local=True)
        elapsed = time.time() - start
        
        print(f"  Embedded {len(vectors)} texts in {elapsed:.3f}s")
        print(f"  Model used: {model}")
        print(f"  Speed: {len(vectors)/elapsed:.2f} texts/second")

        # Cleanup
        print("\nCleaning up test data...")
        db.query(KbChunk).filter(KbChunk.user_id == user_id).delete()
        db.query(KbDocument).filter(KbDocument.user_id == user_id).delete()
        db.query(KbSource).filter(KbSource.id == source.id).delete()
        db.commit()
        print("Done!")

    finally:
        db.close()


if __name__ == "__main__":
    benchmark_gpu()
