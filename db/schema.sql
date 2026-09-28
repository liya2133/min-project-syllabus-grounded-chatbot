-- ============================================
-- Syllabus-Grounded Doubt-Solving Chatbot
-- Database Schema (SQLite)
-- ============================================

-- Turn on foreign key checks (SQLite has them off by default)
PRAGMA foreign_keys = ON;

-- ---------------------------------------------
-- 1. USERS
-- Students and faculty who use the system
-- ---------------------------------------------
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    role TEXT NOT NULL CHECK (role IN ('student', 'faculty', 'admin')),
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- ---------------------------------------------
-- 2. SUBJECTS
-- One row per subject, e.g. "DSML", "DAA"
-- ---------------------------------------------
CREATE TABLE subjects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    code TEXT,                     -- e.g. "20MCA201"
    semester INTEGER,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- ---------------------------------------------
-- 3. DOCUMENTS
-- One row per uploaded PDF (syllabus, notes, PYQ)
-- ---------------------------------------------
CREATE TABLE documents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    subject_id INTEGER NOT NULL,
    filename TEXT NOT NULL,
    doc_type TEXT NOT NULL CHECK (doc_type IN ('syllabus', 'notes', 'pyq')),
    uploaded_by INTEGER,           -- references users.id (faculty/admin)
    uploaded_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (subject_id) REFERENCES subjects(id) ON DELETE CASCADE,
    FOREIGN KEY (uploaded_by) REFERENCES users(id) ON DELETE SET NULL
);

-- ---------------------------------------------
-- 4. CHUNKS
-- Small pieces of text extracted from each document.
-- The actual vector embeddings live in FAISS;
-- this table stores the text + metadata + a way to
-- map back from a FAISS result to this row.
-- ---------------------------------------------
CREATE TABLE chunks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    document_id INTEGER NOT NULL,
    chunk_text TEXT NOT NULL,
    page_number INTEGER,
    chunk_index INTEGER,           -- order of this chunk within the document
    faiss_vector_id INTEGER,       -- the index/id of this chunk's vector in FAISS
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE
);

-- ---------------------------------------------
-- 5. PYQ_TAGS
-- Extra metadata for chunks that come from PYQ documents.
-- Powers the exam-relevance / frequency feature.
-- ---------------------------------------------
CREATE TABLE pyq_tags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chunk_id INTEGER NOT NULL,
    topic TEXT,                    -- e.g. "Normalization", "Decision Trees"
    year INTEGER,
    marks INTEGER,
    question_type TEXT,            -- e.g. "short answer", "essay"
    FOREIGN KEY (chunk_id) REFERENCES chunks(id) ON DELETE CASCADE
);

-- ---------------------------------------------
-- 6. QUERIES_LOG
-- Every question asked and the answer given.
-- This is what your evaluation module will analyze later.
-- ---------------------------------------------
CREATE TABLE queries_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    subject_id INTEGER,
    question TEXT NOT NULL,
    answer TEXT,
    retrieved_chunk_ids TEXT,      -- store as comma-separated ids or JSON array
    was_answered INTEGER DEFAULT 1, -- 0 = "not covered" response was given
    confidence_score REAL,
    asked_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL,
    FOREIGN KEY (subject_id) REFERENCES subjects(id) ON DELETE SET NULL
);

-- ---------------------------------------------
-- Helpful indexes for faster lookups
-- ---------------------------------------------
CREATE INDEX idx_documents_subject ON documents(subject_id);
CREATE INDEX idx_chunks_document ON chunks(document_id);
CREATE INDEX idx_pyq_tags_chunk ON pyq_tags(chunk_id);
CREATE INDEX idx_queries_subject ON queries_log(subject_id);
