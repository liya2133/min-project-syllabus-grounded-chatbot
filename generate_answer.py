"""
generate_answer.py
------------------

Block 3: Answer Generation

Flow:

1. Take student's question.
2. Retrieve relevant syllabus/notes chunks using FAISS.
3. Find matching previous-year questions.
4. Send the retrieved context to Gemini.
5. Generate a syllabus-grounded answer.
6. Show exam relevance.
7. Log the query in SQLite.
"""

import os
import sqlite3
import time

from google import genai

from retrieve import retrieve, DB_PATH
from exam_relevance import get_exam_relevance


# ============================================================
# CONFIGURATION
# ============================================================

MODEL_NAME = "gemini-3.6-flash"


# ============================================================
# GEMINI SETUP
# ============================================================

api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    raise RuntimeError(
        "GEMINI_API_KEY is not set."
    )

client = genai.Client(
    api_key=api_key
)


# ============================================================
# BUILD SYLLABUS CONTEXT
# ============================================================

def build_context(chunks):
    """
    Convert retrieved chunks into text context
    for Gemini.
    """

    context_parts = []

    for chunk in chunks:

        filename = chunk["filename"]
        page_number = chunk["page_number"]
        chunk_text = chunk["chunk_text"]

        if page_number:
            source_label = (
                f"{filename}, page {page_number}"
            )
        else:
            source_label = filename

        context_parts.append(
            f"""
SOURCE: {source_label}

CONTENT:

{chunk_text}
"""
        )

    return "\n".join(context_parts)


# ============================================================
# BUILD PYQ CONTEXT
# ============================================================

def build_pyq_context(exam_result):
    """
    Convert matching PYQs into text context.
    """

    if not exam_result["found"]:
        return (
            "No matching previous-year question "
            "was found in the PYQ database."
        )

    pyq_parts = []

    for question in exam_result["questions"]:

        pyq_parts.append(
            f"""
Question: Q{question["question_number"]}

Module: {question["module"]}

Year: {question["year"]}

Marks: {question["marks"]}

Previous-year question:

{question["question_text"]}
"""
        )

    return "\n".join(pyq_parts)


# ============================================================
# CALL GEMINI
# ============================================================

def call_llm(prompt):
    """
    Send the prompt to Gemini.

    Handles:

    1. 503 - temporary Gemini server overload
       Retry up to 3 times.

    2. 429 - quota exceeded
       Do NOT retry because the daily quota
       has already been exhausted.

    3. Other errors
       Raise the original error.
    """

    for attempt in range(3):

        try:

            response = client.models.generate_content(
                model=MODEL_NAME,
                contents=prompt,
                config={
                    "thinking_config": {
                        "thinking_level": "minimal"
                    }
                }
            )

            return response.text

        except Exception as e:

            error_message = str(e)

            # =================================================
            # 429 - QUOTA EXCEEDED
            # =================================================

            if (
                "429" in error_message
                or "RESOURCE_EXHAUSTED" in error_message
            ):

                print(
                    "\n[debug] Gemini API quota "
                    "has been exceeded."
                )

                return (
                    "The chatbot has temporarily "
                    "reached the Gemini API request "
                    "limit. Please try again after "
                    "the quota resets."
                )

            # =================================================
            # 503 - TEMPORARY SERVER OVERLOAD
            # =================================================

            elif (
                "503" in error_message
                or "UNAVAILABLE" in error_message
            ):

                if attempt < 2:

                    wait_time = 2 * (attempt + 1)

                    print(
                        "\n[debug] Gemini temporarily "
                        "unavailable."
                    )

                    print(
                        f"[debug] Retrying in "
                        f"{wait_time} seconds..."
                    )

                    time.sleep(wait_time)

                else:

                    print(
                        "\n[debug] Gemini remained "
                        "unavailable after 3 attempts."
                    )

                    return (
                        "Gemini is temporarily busy "
                        "right now. Please try your "
                        "question again in a few seconds."
                    )

            # =================================================
            # OTHER ERRORS
            # =================================================

            else:

                raise


# ============================================================
# LOG QUERY
# ============================================================

def log_query(
    question,
    answer,
    chunks,
    confidence_score
):
    """
    Save the student's question, answer,
    retrieved chunks and confidence score
    in SQLite.
    """

    connection = sqlite3.connect(
        DB_PATH
    )

    chunk_ids = [
        str(chunk["chunk_id"])
        for chunk in chunks
    ]

    retrieved_chunk_ids = ",".join(
        chunk_ids
    )

    connection.execute(
        """
        INSERT INTO queries_log
        (
            question,
            answer,
            retrieved_chunk_ids,
            confidence_score
        )
        VALUES (?, ?, ?, ?)
        """,
        (
            question,
            answer,
            retrieved_chunk_ids,
            confidence_score
        )
    )

    connection.commit()
    connection.close()


