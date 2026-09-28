"""
Ingestion & Chunking Script
Syllabus-Grounded Doubt-Solving Chatbot

What it does:
  1. Reads each PDF listed in DOCUMENTS below.
  2. Extracts text page-by-page with pdfplumber.
  3. Splits each page's text into overlapping word-count chunks.
  4. Inserts one row per document into `documents`, one row per
     chunk into `chunks` (each chunk tagged with its exact page number).

Scope (deliberately limited for now):
  - Handles clean, text-extractable PDFs only (this is true of all 5
    DSML files per test_read.py). Image-only / scanned pages are
    skipped and printed as a warning -- OCR fallback comes later.
  - PYQ question/topic tagging (the pyq_tags table) is a separate
    step, not done here.

Run:
  python ingest.py
"""

import sqlite3
import pdfplumber
from pathlib import Path

# ------------------------------------------------------------------
# CONFIG -- edit this section for each subject / ingestion run
# ------------------------------------------------------------------

DB_PATH = "db/chatbot.db"
DATA_DIR = Path("data/dsml")   # folder holding this subject's PDFs

SUBJECT = {
    "name": "Data Science and Machine Learning",
    "code": "DSML",      # set to your real subject code if you have one
    "semester": 3,        # set to the correct semester
}

# filename -> doc_type. doc_type MUST be one of: 'syllabus', 'notes', 'pyq'
# (this matches the CHECK constraint on the documents table)
DOCUMENTS = {
    "DSML_syllabus.pdf": "syllabus",
    "module1_notes.pdf": "notes",
    "module2_notes.pdf": "notes",
    "pyq1.pdf": "pyq",
    "pyq2.pdf": "pyq",
}

CHUNK_WORD_LIMIT = 300   # target words per chunk
CHUNK_OVERLAP = 50       # words repeated between consecutive chunks on a page

# ------------------------------------------------------------------


def get_or_create_subject(conn, subject):
    """Look up the subject by (name, code); insert it if it doesn't exist yet.
    Safe to re-run -- won't create duplicate subject rows."""
    cur = conn.execute(
        "SELECT id FROM subjects WHERE name = ? AND code IS ?",
        (subject["name"], subject["code"]),
    )
    row = cur.fetchone()
    if row:
        return row[0]

    cur = conn.execute(
        "INSERT INTO subjects (name, code, semester) VALUES (?, ?, ?)",
        (subject["name"], subject["code"], subject["semester"]),
    )
    conn.commit()
    return cur.lastrowid


def chunk_words(words, limit, overlap):
    """Split a list of words into overlapping chunks of `limit` words,
    with `overlap` words repeated at the start of each chunk after the first."""
    if not words:
        return []
    chunks = []
    start = 0
    while start < len(words):
        end = start + limit
        chunks.append(" ".join(words[start:end]))
        if end >= len(words):
            break
        start = end - overlap
    return chunks


def ingest_pdf(conn, filepath, doc_type, subject_id):
    filename = filepath.name

    # Skip if this exact file has already been ingested for this subject --
    # prevents duplicate chunks if the script gets run twice.
    existing = conn.execute(
        "SELECT id FROM documents WHERE subject_id = ? AND filename = ?",
        (subject_id, filename),
    ).fetchone()
    if existing:
        return None, []  # signal "already ingested" to the caller

    cur = conn.execute(
        "INSERT INTO documents (subject_id, filename, doc_type) VALUES (?, ?, ?)",
        (subject_id, filename, doc_type),
    )
    document_id = cur.lastrowid
    conn.commit()

    chunk_index = 0
    total_chunks = 0
    skipped_pages = []

    with pdfplumber.open(filepath) as pdf:
        for page_num, page in enumerate(pdf.pages, start=1):
            text = page.extract_text()
            if not text or not text.strip():
                skipped_pages.append(page_num)
                continue  # likely an image-only page; OCR pass handles this later

            words = text.split()
            for chunk_text in chunk_words(words, CHUNK_WORD_LIMIT, CHUNK_OVERLAP):
                conn.execute(
                    """INSERT INTO chunks
                       (document_id, chunk_text, page_number, chunk_index)
                       VALUES (?, ?, ?, ?)""",
                    (document_id, chunk_text, page_num, chunk_index),
                )
                chunk_index += 1
                total_chunks += 1

    conn.commit()
    return total_chunks, skipped_pages


def main():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON;")

    subject_id = get_or_create_subject(conn, SUBJECT)
    print(f"Subject '{SUBJECT['name']}' -> subject_id {subject_id}\n")

    grand_total = 0
    for filename, doc_type in DOCUMENTS.items():
        filepath = DATA_DIR / filename
        if not filepath.exists():
            print(f"  [SKIP] {filename} -- not found in {DATA_DIR}")
            continue

        count, skipped = ingest_pdf(conn, filepath, doc_type, subject_id)
        if count is None:
            print(f"  [SKIP] {filename} -- already ingested for this subject")
            continue
        grand_total += count
        note = f" (pages with no extractable text: {skipped})" if skipped else ""
        print(f"  [OK] {filename} ({doc_type}) -> {count} chunks{note}")

    print(f"\nDone. {grand_total} chunks inserted across {len(DOCUMENTS)} documents.")
    conn.close()


if __name__ == "__main__":
    main()
