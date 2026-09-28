"""
retrieve.py
-----------

Block 2: Retrieval

Flow:

1. Take the student's question.
2. Convert the question into an embedding.
3. Search the FAISS index.
4. Check the similarity threshold.
5. Get matching chunks from SQLite.
6. Filter results by subject when subject_id is provided.
7. If a strong heading is found, retrieve the nearby
   chunks belonging to that section.
8. Return chunk text + chunk ID + source + page + similarity.
"""

import sqlite3
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer


# ============================================================
# CONFIGURATION
# ============================================================

DB_PATH = "db/chatbot.db"

INDEX_PATH = "vector_store/dsml.index"

CHUNK_IDS_PATH = "vector_store/chunk_ids.npy"

MODEL_NAME = "all-MiniLM-L6-v2"

# Number of semantic results finally used
TOP_K = 5

# Search more results internally so that after subject filtering
# we still have enough relevant results.
SEARCH_K = 50

# Minimum similarity required for a normal semantic result
SIMILARITY_THRESHOLD = 0.3

# If the strongest result has a similarity above this
# and looks like a heading, we expand the section.
HEADING_SIMILARITY_THRESHOLD = 0.6

# Number of chunks to retrieve after a strong heading
SECTION_NEIGHBORS = 7

# Maximum number of chunks finally returned
MAX_CONTEXT_CHUNKS = 12


# ============================================================
# LOAD RESOURCES
# ============================================================

def load_resources():
    """
    Load the FAISS index, chunk-ID mapping,
    and Sentence Transformer model.

    These resources are loaded only once.
    """

    print("[debug] Loading retrieval resources...")

    # Load FAISS index
    index = faiss.read_index(
        INDEX_PATH
    )

    # Load mapping between FAISS positions
    # and SQLite chunk IDs
    chunk_ids = np.load(
        CHUNK_IDS_PATH,
        allow_pickle=True
    )

    # Load Sentence Transformer model
    model = SentenceTransformer(
        MODEL_NAME
    )

    print("[debug] Retrieval resources loaded.")

    return index, chunk_ids, model


# ============================================================
# LOAD EVERYTHING ONCE
# ============================================================

# These are loaded only once when retrieve.py starts.

INDEX, CHUNK_IDS, MODEL = load_resources()


# ============================================================
# EMBED QUESTION
# ============================================================

def embed_query(model, question):
    """
    Convert the student's question into
    an embedding vector.
    """

    vector = model.encode(
        [question],
        convert_to_numpy=True
    )

    vector = vector.astype(
        "float32"
    )

    # Normalize the query vector because
    # the FAISS index uses inner-product similarity.
    faiss.normalize_L2(
        vector
    )

    return vector


# ============================================================
# SEARCH FAISS
# ============================================================

def search_index(
    index,
    query_vector,
    top_k=SEARCH_K
):
    """
    Search the FAISS index.
    """

    similarities, positions = index.search(
        query_vector,
        top_k
    )

    return similarities[0], positions[0]


# ============================================================
# GET CHUNK DETAILS
# ============================================================

def get_chunk_details(
    cursor,
    chunk_id
):
    """
    Retrieve complete information about
    one chunk from SQLite.

    subject_id is included so that results
    can be filtered by subject.
    """

    cursor.execute(
        """
        SELECT
            chunks.id,
            chunks.document_id,
            chunks.chunk_text,
            chunks.page_number,
            chunks.chunk_index,
            documents.filename,
            documents.subject_id
        FROM chunks
        JOIN documents
            ON chunks.document_id = documents.id
        WHERE chunks.id = ?
        """,
        (int(chunk_id),)
    )

    return cursor.fetchone()


# ============================================================
# GET SECTION NEIGHBORS
# ============================================================

