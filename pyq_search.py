import sqlite3

DB_PATH = "db/chatbot.db"


def search_pyqs(topic):
    connection = sqlite3.connect(DB_PATH)

    query = """
        SELECT
            question_number,
            part,
            module,
            question_text,
            year,
            marks,
            or_group
        FROM pyq_questions
        WHERE question_text LIKE ?
        ORDER BY year DESC, question_number
    """

    pattern = f"%{topic}%"

    rows = connection.execute(query, (pattern,)).fetchall()

    connection.close()

    results = []

    for row in rows:
        results.append({
            "question_number": row[0],
            "part": row[1],
            "module": row[2],
            "question_text": row[3],
            "year": row[4],
            "marks": row[5],
            "or_group": row[6]
        })

    return results


if __name__ == "__main__":

    topic = input("Enter topic: ")

    results = search_pyqs(topic)

    if not results:
        print("\nNo PYQ found for this topic.")

    else:
        print(f"\nFound {len(results)} PYQ(s):\n")

        for result in results:
            print(
                f"Q{result['question_number']} | "
                f"Module {result['module']} | "
                f"{result['marks']} marks | "
                f"{result['year']}"
            )

            print(result["question_text"])
            print()