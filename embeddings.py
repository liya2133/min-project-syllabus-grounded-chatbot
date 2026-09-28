"""
Embedding Generation and FAISS Index Creation
Syllabus-Grounded Doubt-Solving Chatbot
"""

import sqlite3
from pathlib import Path

import numpy as np
import faiss
from sentence_transformers import SentenceTransformer


# --------------------------------------------------
# CONFIGURATION
# --------------------------------------------------

DB_PATH = "db/chatbot.db"

INDEX_DIR = Path("vector_store")
INDEX_DIR.mkdir(exist_ok=True)

FAISS_INDEX_PATH = INDEX_DIR / "dsml.index"
MAPPING_PATH = INDEX_DIR / "chunk_ids.npy"

MODEL_NAME = "all-MiniLM-L6-v2"


# --------------------------------------------------
# LOAD CHUNKS FROM DATABASE
# --------------------------------------------------

def load_chunks():
    conn = sqlite3.connect(DB_PATH)

    cursor = conn.execute(
        """
        SELECT id, chunk_text
        FROM chunks
        ORDER BY id
        """
    )

    rows = cursor.fetchall()
    conn.close()

    return rows


# --------------------------------------------------
# MAIN PROCESS
# --------------------------------------------------

def main():
    print("Loading chunks from the database...")

    rows = load_chunks()

    if not rows:
        print("No chunks found in the database.")
        return

    chunk_ids = [row[0] for row in rows]
    texts = [row[1] for row in rows]

    print(f"Found {len(texts)} chunks.")

    print("Loading Sentence-Transformers model...")

    model = SentenceTransformer(MODEL_NAME)

    print("Generating embeddings...")

    embeddings = model.encode(
        texts,
        show_progress_bar=True,
        convert_to_numpy=True,
        normalize_embeddings=True
    )

    embeddings = np.asarray(embeddings, dtype="float32")

    print(f"Embedding shape: {embeddings.shape}")

    print("Creating FAISS index...")

    dimension = embeddings.shape[1]

    # Inner-product search works like cosine similarity
    # because the embeddings are normalized.
    index = faiss.IndexFlatIP(dimension)

    index.add(embeddings)

    print(f"FAISS index contains {index.ntotal} vectors.")

    print("Saving FAISS index...")

    faiss.write_index(index, str(FAISS_INDEX_PATH))

    print("Saving chunk-ID mapping...")

    np.save(MAPPING_PATH, np.array(chunk_ids, dtype=np.int64))

    print("Updating database with FAISS vector IDs...")

    conn = sqlite3.connect(DB_PATH)

    for faiss_id, chunk_id in enumerate(chunk_ids):
        conn.execute(
            """
            UPDATE chunks
            SET faiss_vector_id = ?
            WHERE id = ?
            """,
            (faiss_id, chunk_id)
        )

    conn.commit()
    conn.close()

    print("\nEmbedding generation completed successfully.")
    print(f"FAISS index saved at: {FAISS_INDEX_PATH}")
    print(f"Chunk mapping saved at: {MAPPING_PATH}")
    print(f"Total vectors created: {len(chunk_ids)}")


if __name__ == "__main__":
    main()