import sqlite3
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import bcrypt



DB_PATH = "psychologist_bot.db"

def get_db_connection():
    return sqlite3.connect(DB_PATH)

def get_user_data(user_id: int) -> Optional[Dict[str, Any]]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT user_id, chat_id, username, balance, password FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return {'user_id': row[0], 'chat_id': row[1], 'username': row[2], 'balance': row[3], 'password':row[4]}
    return None

def get_all_users_data() -> List[Dict[str, Any]]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT user_id, chat_id, username, balance FROM users")
    columns = [desc[0] for desc in cursor.description]
    data = [dict(zip(columns, row)) for row in cursor.fetchall()]
    conn.close()
    return data

def get_all_mood_entries(user_id: int) -> List[Dict[str, Any]]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT timestamp, mood_score, trigger_text, thought_text 
        FROM mood_entries 
        WHERE user_id = ? 
        ORDER BY timestamp DESC
    """, (user_id,))
    columns = [desc[0] for desc in cursor.description]
    data = [dict(zip(columns, row)) for row in cursor.fetchall()]
    conn.close()
    return data

def save_mood_entry(user_id: int, mood_score: int, trigger_text: str, thought_text: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    timestamp = datetime.now().isoformat()
    cursor.execute("""
        INSERT INTO mood_entries (user_id, timestamp, mood_score, trigger_text, thought_text)
        VALUES (?, ?, ?, ?, ?)
    """, (user_id, timestamp, mood_score, trigger_text, thought_text))
    conn.commit()
    conn.close()

class User(BaseModel):
    user_id: int
    chat_id: int
    username: Optional[str] = None
    password: Optional[str] = None

class MoodEntryRequest(BaseModel):
    user_id: int
    mood_score: int
    trigger_text: Optional[str] = None
    thought_text: Optional[str] = None

class MoodEntry(BaseModel):
    timestamp: str
    mood_score: int
    trigger_text: Optional[str] = None
    thought_text: Optional[str] = None

class UserStats(BaseModel):
    total_entries: int
    average_mood: float
    mood_range: str
    first_entry_date: Optional[str] = None
    last_entry_date: Optional[str] = None


app = FastAPI(title="Psychologist Bot Worker API")

@app.post("/mood_entry", status_code=201, summary="Submit a new mood entry")
def create_mood_entry(entry: MoodEntryRequest):
    if get_user_data(entry.user_id) is None:
        raise HTTPException(status_code=404, detail="User not found. Cannot save mood entry.")
    
    save_mood_entry(
        user_id=entry.user_id,
        mood_score=entry.mood_score,
        trigger_text=entry.trigger_text,
        thought_text=entry.thought_text
    )
    
    return {"message": "Mood entry successfully saved."}

@app.get("/users", response_model=List[User], summary="Get all registered users")
def read_users():
    return get_all_users_data()

@app.get("/users/{user_id}", response_model=User, summary="Get a specific user's profile")
def read_user(user_id: int):
    user = get_user_data(user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@app.get("/mood_entries/{user_id}", response_model=List[MoodEntry], summary="Get all mood entries for a user")
def read_mood_entries(user_id: int):
    entries = get_all_mood_entries(user_id)
    if not entries and get_user_data(user_id) is None:
        raise HTTPException(status_code=404, detail="User not found")
    return entries

@app.get("/stats/{user_id}", response_model=UserStats, summary="Get calculated statistics for a user")
def get_user_stats(user_id: int):
    entries = get_all_mood_entries(user_id)
    
    if not entries:
        if get_user_data(user_id) is None:
            raise HTTPException(status_code=404, detail="User not found")
        return UserStats(
            total_entries=0,
            average_mood=0.0,
            mood_range="N/A",
            first_entry_date=None,
            last_entry_date=None
        )

    mood_scores = [entry['mood_score'] for entry in entries]
    timestamps = [datetime.fromisoformat(entry['timestamp']) for entry in entries]
    
    total_entries = len(entries)
    average_mood = sum(mood_scores) / total_entries
    min_mood = min(mood_scores)
    max_mood = max(mood_scores)
    
    first_entry_date = min(timestamps).isoformat()
    last_entry_date = max(timestamps).isoformat()
    
    return UserStats(
        total_entries=total_entries,
        average_mood=round(average_mood, 2),
        mood_range=f"{min_mood} - {max_mood}",
        first_entry_date=first_entry_date,
        last_entry_date=last_entry_date
    )


class LoginRequest(BaseModel):
    user_id: int
    password: str


@app.post("/login")
def login(request: LoginRequest):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT password FROM users WHERE user_id = ?", (request.user_id,))
    row = cursor.fetchone()
    conn.close()
    if not row or not row[0]:
        raise HTTPException(status_code=401, detail="Пользователь не найден")
    stored_password = row[0]
    if bcrypt.checkpw(request.password.encode('utf-8'), stored_password.encode('utf-8')):
        return {"status": "success", "user_id": request.user_id}
    else:
        raise HTTPException(status_code=401, detail="Неверный пароль")
@app.post("/debug_login")
def debug_login(request: LoginRequest):
    return {
        "received": {
            "user_id": request.user_id,
            "password_length": len(request.password),
        },
        "message": "Данные получены"
    }