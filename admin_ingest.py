import sqlite3
import pdfplumber
from pathlib import Path

from retrieve import DB_PATH


CHUNK_WORD_LIMIT = 300
CHUNK_OVERLAP = 50


def chunk_words(words, limit=CHUNK_WORD_LIMIT, overlap=CHUNK_OVERLAP):
    """Split words into overlapping chunks."""

    if not words:
        return []

    chunks = []
    start = 0

    while start < len(words):
        end = start + limit

        chunk = " ".join(words[start:end])
        chunks.append(chunk)

        if end >= len(words):
            break

        start = end - overlap

    return chunks


def ingest_uploaded_pdf(filepath, subject_id, doc_type):
    """
    Process an uploaded PDF.

    PDF
      ↓
    Extract text
      ↓
    Create chunks
      ↓
    Store document + chunks in SQLite
    """

    filepath = Path(filepath)
    filename = filepath.name

    connection = sqlite3.connect(DB_PATH)
    connection.execute("PRAGMA foreign_keys = ON")

    # Check whether this file already exists for this subject
    existing = connection.execute(
        """
        SELECT id
        FROM documents
        WHERE subject_id = ? AND filename = ?
        """,
        (subject_id, filename)
    ).fetchone()

    if existing:
        connection.close()

        return {
            "success": False,
            "message": "This file already exists for this subject."
        }

    # Add document record
    cursor = connection.execute(
        """
        INSERT INTO documents
        (subject_id, filename, doc_type)
        VALUES (?, ?, ?)
        """,
        (subject_id, filename, doc_type)
    )

    document_id = cursor.lastrowid

    total_chunks = 0
    skipped_pages = []

    try:

        # Open PDF
        with pdfplumber.open(filepath) as pdf:

            # Process each page
            for page_number, page in enumerate(pdf.pages, start=1):

                text = page.extract_text()

                # If no text was extracted
                if not text or not text.strip():
                    skipped_pages.append(page_number)
                    continue

                # Convert text into words
                words = text.split()

                # Create chunks
                chunks = chunk_words(words)

                # Store chunks
                for chunk_index, chunk_text in enumerate(chunks):

                    connection.execute(
                        """
                        INSERT INTO chunks
                        (
                            document_id,
                            chunk_text,
                            page_number,
                            chunk_index
                        )
                        VALUES (?, ?, ?, ?)
                        """,
                        (
                            document_id,
                            chunk_text,
                            page_number,
                            chunk_index
                        )
                    )

                    total_chunks += 1

        # Save everything
        connection.commit()

    except Exception:

        # Undo database changes if something fails
        connection.rollback()

        connection.execute(
            "DELETE FROM documents WHERE id = ?",
            (document_id,)
        )

        connection.commit()
        connection.close()

        raise

    connection.close()

    return {
        "success": True,
        "document_id": document_id,
        "filename": filename,
        "subject_id": subject_id,
        "doc_type": doc_type,
        "chunks_created": total_chunks,
        "skipped_pages": skipped_pages
    }