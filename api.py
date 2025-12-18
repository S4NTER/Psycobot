import sqlite3
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel


DB_PATH = "psychologist_bot.db"

def get_db_connection():
    return sqlite3.connect(DB_PATH)

def get_user_data(user_id: int) -> Optional[Dict[str, Any]]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT user_id, chat_id, username, last_report_date FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return {'user_id': row[0], 'chat_id': row[1], 'username': row[2], 'last_report_date': row[3]}
    return None

def get_all_users_data() -> List[Dict[str, Any]]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT user_id, chat_id, username, last_report_date FROM users")
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


class User(BaseModel):
    user_id: int
    chat_id: int
    username: Optional[str] = None
    last_report_date: Optional[str] = None

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

