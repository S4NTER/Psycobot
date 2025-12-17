import streamlit as st
import requests
import pandas as pd
from datetime import datetime
import json

import os
API_BASE_URL = os.environ.get("API_BASE_URL", "http://api:8000")

@st.cache_data(ttl=60)
def get_api_data(endpoint):
    try:
        response = requests.get(f"{API_BASE_URL}/{endpoint}")
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Error connecting to API: {e}")
        return None

def get_user_data(user_id):
    user_profile = get_api_data(f"users/{user_id}")
    user_stats = get_api_data(f"stats/{user_id}")
    user_entries = get_api_data(f"mood_entries/{user_id}")
    return user_profile, user_stats, user_entries

def get_all_users():
    return get_api_data("users")

def get_suggestions():
    return get_api_data("suggestions")

st.set_page_config(
    page_title="Psychologist Bot Dashboard",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("🧠 Psychologist Bot Dashboard")
