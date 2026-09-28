import sqlite3

from flask import Blueprint, request, jsonify

from admin_ingest import ingest_uploaded_pdf
from retrieve import DB_PATH


# ============================================================
# ADMIN BLUEPRINT
# ============================================================

admin_bp = Blueprint(
    "admin",
    __name__,
    url_prefix="/admin"
)


# ============================================================
# DATABASE CONNECTION
# ============================================================

def get_db_connection():
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


# ============================================================
# CREATE SUBJECT
# ============================================================

@admin_bp.route("/subjects", methods=["POST"])
def create_subject():

    data = request.get_json()

    if not data:
        return jsonify({
            "error": "No JSON data received"
        }), 400

    name = data.get("name")
    code = data.get("code")
    semester = data.get("semester")

    if not name:
        return jsonify({
            "error": "Subject name is required"
        }), 400

    name = name.strip()

    if not name:
        return jsonify({
            "error": "Subject name cannot be empty"
        }), 400

    if semester is not None:
        try:
            semester = int(semester)
        except (ValueError, TypeError):
            return jsonify({
                "error": "Semester must be an integer"
            }), 400

    connection = get_db_connection()

    try:
        cursor = connection.execute(
            """
            INSERT INTO subjects
            (
                name,
                code,
                semester
            )
            VALUES (?, ?, ?)
            """,
            (
                name,
                code,
                semester
            )
        )

        connection.commit()
        subject_id = cursor.lastrowid

    except sqlite3.IntegrityError as e:

        connection.close()

        return jsonify({
            "error": str(e)
        }), 400

    connection.close()

    return jsonify({
        "message": "Subject created successfully",
        "subject": {
            "id": subject_id,
            "name": name,
            "code": code,
            "semester": semester
        }
    }), 201


# ============================================================
# GET ALL SUBJECTS
# ============================================================

@admin_bp.route("/subjects", methods=["GET"])
def get_subjects():

    connection = get_db_connection()

    rows = connection.execute(
        """
        SELECT
            id,
            name,
            code,
            semester,
            created_at
        FROM subjects
        ORDER BY id
        """
    ).fetchall()

    connection.close()

    subjects = []

    for row in rows:

        subjects.append({
            "id": row["id"],
            "name": row["name"],
            "code": row["code"],
            "semester": row["semester"],
            "created_at": row["created_at"]
        })

    return jsonify({
        "subjects": subjects
    })


# ============================================================
# GET ALL UPLOADED DOCUMENTS
# ============================================================

@admin_bp.route("/documents", methods=["GET"])
def get_documents():

    connection = get_db_connection()

    rows = connection.execute(
        """
        SELECT
            documents.id,
            documents.filename,
            documents.doc_type,
            documents.uploaded_at,
            subjects.id AS subject_id,
            subjects.name AS subject_name,
            subjects.code AS subject_code
        FROM documents
        JOIN subjects
            ON documents.subject_id = subjects.id
        ORDER BY documents.id
        """
    ).fetchall()

    connection.close()

    documents = []

    for row in rows:

        documents.append({
            "id": row["id"],
            "filename": row["filename"],
            "doc_type": row["doc_type"],
            "uploaded_at": row["uploaded_at"],
            "subject_id": row["subject_id"],
            "subject_name": row["subject_name"],
            "subject_code": row["subject_code"]
        })

    return jsonify({
        "documents": documents
    })


# ============================================================
# GET CHUNKS OF A DOCUMENT
# ============================================================

@admin_bp.route("/documents/<int:document_id>/chunks", methods=["GET"])
def get_document_chunks(document_id):

    connection = get_db_connection()

    # --------------------------------------------------------
    # Check whether document exists
    # --------------------------------------------------------

    document = connection.execute(
        """
        SELECT
            documents.id,
            documents.filename,
            documents.doc_type,
            documents.subject_id,
            subjects.name AS subject_name
        FROM documents
        JOIN subjects
            ON documents.subject_id = subjects.id
        WHERE documents.id = ?
        """,
        (document_id,)
    ).fetchone()

    if not document:

        connection.close()

        return jsonify({
            "error": "Document not found"
        }), 404

    # --------------------------------------------------------
    # Get chunks
    # --------------------------------------------------------

    rows = connection.execute(
        """
        SELECT
            id,
            chunk_text,
            page_number,
            chunk_index,
            faiss_vector_id,
            created_at
        FROM chunks
        WHERE document_id = ?
        ORDER BY page_number, chunk_index
        """,
        (document_id,)
    ).fetchall()

    connection.close()

    chunks = []

    for row in rows:

        chunks.append({
            "id": row["id"],
            "chunk_text": row["chunk_text"],
            "page_number": row["page_number"],
            "chunk_index": row["chunk_index"],
            "faiss_vector_id": row["faiss_vector_id"],
            "created_at": row["created_at"]
        })

    return jsonify({

        "document": {
            "id": document["id"],
            "filename": document["filename"],
            "doc_type": document["doc_type"],
            "subject_id": document["subject_id"],
            "subject_name": document["subject_name"]
        },

        "total_chunks": len(chunks),

        "chunks": chunks

    })


