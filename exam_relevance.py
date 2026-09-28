import sqlite3
import re

DB_PATH = "db/chatbot.db"


# ============================================================
# STOP WORDS
# ============================================================

STOP_WORDS = {
    "what",
    "is",
    "are",
    "the",
    "a",
    "an",
    "explain",
    "describe",
    "discuss",
    "define",
    "give",
    "with",
    "and",
    "of",
    "in",
    "on",
    "for",
    "to",
    "how",
    "why",
    "can",
    "you",
    "me",
    "about",
    "tell",
    "does",
    "do",
    "please",
    "different",
    "types",
}


# ============================================================
# GET KEYWORDS
# ============================================================

def get_keywords(text):

    words = re.findall(
        r"[a-zA-Z]+",
        text.lower()
    )

    keywords = []

    for word in words:

        if word in STOP_WORDS:
            continue

        if len(word) <= 2:
            continue

        keywords.append(word)

    return keywords


# ============================================================
# EXAM RELEVANCE
# ============================================================

def get_exam_relevance(topic):

    connection = sqlite3.connect(
        DB_PATH
    )

    keywords = get_keywords(
        topic
    )

    if not keywords:

        connection.close()

        return {
            "found": False,
            "count": 0,
            "questions": []
        }


    # --------------------------------------------------------
    # Search every keyword
    # --------------------------------------------------------

    conditions = []

    parameters = []

    for keyword in keywords:

        conditions.append(
            "LOWER(question_text) LIKE ?"
        )

        parameters.append(
            f"%{keyword}%"
        )


    query = f"""
        SELECT
            question_number,
            module,
            question_text,
            year,
            marks
        FROM pyq_questions
        WHERE {" OR ".join(conditions)}
        ORDER BY year DESC,
                 question_number
    """


    rows = connection.execute(
        query,
        parameters
    ).fetchall()


    connection.close()


    # --------------------------------------------------------
    # Remove duplicate questions
    # --------------------------------------------------------

    unique_questions = {}

    for row in rows:

        question_number = row[0]

        unique_questions[
            question_number
        ] = row


    # --------------------------------------------------------
    # Convert to dictionaries
    # --------------------------------------------------------

    questions = []

    for row in unique_questions.values():

        questions.append(
            {
                "question_number": row[0],
                "module": row[1],
                "question_text": row[2],
                "year": row[3],
                "marks": row[4]
            }
        )


    return {
        "found": len(questions) > 0,
        "count": len(questions),
        "questions": questions
    }


# ============================================================
# TESTING
# ============================================================

if __name__ == "__main__":

    topic = input(
        "Enter topic: "
    )

    result = get_exam_relevance(
        topic
    )

    print("\n--- EXAM RELEVANCE ---")

    if not result["found"]:

        print(
            "No matching PYQ found."
        )

    else:

        print(
            f"Found {result['count']} "
            f"matching question(s).\n"
        )

        for question in result["questions"]:

            print(
                f"Q{question['question_number']} "
                f"| Module: {question['module']} "
                f"| Year: {question['year']} "
                f"| Marks: {question['marks']}"
            )

            print(
                question["question_text"]
            )

            print()