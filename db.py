import sqlite3
from datetime import datetime

DB_PATH = "psychologist_bot.db"


def initialize_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS mood_entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            timestamp TEXT NOT NULL,
            mood_score INTEGER NOT NULL,
            trigger_text TEXT,
            thought_text TEXT
        )
    """)

    conn.commit()
    conn.close()
    print(f"База данных инициализирована: {DB_PATH}")


def save_entry(user_id: int, mood_score: int, trigger_text: str, thought_text: str):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    timestamp = datetime.now().isoformat()

    cursor.execute("""
        INSERT INTO mood_entries (user_id, timestamp, mood_score, trigger_text, thought_text)
        VALUES (?, ?, ?, ?, ?)
    """, (user_id, timestamp, mood_score, trigger_text, thought_text))

    conn.commit()
    conn.close()
    print(f"Запись сохранена для пользователя {user_id}")


if __name__ == "main":
    initialize_db()
    save_entry(12345, 7, "Тестовый триггер", "Тестовая мысль")