def get_section_neighbors(
    cursor,
    document_id,
    chunk_index,
    number_of_chunks
):
    """
    Retrieve chunks immediately following
    a strong heading from the same document.
    """

    cursor.execute(
        """
        SELECT
            chunks.id,
            chunks.document_id,
            chunks.chunk_text,
            chunks.page_number,
            chunks.chunk_index,
            documents.filename,
            documents.subject_id
        FROM chunks
        JOIN documents
            ON chunks.document_id = documents.id
        WHERE chunks.document_id = ?
          AND chunks.chunk_index > ?
        ORDER BY chunks.chunk_index ASC
        LIMIT ?
        """,
        (
            int(document_id),
            int(chunk_index),
            int(number_of_chunks)
        )
    )

    return cursor.fetchall()


# ============================================================
# CHECK WHETHER CHUNK LOOKS LIKE A HEADING
# ============================================================

def looks_like_heading(chunk_text):
    """
    Simple heading detection.

    Many extracted PDF headings are short pieces of text.
    """

    cleaned = " ".join(
        chunk_text.split()
    ).strip()

    if not cleaned:
        return False

    # Short extracted chunks are likely to be headings.
    if len(cleaned) <= 100:
        return True

    return False


# ============================================================
# CONVERT DATABASE ROW TO RESULT DICTIONARY
# ============================================================

def make_result(
    row,
    similarity
):
    """
    Convert a database row into the dictionary
    format used by the chatbot.
    """

    (
        chunk_id,
        document_id,
        chunk_text,
        page_number,
        chunk_index,
        filename,
        subject_id
    ) = row

    return {
        "chunk_id": int(chunk_id),
        "document_id": int(document_id),
        "chunk_text": chunk_text,
        "page_number": page_number,
        "chunk_index": chunk_index,
        "filename": filename,
        "subject_id": int(subject_id),
        "similarity": float(similarity)
    }


# ============================================================
# RETRIEVE
# ============================================================

