import sqlite3
from datetime import datetime
from config import DB_PATH


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

    cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                chat_id INTEGER NOT NULL,
                username TEXT,
                balance INTEGER DEFAULT 0,
                password TEXT NOT NULL
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


def register_user(user_id: int, chat_id: int, username: str = None, password: str = None):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        INSERT OR REPLACE INTO users (user_id, chat_id, username, balance, password)
        VALUES (?, ?, ?, ?, ?)
    """, (user_id, chat_id, username, get_balance(user_id), password))

    conn.commit()
    conn.close()


def set_password(user_id: int, password: str):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
            UPDATE users 
            SET password = ?
            WHERE user_id = ?; 
    """, (password, user_id))

    conn.commit()
    conn.close()


def set_balance(user_id: int, balance: int):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
            UPDATE users 
            SET balance = ?
            WHERE user_id = ?; 
        """, (balance, user_id))

    conn.commit()
    conn.close()


def get_balance(user_id: int):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
             SELECT balance FROM users WHERE user_id  = ?
        """, (user_id,))

    balance = cursor.fetchone()
    # conn.commit()
    conn.close()

    return balance[0] if balance else 0


def get_user_data(user_id: int):
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


def get_weekly_data(user_id: int, start_date: datetime):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    start_date_iso = start_date.isoformat()

    cursor.execute("""
        SELECT timestamp, mood_score, trigger_text, thought_text
        FROM mood_entries 
        WHERE user_id = ? AND timestamp >= ? 
        ORDER BY timestamp
    """, (user_id, start_date_iso))

    data = cursor.fetchall()
    conn.close()

    result = []
    for row in data:
        result.append({
            'timestamp': row[0],
            'mood_score': row[1],
            'trigger_text': row[2] if row[2] else '',
            'thought_text': row[3] if row[3] else ''
        })

    return result


if __name__ == "main":
    initialize_db()
