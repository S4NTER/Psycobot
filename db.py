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


def register_user(user_id: int, chat_id: int, username: str = None):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            chat_id INTEGER NOT NULL,
            username TEXT
        )
    """)

    cursor.execute("""
        INSERT OR REPLACE INTO users (user_id, chat_id, username)
        VALUES (?, ?, ?)
    """, (user_id, chat_id, username))

    conn.commit()
    conn.close()


def get_user_data(user_id: int) -> list:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT timestamp, mood_score, trigger_text, thought_text 
        FROM mood_entries 
        WHERE user_id = ? 
        ORDER BY timestamp DESC
    """, (user_id,))

    data = cursor.fetchall()
    conn.close()
    return data


if __name__ == "main":
    initialize_db()