# ============================================================
# DELETE DOCUMENT
# ============================================================

@admin_bp.route("/documents/<int:document_id>", methods=["DELETE"])
def delete_document(document_id):

    connection = get_db_connection()

    # --------------------------------------------------------
    # Check whether document exists
    # --------------------------------------------------------

    document = connection.execute(
        """
        SELECT
            id,
            filename,
            subject_id
        FROM documents
        WHERE id = ?
        """,
        (document_id,)
    ).fetchone()

    if not document:

        connection.close()

        return jsonify({
            "error": "Document not found"
        }), 404

    # --------------------------------------------------------
    # Delete document
    # --------------------------------------------------------

    try:

        connection.execute(
            """
            DELETE FROM documents
            WHERE id = ?
            """,
            (document_id,)
        )

        connection.commit()

    except Exception as e:

        connection.rollback()
        connection.close()

        print("[DELETE ERROR]", e)

        return jsonify({
            "error": "Failed to delete document"
        }), 500

    connection.close()

    return jsonify({

        "message": "Document deleted successfully",

        "document": {
            "id": document["id"],
            "filename": document["filename"],
            "subject_id": document["subject_id"]
        }

    })


# ============================================================
# UPLOAD PDF
# ============================================================

@admin_bp.route("/upload", methods=["POST"])
def upload_pdf():

    subject_id = request.form.get("subject_id")

    if not subject_id:

        return jsonify({
            "error": "subject_id is required"
        }), 400

    try:

        subject_id = int(subject_id)

    except (ValueError, TypeError):

        return jsonify({
            "error": "subject_id must be an integer"
        }), 400

    doc_type = request.form.get("doc_type")

    allowed_types = [
        "syllabus",
        "notes",
        "pyq"
    ]

    if doc_type not in allowed_types:

        return jsonify({
            "error": "doc_type must be syllabus, notes, or pyq"
        }), 400

    if "file" not in request.files:

        return jsonify({
            "error": "PDF file is required"
        }), 400

    file = request.files["file"]

    if not file.filename:

        return jsonify({
            "error": "No file selected"
        }), 400

    if not file.filename.lower().endswith(".pdf"):

        return jsonify({
            "error": "Only PDF files are allowed"
        }), 400

    connection = get_db_connection()

    subject = connection.execute(
        """
        SELECT
            id,
            name
        FROM subjects
        WHERE id = ?
        """,
        (subject_id,)
    ).fetchone()

    connection.close()

    if not subject:

        return jsonify({
            "error": "Subject not found"
        }), 404

    # --------------------------------------------------------
    # Create upload folder
    # --------------------------------------------------------

    import os

    upload_folder = "data/uploads"

    os.makedirs(
        upload_folder,
        exist_ok=True
    )

    # --------------------------------------------------------
    # Save PDF
    # --------------------------------------------------------

    filepath = os.path.join(
        upload_folder,
        file.filename
    )

    file.save(filepath)

    # --------------------------------------------------------
    # Process PDF
    # --------------------------------------------------------

    try:

        result = ingest_uploaded_pdf(
            filepath,
            subject_id,
            doc_type
        )

    except Exception as e:

        print("[UPLOAD ERROR]", e)

        return jsonify({
            "error": "Failed to process PDF."
        }), 500

    # --------------------------------------------------------
    # Return result
    # --------------------------------------------------------

    return jsonify({

        "message": "PDF uploaded and processed successfully",

        "subject": {
            "id": subject["id"],
            "name": subject["name"]
        },

        "document": result

    }), 201