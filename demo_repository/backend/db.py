import sqlite3

DATABASE_PATH = "demo_app.db"


def execute_raw_query(query: str):
    """DEMO ONLY: Critical SQL Injection vulnerability via unescaped string formatting (Security Analyzer: SEC002)."""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    # Unsafe raw execution of concatenated string
    cursor.execute(query)
    rows = cursor.fetchall()
    conn.commit()
    conn.close()
    return rows
