import streamlit as st
import db

st.set_page_config(
    page_title="Psychologist Bot Dashboard",
    layout="wide",
    initial_sidebar_state="collapsed"
)
import requests
import pandas as pd
from datetime import datetime
import json
import os
import time
from streamlit_cookies_manager import EncryptedCookieManager
cookies = EncryptedCookieManager(
    prefix="psychobot/",
    password=os.environ.get("Cookies_password")
)


API_BASE_URL = os.environ.get("API_BASE_URL", "http://api:8000")
ADMIN_TELEGRAM_ID = int(os.environ.get("ADMIN_ID"))

def hide_streamlit_elements():
    hide_css = """
    <style>
    /* Hide the deploy button and menu */
    #MainMenu {
        visibility: hidden;
    }
    
    /* Hide the footer */
    footer {
        visibility: hidden;
    }
    
    /* Hide the header */
    header {
        visibility: hidden;
    }
    
    /* Adjust the main content area */
    .main {
        margin-top: 0;
    }
    </style>
    """
    st.markdown(hide_css, unsafe_allow_html=True)

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
    #user_balance = get_api_data(f"balance/{user_id}")
    return user_profile, user_stats, user_entries#, user_balance

def get_all_users():
    return get_api_data("users")

def get_suggestions():
    return get_api_data("suggestions")

def is_user_in_database(user_id: int) -> bool:
    all_users = get_all_users()
    if all_users:
        return any(user['user_id'] == user_id for user in all_users)
    return False

def is_admin(user_id: int) -> bool:
    return user_id == ADMIN_TELEGRAM_ID

hide_streamlit_elements()

st.title("🧠 Psychologist Bot Dashboard")
if not cookies.ready():
    st.stop()
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
    st.session_state.user_id = None
    st.session_state.is_admin = False
    st.session_state.logout_forced = False

if not st.session_state.authenticated and not st.session_state.logout_forced:
    cookie_user_id = cookies.get('user_id')
    if cookie_user_id and str(cookie_user_id).strip() != "":
        try:
            telegram_id = int(cookie_user_id)
            if is_user_in_database(telegram_id):
                st.session_state.authenticated = True
                st.session_state.user_id = telegram_id
                st.session_state.is_admin = is_admin(telegram_id)
        except (ValueError,TypeError):
            if 'user_id' in cookies:
                del cookies['user_id']
            cookies.save()

if not st.session_state.authenticated:
    st.markdown("---")
    st.subheader("🔐 Вход в систему")
    
    with st.form("login_form"):
        user_id = st.text_input("Введите ваш Login", type="default")
        password = st.text_input("Введите пароль", type="password")
        submit_button = st.form_submit_button("Войти")
        
        if submit_button:
            
            try:
                telegram_id = int(user_id)
                response = requests.post(
                    f"{API_BASE_URL}/login",
                    json={"user_id": telegram_id, "password": password}
                )
                if response.status_code == 200:
                    st.session_state.authenticated = True
                    st.session_state.user_id = telegram_id
                    st.session_state.is_admin = is_admin(telegram_id)
                    st.session_state.logout_forced = False
                    cookies['user_id'] = str(telegram_id)
                    cookies.save()
                    st.success(f"✅ Добро пожаловать! (ID: {telegram_id})")
                    st.rerun()
                else:
                    st.error("❌ Неверный ID или пароль")
            except ValueError:
                st.error("❌ Пожалуйста, введите корректный ID или пароль.")
    st.stop()
    
    st.markdown("---")
    st.info("ℹ️ Введите ваш Telegram ID для доступа к вашей статистике.")