# ============================================================
# ANSWER QUESTION
# ============================================================

def answer_question(question):
    """
    Main chatbot function.
    """

    # --------------------------------------------------------
    # STEP 1: Retrieve relevant chunks
    # --------------------------------------------------------

    retrieval_result = retrieve(
        question
    )

    chunks = retrieval_result["chunks"]


    # --------------------------------------------------------
    # STEP 2: Check exam relevance
    # --------------------------------------------------------

    exam_result = get_exam_relevance(
        question
    )


    # --------------------------------------------------------
    # STEP 3: If topic is not covered
    # --------------------------------------------------------

    if retrieval_result["status"] == "not_covered":

        answer = retrieval_result["message"]

        log_query(
            question,
            answer,
            [],
            0.0
        )

        return {
            "answer": answer,
            "exam_relevance": exam_result
        }


    # --------------------------------------------------------
    # STEP 4: Build syllabus context
    # --------------------------------------------------------

    # Only send the top 5 chunks to Gemini.
    #
    # This keeps the prompt smaller and
    # reduces unnecessary processing.

    syllabus_context = build_context(
        chunks[:5]
    )


    # --------------------------------------------------------
    # STEP 5: Build PYQ context
    # --------------------------------------------------------

    pyq_context = build_pyq_context(
        exam_result
    )


    # --------------------------------------------------------
    # STEP 6: Build Gemini prompt
    # --------------------------------------------------------

    prompt = f"""
You are a syllabus-grounded academic chatbot
for MCA students.

The student asked:

{question}


You have two types of information:

1. SYLLABUS / NOTES
2. PREVIOUS YEAR QUESTIONS (PYQs)


IMPORTANT RULES:

- Answer the student's question using ONLY
  the syllabus/notes provided below.

- Do not use outside knowledge.

- Do not invent facts.

- Keep the explanation simple and suitable
  for an MCA student.

- Give a clear and direct answer.

- The PYQ information is used only to provide
  exam-relevance evidence.

- Do not use PYQs as factual source material
  for explaining the topic.

- If matching PYQs are available, mention them
  separately under "Exam Relevance".

- Do not claim that a topic is important merely
  because it appeared in one PYQ.

- Clearly separate the answer from PYQ evidence.

- If the provided syllabus/notes do not contain
  enough information to explain something,
  clearly say that the available material does
  not provide further details.


--------------------------------------------------
SYLLABUS / NOTES
--------------------------------------------------

{syllabus_context}


--------------------------------------------------
PREVIOUS YEAR QUESTIONS
--------------------------------------------------

{pyq_context}


--------------------------------------------------
RESPONSE FORMAT
--------------------------------------------------

Answer:

[Answer the student's question using only
the syllabus/notes. Keep it simple.]


Exam Relevance:

[If matching PYQs were found, mention:

- Matching PYQ found: Yes
- Module
- Year
- Marks
- Previous question

If no matching PYQ was found, say:

"No matching PYQ was found in the available
PYQ database."]


Sources:

[List the syllabus/notes filename
and page number.]
"""


    # --------------------------------------------------------
    # STEP 7: Ask Gemini
    # --------------------------------------------------------

    answer = call_llm(
        prompt
    )


    # --------------------------------------------------------
    # STEP 8: Calculate confidence
    # --------------------------------------------------------

    semantic_scores = [
        chunk.get(
            "similarity",
            0.0
        )
        for chunk in chunks
        if chunk.get(
            "similarity",
            0.0
        ) > 0.0
    ]

    top_confidence = max(
        semantic_scores,
        default=0.0
    )


    # --------------------------------------------------------
    # STEP 9: Log query
    # --------------------------------------------------------

    log_query(
        question,
        answer,
        chunks,
        top_confidence
    )


    # --------------------------------------------------------
    # STEP 10: Return result
    # --------------------------------------------------------

    return {
        "answer": answer,
        "exam_relevance": exam_result
    }


# ============================================================
# MAIN CHATBOT
# ============================================================

if __name__ == "__main__":

    print(
        "Syllabus Chatbot"
    )

    print(
        "----------------"
    )

    print(
        "Type 'exit' to stop.\n"
    )

    while True:

        question = input(
            "You: "
        ).strip()


        # ----------------------------------------------------
        # EXIT
        # ----------------------------------------------------

        if question.lower() == "exit":

            print(
                "Goodbye!"
            )

            break


        # ----------------------------------------------------
        # EMPTY QUESTION
        # ----------------------------------------------------

        if not question:
            continue


        # ----------------------------------------------------
        # GENERATE ANSWER
        # ----------------------------------------------------

        try:

            result = answer_question(
                question
            )

            print(
                "\nChatbot:\n"
            )

            print(
                result["answer"]
            )

            print(
                "\n"
                + "-" * 60
                + "\n"
            )

        except Exception as e:

            print(
                "\nError:",
                e
            )

            print()