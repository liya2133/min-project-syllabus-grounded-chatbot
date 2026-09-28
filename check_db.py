import sqlite3

connection = sqlite3.connect("db/chatbot.db")

print("Logged queries:")

rows = connection.execute("""
    SELECT question, confidence_score
    FROM queries_log
    ORDER BY id DESC
    LIMIT 10
""").fetchall()

for row in rows:
    print("\nQuestion:", row[0])
    print("Confidence:", row[1])

connection.close()