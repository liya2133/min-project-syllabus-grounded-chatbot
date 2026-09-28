import os
import re
import sqlite3
import pdfplumber


# =========================================================
# SETTINGS
# =========================================================

DATA_FOLDER = "data/dsml"
DB_PATH = "db/chatbot.db"


# =========================================================
# FIND PYQ FILES
# =========================================================

def get_pyq_files():

    files = []

    for filename in os.listdir(DATA_FOLDER):

        if (
            filename.lower().startswith("pyq")
            and filename.lower().endswith(".pdf")
        ):
            files.append(
                os.path.join(DATA_FOLDER, filename)
            )

    files.sort()

    return files


# =========================================================
# EXTRACT PDF TEXT
# =========================================================

def extract_pdf_text(pdf_path):

    text = ""

    with pdfplumber.open(pdf_path) as pdf:

        for page in pdf.pages:

            page_text = page.extract_text()

            if page_text:

                text += "\n"
                text += page_text

    return text


# =========================================================
# EXTRACT YEAR
# =========================================================

def extract_year(text):

    matches = re.findall(
        r"\b(19\d{2}|20\d{2})\b",
        text
    )

    if matches:

        return int(matches[0])

    return None


# =========================================================
# CLEAN QUESTION TEXT
# =========================================================

def clean_text(text):

    # Remove page numbers
    text = re.sub(
        r"Page\s+\d+\s+of\s+\d+",
        " ",
        text,
        flags=re.IGNORECASE
    )

    # Remove exam code
    text = re.sub(
        r"\b0520MCA201122203\b",
        " ",
        text
    )

    # Remove (3) and (6)
    text = re.sub(
        r"\s*\((3|6)\)\s*",
        " ",
        text
    )

    # Remove ****
    text = re.sub(
        r"\s*\*{4,}\s*$",
        "",
        text
    )

    # Remove course code
    text = re.sub(
        r"\b20MCA201\b",
        " ",
        text
    )

    # Remove module headers that accidentally
    # became part of the previous question
    text = re.sub(
        r"\s+Module\s+(I|II|III|IV|V)\s*$",
        "",
        text,
        flags=re.IGNORECASE
    )

    # Remove standalone OR at the end
    text = re.sub(
        r"\s+\bOR\b\s*$",
        "",
        text,
        flags=re.IGNORECASE
    )

    # Remove extra spaces
    text = re.sub(
        r"\s+",
        " ",
        text
    )

    return text.strip()


# =========================================================
# GET MODULE
# =========================================================

def get_module(question_number):

    if question_number in [11, 12]:
        return "I"

    elif question_number in [13, 14]:
        return "II"

    elif question_number in [15, 16]:
        return "III"

    elif question_number in [17, 18]:
        return "IV"

    elif question_number in [19, 20]:
        return "V"

    return None


# =========================================================
# GET OR GROUP
# =========================================================

def get_or_group(question_number):

    if question_number in [11, 12]:
        return "11-12"

    elif question_number in [13, 14]:
        return "13-14"

    elif question_number in [15, 16]:
        return "15-16"

    elif question_number in [17, 18]:
        return "17-18"

    elif question_number in [19, 20]:
        return "19-20"

    return None


# =========================================================
# EXTRACT PART A
# =========================================================

def extract_part_a(text):

    questions = []

    match = re.search(
        r"PART A(.*?)(?=PART B)",
        text,
        flags=re.IGNORECASE | re.DOTALL
    )

    if not match:
        return questions

    part_a_text = match.group(1)

    pattern = re.compile(
        r"(?:^|\n)\s*"
        r"(10|[1-9])"
        r"\s+"
        r"(.+?)"
        r"(?=\n\s*(?:10|[1-9])\s+|\Z)",
        flags=re.DOTALL
    )

    matches = pattern.finditer(
        part_a_text
    )

    for match in matches:

        question_number = int(
            match.group(1)
        )

        question_text = clean_text(
            match.group(2)
        )

        if question_text:

            questions.append(
                {
                    "question_number": question_number,
                    "part": "A",
                    "module": None,
                    "question_text": question_text,
                    "marks": 3,
                    "or_group": None
                }
            )

    return questions


# =========================================================
# EXTRACT PART B
# =========================================================

def extract_part_b(text):

    questions = []

    match = re.search(
        r"PART B(.*)",
        text,
        flags=re.IGNORECASE | re.DOTALL
    )

    if not match:
        return questions

    part_b_text = match.group(1)

    pattern = re.compile(
        r"(?:^|\n)\s*"
        r"(1[1-9]|20)"
        r"\s+"
        r"(.+?)"
        r"(?=\n\s*(?:1[1-9]|20)\s+|\Z)",
        flags=re.DOTALL
    )

    matches = pattern.finditer(
        part_b_text
    )

    for match in matches:

        question_number = int(
            match.group(1)
        )

        question_text = clean_text(
            match.group(2)
        )

        if question_text:

            questions.append(
                {
                    "question_number": question_number,
                    "part": "B",
                    "module": get_module(
                        question_number
                    ),
                    "question_text": question_text,
                    "marks": 6,
                    "or_group": get_or_group(
                        question_number
                    )
                }
            )

    return questions


# =========================================================
# VALIDATE
# =========================================================

