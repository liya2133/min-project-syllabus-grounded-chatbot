from flask import Flask, request, jsonify
from flask_cors import CORS

from generate_answer import answer_question
from admin import admin_bp

app = Flask(__name__)

CORS(app)
app.register_blueprint(admin_bp)


# ============================================================
# HOME
# ============================================================

@app.route("/", methods=["GET"])
def home():

    return jsonify({
        "message": "Syllabus Chatbot API is running"
    })


# ============================================================
# ASK QUESTION
# ============================================================

@app.route("/ask", methods=["POST"])
def ask_question():

    data = request.get_json()

    # --------------------------------------------------------
    # Check JSON
    # --------------------------------------------------------

    if not data:

        return jsonify({
            "error": "No JSON data received"
        }), 400

    # --------------------------------------------------------
    # Get question
    # --------------------------------------------------------

    question = data.get("question")

    if not question:

        return jsonify({
            "error": "Question is required"
        }), 400

    # --------------------------------------------------------
    # Get subject ID
    # --------------------------------------------------------

    subject_id = data.get("subject_id")

    # --------------------------------------------------------
    # Validate subject ID
    # --------------------------------------------------------

    if subject_id is not None:

        try:

            subject_id = int(subject_id)

        except (ValueError, TypeError):

            return jsonify({
                "error": "subject_id must be an integer"
            }), 400

    # --------------------------------------------------------
    # Generate answer
    # --------------------------------------------------------

    try:

        result = answer_question(
            question,
            subject_id=subject_id
        )

        return jsonify(result)

    except Exception as e:

        print(
            "[ERROR]",
            e
        )

        return jsonify({
            "error": "Something went wrong while processing the question."
        }), 500


# ============================================================
# RUN SERVER
# ============================================================

if __name__ == "__main__":

    app.run(
        debug=True,
        host="127.0.0.1",
        port=5000
    )