def retrieve(question, subject_id=None):

    # --------------------------------------------------------
    # STEP 1: Use already-loaded resources
    # --------------------------------------------------------

    index = INDEX
    chunk_ids = CHUNK_IDS
    model = MODEL

    # --------------------------------------------------------
    # STEP 2: Convert question into embedding
    # --------------------------------------------------------

    query_vector = embed_query(
        model,
        question
    )

    # --------------------------------------------------------
    # STEP 3: Search FAISS
    # --------------------------------------------------------

    similarities, positions = search_index(
        index,
        query_vector
    )

    print(
        "\n[debug] raw similarities "
        "(before threshold filtering):",
        [
            round(float(s), 4)
            for s in similarities[:TOP_K]
        ]
    )

    if subject_id is not None:
        print(
            f"[debug] filtering results for subject_id={subject_id}"
        )

    # --------------------------------------------------------
    # STEP 4: Open SQLite database
    # --------------------------------------------------------

    conn = sqlite3.connect(
        DB_PATH
    )

    cursor = conn.cursor()

    semantic_results = []

    # --------------------------------------------------------
    # STEP 5: Get semantic search results
    # --------------------------------------------------------

    for similarity, position in zip(
        similarities,
        positions
    ):

        # Ignore invalid FAISS positions
        if position == -1:
            continue

        # Ignore results below threshold
        if similarity < SIMILARITY_THRESHOLD:
            continue

        # Convert FAISS position into actual
        # SQLite chunk ID.
        chunk_id = int(
            chunk_ids[position]
        )

        details = get_chunk_details(
            cursor,
            chunk_id
        )

        if not details:
            continue

        # ----------------------------------------------------
        # SUBJECT FILTER
        # ----------------------------------------------------

        result_subject_id = int(
            details[6]
        )

        if (
            subject_id is not None
            and result_subject_id != int(subject_id)
        ):
            continue

        result = make_result(
            details,
            similarity
        )

        result["is_neighbor"] = False

        semantic_results.append(
            result
        )

        # We already have enough results.
        if len(semantic_results) >= TOP_K:
            break

    # --------------------------------------------------------
    # STEP 6: Nothing relevant found
    # --------------------------------------------------------

    if not semantic_results:

        conn.close()

        return {
            "status": "not_covered",

            "message": (
                "Sorry, this isn't covered "
                "in the material I have."
            ),

            "chunks": []
        }

    # --------------------------------------------------------
    # STEP 7: Check strongest result
    # --------------------------------------------------------

    strongest_result = semantic_results[0]

    is_strong_heading = (
        strongest_result["similarity"]
        >= HEADING_SIMILARITY_THRESHOLD

        and

        looks_like_heading(
            strongest_result["chunk_text"]
        )
    )

    # --------------------------------------------------------
    # STEP 8: Section-aware retrieval
    # --------------------------------------------------------

    if is_strong_heading:

        print(
            "\n[debug] Strong heading detected:"
        )

        print(
            f"        "
            f"{strongest_result['chunk_text'][:100]}"
        )

        print(
            "[debug] Retrieving nearby section chunks..."
        )

        neighbors = get_section_neighbors(
            cursor,
            strongest_result["document_id"],
            strongest_result["chunk_index"],
            SECTION_NEIGHBORS
        )

        # IMPORTANT:
        #
        # When a strong heading is detected,
        # we do NOT mix unrelated semantic results
        # with this section.
        #
        # We keep the heading and retrieve its
        # neighboring section content.

        final_results = [
            strongest_result
        ]

        added_chunk_ids = {
            strongest_result["chunk_id"]
        }

        for row in neighbors:

            # Make sure section neighbors are from
            # the same subject when a subject was supplied.
            neighbor_subject_id = int(row[6])

            if (
                subject_id is not None
                and neighbor_subject_id != int(subject_id)
            ):
                continue

            chunk_id = int(
                row[0]
            )

            # Avoid duplicate chunks
            if chunk_id in added_chunk_ids:
                continue

            result = make_result(
                row,
                similarity=0.0
            )

            result["is_neighbor"] = True

            final_results.append(
                result
            )

            added_chunk_ids.add(
                chunk_id
            )

            if len(final_results) >= MAX_CONTEXT_CHUNKS:
                break

    else:

        # ----------------------------------------------------
        # No strong heading found.
        #
        # Use normal FAISS semantic retrieval.
        # ----------------------------------------------------

        final_results = []

        added_chunk_ids = set()

        for result in semantic_results:

            chunk_id = result["chunk_id"]

            if chunk_id in added_chunk_ids:
                continue

            result["is_neighbor"] = False

            final_results.append(
                result
            )

            added_chunk_ids.add(
                chunk_id
            )

    # --------------------------------------------------------
    # STEP 9: Limit final context size
    # --------------------------------------------------------

    final_results = final_results[
        :MAX_CONTEXT_CHUNKS
    ]

    # --------------------------------------------------------
    # STEP 10: Close database
    # --------------------------------------------------------

    conn.close()

    # --------------------------------------------------------
    # STEP 11: Return results
    # --------------------------------------------------------

    return {
        "status": "found",

        "message": (
            f"Found {len(final_results)} "
            f"relevant chunk(s)."
        ),

        "chunks": final_results
    }


# ============================================================
# TESTING
# ============================================================

if __name__ == "__main__":

    question = input(
        "Ask a question: "
    )

    # --------------------------------------------------------
    # TEMPORARY DSML TEST
    #
    # DSML subject ID in your current database is 1.
    #
    # Later the Flask API will pass the selected subject_id
    # automatically.
    # --------------------------------------------------------

    result = retrieve(
        question,
        subject_id=1
    )

    print(
        "\n--- RESULT ---"
    )

    print(
        result["message"]
    )

    for i, chunk in enumerate(
        result["chunks"],
        start=1
    ):

        print(
            f"\nChunk {i} "
            f"| ID: {chunk['chunk_id']} "
            f"| similarity: "
            f"{chunk['similarity']:.4f}"
        )

        print(
            f"Subject ID: "
            f"{chunk['subject_id']}"
        )

        print(
            f"Source: "
            f"{chunk['filename']}, "
            f"page {chunk['page_number']}"
        )

        print(
            chunk["chunk_text"][:300]
            + "..."
        )