def validate_questions(questions):

    numbers = [
        q["question_number"]
        for q in questions
    ]

    expected = list(range(1, 21))

    return numbers == expected


# =========================================================
# GET DOCUMENT ID
# =========================================================

def get_document_id(
    connection,
    filename
):

    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT id
        FROM documents
        WHERE filename = ?
        """,
        (filename,)
    )

    result = cursor.fetchone()

    if result:
        return result[0]

    return None


# =========================================================
# INSERT QUESTIONS
# =========================================================

def insert_questions(
    connection,
    document_id,
    year,
    questions
):

    cursor = connection.cursor()

    # Remove existing questions for this document
    cursor.execute(
        """
        DELETE FROM pyq_questions
        WHERE document_id = ?
        """,
        (document_id,)
    )

    # Insert fresh questions
    for question in questions:

        cursor.execute(
            """
            INSERT INTO pyq_questions
            (
                document_id,
                question_number,
                part,
                module,
                question_text,
                year,
                marks,
                or_group
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                document_id,
                question["question_number"],
                question["part"],
                question["module"],
                question["question_text"],
                year,
                question["marks"],
                question["or_group"]
            )
        )

    connection.commit()


# =========================================================
# DISPLAY
# =========================================================

def display_questions(questions):

    print()

    for question in questions:

        print("-" * 60)

        print(
            f"Q{question['question_number']}"
        )

        print(
            f"Part: {question['part']}"
        )

        print(
            f"Module: {question['module']}"
        )

        print(
            f"Marks: {question['marks']}"
        )

        print(
            f"OR Group: {question['or_group']}"
        )

        print()

        print(
            question["question_text"]
        )

    print("-" * 60)


# =========================================================
# PROCESS ONE PDF
# =========================================================

def process_pdf(
    connection,
    pdf_path
):

    filename = os.path.basename(
        pdf_path
    )

    print()
    print("=" * 60)
    print(
        f"Document: {filename}"
    )
    print("=" * 60)

    # -----------------------------------------------------
    # Extract text
    # -----------------------------------------------------

    text = extract_pdf_text(
        pdf_path
    )

    # -----------------------------------------------------
    # Scanned PDF
    # -----------------------------------------------------

    if not text.strip():

        print()
        print(
            "No extractable text found."
        )

        print(
            "Skipping this PDF."
        )

        return 0

    # -----------------------------------------------------
    # Year
    # -----------------------------------------------------

    year = extract_year(
        text
    )

    print(
        f"Year: {year}"
    )

    # -----------------------------------------------------
    # Extract questions
    # -----------------------------------------------------

    part_a = extract_part_a(
        text
    )

    part_b = extract_part_b(
        text
    )

    questions = part_a + part_b

    questions.sort(
        key=lambda q:
            q["question_number"]
    )

    # -----------------------------------------------------
    # Validate
    # -----------------------------------------------------

    if not validate_questions(
        questions
    ):

        print()
        print(
            "VALIDATION FAILED."
        )

        print(
            "Questions were NOT inserted."
        )

        return 0

    print()
    print(
        "VALIDATION PASSED."
    )

    print(
        "All Q1-Q20 extracted correctly."
    )

    # -----------------------------------------------------
    # Display
    # -----------------------------------------------------

    display_questions(
        questions
    )

    # -----------------------------------------------------
    # Find document ID
    # -----------------------------------------------------

    document_id = get_document_id(
        connection,
        filename
    )

    if document_id is None:

        print()
        print(
            f"ERROR: {filename} "
            "not found in documents table."
        )

        print(
            "Questions were NOT inserted."
        )

        return 0

    # -----------------------------------------------------
    # Insert
    # -----------------------------------------------------

    insert_questions(
        connection,
        document_id,
        year,
        questions
    )

    print()
    print(
        f"Inserted {len(questions)} "
        f"questions into pyq_questions."
    )

    return len(questions)


# =========================================================
# MAIN
# =========================================================

def main():

    print()
    print("=" * 60)
    print("PYQ PROCESSING")
    print("=" * 60)

    # -----------------------------------------------------
    # Check database
    # -----------------------------------------------------

    if not os.path.exists(DB_PATH):

        print(
            f"\nDatabase not found: {DB_PATH}"
        )

        return

    # -----------------------------------------------------
    # Connect
    # -----------------------------------------------------

    connection = sqlite3.connect(
        DB_PATH
    )

    # -----------------------------------------------------
    # Find PDFs
    # -----------------------------------------------------

    pdf_files = get_pyq_files()

    if not pdf_files:

        print(
            "\nNo PYQ PDFs found."
        )

        connection.close()

        return

    total_inserted = 0

    # -----------------------------------------------------
    # Process each PDF
    # -----------------------------------------------------

    for pdf_path in pdf_files:

        count = process_pdf(
            connection,
            pdf_path
        )

        total_inserted += count

    # -----------------------------------------------------
    # Close database
    # -----------------------------------------------------

    connection.close()

    # -----------------------------------------------------
    # Final result
    # -----------------------------------------------------

    print()
    print("=" * 60)
    print("FINAL RESULT")
    print("=" * 60)

    print(
        f"Total questions inserted: "
        f"{total_inserted}"
    )

    print("=" * 60)
    print()


# =========================================================
# START
# =========================================================

if __name__ == "__main__":

    main()