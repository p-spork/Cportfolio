import streamlit as st
import json
from pathlib import Path
from datetime import date, timedelta, datetime
import requests
import pandas as pd
import os
from storage import load_users, save_users

#pip install huggingface-hub
from huggingface_hub import InferenceClient

st.set_page_config(page_title="Insights - Cportfolio", page_icon="", layout="wide")

# load in user data

USERS = load_users()

# check login status
if "user" not in st.session_state or st.session_state.user is None:
    st.warning("Please log in first.")
    st.switch_page("home.py")
     
user = st.session_state.user
portfolio = USERS[user]["portfolio"]
tickers = list(portfolio.keys())

st.sidebar.success(f"Logged in as {user}")


# logout button
if st.sidebar.button("Log out", use_container_width=True):
    st.session_state.user = None
    st.switch_page("home.py")

# main page

st.title(f"{user.capitalize()}'s Portfolio Insights ")
st.divider()

st.subheader("Your current holdings")

df = pd.DataFrame(
    [{"Ticker": t, "Shares Owned": portfolio[t]} for t in tickers]
).sort_values("Ticker")

st.dataframe(df, use_container_width=True)


st.subheader("Artificial Intelligence Insights")

# Initialize the InferenceClient with your Hugging Face API token

client = InferenceClient(
    api_key=st.secrets.get("HF_TOKEN")
)

# ---------- Build JSON payload ----------
payload = {
    "user": user,
    "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    "holdings": [
        {"ticker": t, "shares": int(portfolio[t])}
        for t in tickers
    ],
}

#debug code to see what json looks like when being sent.
#st.code(json.dumps(payload, indent=2), language="json")

def call_hf_insights(payload: dict) -> str:
    hf_token = st.secrets.get("HF_TOKEN")
    if not hf_token:
        #error checking for missing token
        return "No HF_TOKEN found in .streamlit/secrets.toml"
    
    #create the client with the key
    client = InferenceClient(api_key=hf_token)

    #make the prompt , this prompt was designed for this use case. 
    prompt = f"""
You are a calm, neutral portfolio analyst.

Given the following JSON describing a user's stock holdings, do NOT give financial advice.
Instead, do this:

1. Give 3–6 bullet-point **insights** about:
   - concentration vs diversification
   - any unusually large positions
   - anything interesting about the mix of tickers (e.g. large cap vs others, tech-heavy, etc.)

2. Give 2–3 **popular narratives** or themes that investors often talk about
   for portfolios like this (e.g. “big tech growth focus”, “EV-heavy exposure”, etc.).
   Keep them generic, not as recommendations.

3. Give 2–3 **risks to watch**, phrased cautiously.

Important rules:
- DO NOT tell the user what they *should* buy or sell.
- DO NOT mention that you are an AI; just speak like an analyst.
- Use markdown with headings and bullet points.
- Be concise.

JSON:
{json.dumps(payload, indent=2)}
"""
    #call the model
    completion = client.chat.completions.create(
        model ="HuggingFaceH4/zephyr-7b-beta:featherless-ai", 
        messages=[
            {
                "role": "user",
                "content": prompt,
            }
        ],
        max_tokens=250,
    )

    msg = completion.choices[0].message
    if isinstance(msg, dict):
        return msg.get("content", "").strip()
    return getattr(msg, "content", str(msg)).strip()

st.markdown("AI-Generated Portfolio Insight")

if st.button("Generate Insights", use_container_width=True):
    with st.spinner("Generating insights..."):
        insights = call_hf_insights(payload)
        
    st.markdown(insights)