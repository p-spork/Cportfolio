import streamlit as st
import json
from pathlib import Path

st.set_page_config(page_title="Login - Cportfolio", page_icon="🔐")

# --- Load user data
data_path = Path(__file__).parent.parent / "data" / "users.json"
with open(data_path) as f:
    USERS = json.load(f)

# --- Initialize 
if "user" not in st.session_state:
    st.session_state.user = None

st.title("🔐 Login to Cportfolio")

if st.session_state.user:
    st.success(f"Welcome back, {st.session_state.user}!")
    if st.button("Go to Dashboard", use_container_width=True):
        st.switch_page("pages/dashboard.py")

else:
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login", use_container_width=True):
        if username in USERS and USERS[username]["password"] == password:
            # Set session state and redirect
            st.session_state.user = username
            st.success("Login successful! Redirecting...")
            st.switch_page("pages/dashboard.py")  # redirect immediately
        else:
            st.error("Invalid username or password.")
