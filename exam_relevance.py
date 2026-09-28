import sqlite3

from retrieve import DB_PATH


# ============================================================
# GET EXAM RELEVANCE
# ============================================================

def get_exam_relevance(question, subject_id=None):
    """
    Find previous-year questions related to the student's
    question.

    If subject_id is provided, only PYQs belonging to that
    subject are considered.

    PYQ subject is determined through:

        pyq_questions
              ↓ document_id
        documents
              ↓ subject_id
        subjects
    """

    # --------------------------------------------------------
    # Convert question into useful keywords
    # --------------------------------------------------------

    keywords = question.lower().strip().split()

    stop_words = {
        "what",
        "is",
        "are",
        "the",
        "a",
        "an",
        "of",
        "in",
        "on",
        "for",
        "to",
        "and",
        "explain",
        "define",
        "describe",
        "give",
        "with",
        "about",
        "how",
        "why",
        "difference",
        "between"
    }

    keywords = [
        word
        for word in keywords
        if word not in stop_words
    ]

    # --------------------------------------------------------
    # No useful keywords
    # --------------------------------------------------------

    if not keywords:

        return {
            "found": False,
            "count": 0,
            "questions": []
        }

    # --------------------------------------------------------
    # Build phrase
    # --------------------------------------------------------

    phrase = " ".join(keywords)

    connection = sqlite3.connect(DB_PATH)

    connection.row_factory = sqlite3.Row

    # ========================================================
    # STEP 1
    # Search exact phrase
    # ========================================================

    if subject_id is not None:

        cursor = connection.execute(
            """
            SELECT
                pq.question_number,
                pq.part,
                pq.module,
                pq.question_text,
                pq.year,
                pq.marks,
                pq.or_group
            FROM pyq_questions AS pq
            JOIN documents AS d
                ON pq.document_id = d.id
            WHERE LOWER(pq.question_text) LIKE ?
              AND d.subject_id = ?
            """,
            (
                f"%{phrase}%",
                subject_id
            )
        )

    else:

        cursor = connection.execute(
            """
            SELECT
                pq.question_number,
                pq.part,
                pq.module,
                pq.question_text,
                pq.year,
                pq.marks,
                pq.or_group
            FROM pyq_questions AS pq
            WHERE LOWER(pq.question_text) LIKE ?
            """,
            (
                f"%{phrase}%",
            )
        )

    rows = cursor.fetchall()

    # ========================================================
    # STEP 2
    # If exact phrase not found,
    # search using ALL keywords
    # ========================================================

    if not rows and len(keywords) > 1:

        conditions = []

        parameters = []

        for keyword in keywords:

            conditions.append(
                "LOWER(pq.question_text) LIKE ?"
            )

            parameters.append(
                f"%{keyword}%"
            )

        where_clause = " AND ".join(
            conditions
        )

        if subject_id is not None:

            query = f"""
                SELECT
                    pq.question_number,
                    pq.part,
                    pq.module,
                    pq.question_text,
                    pq.year,
                    pq.marks,
                    pq.or_group
                FROM pyq_questions AS pq
                JOIN documents AS d
                    ON pq.document_id = d.id
                WHERE {where_clause}
                  AND d.subject_id = ?
            """

            parameters.append(subject_id)

        else:

            query = f"""
                SELECT
                    pq.question_number,
                    pq.part,
                    pq.module,
                    pq.question_text,
                    pq.year,
                    pq.marks,
                    pq.or_group
                FROM pyq_questions AS pq
                WHERE {where_clause}
            """

        rows = connection.execute(
            query,
            parameters
        ).fetchall()

    # --------------------------------------------------------
    # Close database
    # --------------------------------------------------------

    connection.close()

    # ========================================================
    # Convert rows into dictionaries
    # ========================================================

    questions = []

    seen = set()

    for row in rows:

        question_data = {
            "question_number": row["question_number"],
            "part": row["part"],
            "module": row["module"],
            "question_text": row["question_text"],
            "year": row["year"],
            "marks": row["marks"],
            "or_group": row["or_group"]
        }

        # ----------------------------------------------------
        # Remove duplicates
        # ----------------------------------------------------

        unique_key = (
            question_data["year"],
            question_data["question_number"],
            question_data["question_text"]
        )

        if unique_key in seen:
            continue

        seen.add(unique_key)

        questions.append(
            question_data
        )

    # ========================================================
    # Return result
    # ========================================================

    return {
        "found": len(questions) > 0,
        "count": len(questions),
        "questions": questions
    }