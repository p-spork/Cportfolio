import json, os
from pathlib import Path
import streamlit as st
from security import hash_password, verify_password
from storage import load_users, save_users

st.set_page_config(page_title="Cportfolio", page_icon="", layout="wide")
#  load in user data
USERS = load_users()
# Folder that contains app.py
#BASE_DIR = Path(__file__).resolve().parent

# Point to Cportfolio/data/users.json
#data_path = BASE_DIR / "data" / "users.json"   



#with data_path.open("r", encoding="utf-8") as f:
 #   USERS = json.load(f)



st.title("Welcome to Cportfolio")
st.write("Use the sidebar to navigate between pages.")





st.subheader("Create a new account")
#sign in section
st.subheader("Log in")
username = st.text_input("Username")
password = st.text_input("Password", type="password")

if st.button("Login", use_container_width=True):
    if username in USERS and verify_password(USERS[username]["password"], password):
        # set session state and redirect
        st.session_state.user = username
        st.success("Login successful! Redirecting...")

        st.switch_page("pages/dashboard.py")  # redirect immediately
    else:
        st.error("Invalid username or password.")

# sign up section
st.subheader("Sign up")
new_user = st.text_input("Choose a username", key="signup_user")
new_pass = st.text_input("Choose a password", type="password", key="signup_pass")
new_pass2 = st.text_input("Confirm password", type="password", key="signup_pass2")

if st.button("Create account", use_container_width=True):
    users = load_users()

    # basic password validation
    if not new_user.strip():
        st.error("Username cannot be empty.")
    elif new_user in users:
        st.error("That username is already taken.")
    elif len(new_pass) < 8:
        st.error("Password must be at least 8 characters.")
    elif new_pass != new_pass2:
        st.error("Passwords do not match.")
    else:
        users[new_user] = {
            "password": hash_password(new_pass),
            "portfolio": {}
        }
        save_users(users)
        st.success("Account created! You can log in now.")