else:
    col1, col2 = st.columns([0.9, 0.1])
    with col2:
        if st.button("🚪 Выход", key="logout_button"):
            
            if 'user_id' in cookies:
                cookies['user_id'] = ""
            cookies.save()
            st.session_state.authenticated = False
            st.session_state.user_id = None
            st.session_state.is_admin = False
            st.session_state.logout_forced = True
            st.rerun()
    
    if st.session_state.is_admin:
        st.markdown(f"**Статус:** 👑 Администратор | **Telegram ID:** {st.session_state.user_id}")
    else:
        st.markdown(f"**Статус:** 👤 Пользователь | **Telegram ID:** {st.session_state.user_id}")
    
    st.markdown("---")
    
    if st.session_state.is_admin:
        st.header("📊 Администраторский Дашборд")
        
        all_users = get_all_users()
        
        if all_users:
            user_options = {
                f"{user['user_id']} ({user.get('username', 'No Username')})": user['user_id']
                for user in all_users
            }
            
            sorted_options = sorted(user_options.keys())
            
            selected_option = st.selectbox(
                "Выберите профиль пользователя для просмотра:",
                sorted_options
            )
            
            selected_user_id = user_options[selected_option]
            
            st.markdown("---")
            
            profile, stats, entries = get_user_data(selected_user_id)
            
            if profile and stats:
                
                st.subheader("👤 Профиль пользователя")
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.metric("User ID", profile['user_id'])
                with col2:
                    st.metric("Username", profile.get('username', 'N/A'))
                with col3:
                    st.metric("⭐ Balance", db.get_balance(selected_user_id))
                    
                st.markdown("---")
                
                st.subheader("📈 Общая статистика")
                col_a, col_b, col_c, col_d, col_e = st.columns(5)
                
                with col_a:
                    st.metric("Total Entries", stats['total_entries'])
                with col_b:
                    st.metric("Average Mood Score", f"{stats['average_mood']:.2f}")
                with col_c:
                    st.metric("Mood Range", stats['mood_range'])
                with col_d:
                    st.metric("First Entry", stats['first_entry_date'].split('T')[0] if stats['first_entry_date'] else 'N/A')
                with col_e:
                    st.metric("Last Entry", stats['last_entry_date'].split('T')[0] if stats['last_entry_date'] else 'N/A')
                    
                st.markdown("---")
                
                st.subheader("📉 Тенденция настроения")
                
                if entries:
                    df = pd.DataFrame(entries)
                    df['timestamp'] = pd.to_datetime(df['timestamp'])
                    df = df.sort_values('timestamp')
                    
                    st.line_chart(df, x='timestamp', y='mood_score')
                    
                    st.subheader("📋 Записи настроения")
                    st.dataframe(df[['timestamp', 'mood_score', 'trigger_text', 'thought_text']], use_container_width=True)
                else:
                    st.info("No mood entries found for this user to display a trend.")
                    
            else:
                st.error("Could not retrieve data for the selected user.")
        
        else:
            st.warning("No users found in the database.")
    
    else:
        st.header("📊 Ваша статистика")
        
        profile, stats, entries = get_user_data(st.session_state.user_id)
        
        if profile and stats:
            
            st.subheader("👤 Ваш профиль")
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("User ID", profile['user_id'])
            with col2:
                st.metric("Username", profile.get('username', 'N/A'))
            with col3:
                st.metric("⭐ Balance", db.get_balance(st.session_state.user_id))
                
            st.markdown("---")
            
            st.subheader("📈 Ваша статистика")
            col_a, col_b, col_c, col_d, col_e = st.columns(5)
            
            with col_a:
                st.metric("Total Entries", stats['total_entries'])
            with col_b:
                st.metric("Average Mood Score", f"{stats['average_mood']:.2f}")
            with col_c:
                st.metric("Mood Range", stats['mood_range'])
            with col_d:
                st.metric("First Entry", stats['first_entry_date'].split('T')[0] if stats['first_entry_date'] else 'N/A')
            with col_e:
                st.metric("Last Entry", stats['last_entry_date'].split('T')[0] if stats['last_entry_date'] else 'N/A')
                
            st.markdown("---")
            
            st.subheader("📉 Ваша тенденция настроения")
            
            if entries:
                df = pd.DataFrame(entries)
                df['timestamp'] = pd.to_datetime(df['timestamp'])
                df = df.sort_values('timestamp')
                
                st.line_chart(df, x='timestamp', y='mood_score')
                
                st.subheader("📋 Ваши записи настроения")
                st.dataframe(df[['timestamp', 'mood_score', 'trigger_text', 'thought_text']], use_container_width=True)
            else:
                st.info("У вас пока нет записей настроения.")
                
        else:
            st.error("Could not retrieve your data.")
    
    