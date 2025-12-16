
import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import os

# Конфигурация страницы
st.set_page_config(
    page_title="Психологический Бот-Ассистент",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Стилизация
st.markdown("""
<style>
    .main-header {
        text-align: center;
        color: #2E86AB;
        margin-bottom: 2rem;
    }
    .metric-card {
        background-color: #F0F4F8;
        padding: 1.5rem;
        border-radius: 0.5rem;
        margin-bottom: 1rem;
    }
    .emotion-happy { color: #FFD700; }
    .emotion-sad { color: #4169E1; }
    .emotion-anxious { color: #FF6347; }
    .emotion-angry { color: #DC143C; }
    .emotion-neutral { color: #808080; }
    .emotion-excited { color: #FF1493; }
    .emotion-calm { color: #90EE90; }
</style>
""", unsafe_allow_html=True)

# Получение URL Worker API из переменных окружения
WORKER_API_URL = os.getenv("WORKER_API_URL", "http://worker:8000")

# Инициализация сессии
if "user_id" not in st.session_state:
    st.session_state.user_id = "web_user"

if "analysis_history" not in st.session_state:
    st.session_state.analysis_history = []


