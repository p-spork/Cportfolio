import streamlit as st
import json
from pathlib import Path
import pandas as pd
import requests
from datetime import date, timedelta, datetime

st.set_page_config(page_title="Dashboard - Cportfolio", page_icon="📊", layout="wide")

# --- Load user data ---
data_path = Path(__file__).parent.parent / "data" / "users.json"

# Utility function to read/write user data
def load_users():
    with open(data_path) as f:
        return json.load(f)

def save_users(users):
    with open(data_path, "w") as f:
        json.dump(users, f, indent=2)

USERS = load_users()

# ---  Check login status ---
if "user" not in st.session_state or st.session_state.user is None:
    st.warning("Please log in first.")
    st.switch_page("pages/home.py")

user = st.session_state.user
portfolio = USERS[user]["portfolio"]
tickers = list(portfolio.keys())

# --- Sidebar ---
st.sidebar.success(f"Logged in as {user}")
if st.sidebar.button("Log out", use_container_width=True):
    st.session_state.user = None
    st.switch_page("pages/home.py")

st.title(f"{user.capitalize()}'s Portfolio Dashboard 📈")
#-------------------
# Portfolio Management

st.subheader("Your Portfolio")

df = pd.DataFrame(list(portfolio.items()), columns=["Ticker", "Shares Owned"])
st.dataframe(df, use_container_width=True)
st.bar_chart(df.set_index("Ticker"))

# --- Add new stock form ---
st.markdown("### ➕ Add a New Stock")

with st.form("add_stock_form"):
    new_ticker = st.text_input("Stock Symbol (e.g., AAPL, MSFT, TSLA)").upper().strip()
    new_shares = st.number_input("Number of Shares", min_value=1, step=1)
    submitted = st.form_submit_button("Add Stock", use_container_width=True)

if submitted:
    if not new_ticker:
        st.error("Please enter a valid stock symbol.")
    else:
        # If the stock already exists, add shares
        if new_ticker in portfolio:
            portfolio[new_ticker] += int(new_shares)
            st.success(f"Added {new_shares} more shares of {new_ticker}.")
        else:
            portfolio[new_ticker] = int(new_shares)
            st.success(f"Added {new_ticker} with {new_shares} shares to your portfolio.")

        # Save back to users.json
        USERS[user]["portfolio"] = portfolio
        save_users(USERS)

        # Force UI refresh
        st.rerun()

#stock news from finnhub

FINNHUB_API_KEY = st.secrets["FINNHUB_API_KEY"]

@st.cache_data(ttl=3600)
def get_stock_news(ticker):
    """Fetch recent company news from Finnhub (last 7 days)."""
    to_date = date.today()
    from_date = to_date - timedelta(days=7)
    url = (
        f"https://finnhub.io/api/v1/company-news"
        f"?symbol={ticker}&from={from_date}&to={to_date}&token={FINNHUB_API_KEY}"
    )
    r = requests.get(url)
    if r.status_code == 200:
        return r.json()[:5]
    return []

st.subheader("📰 Latest News for Your Stocks")

for ticker in tickers:
    with st.expander(f"{ticker} - Recent Headlines"):
        articles = get_stock_news(ticker)

        if not articles:
            st.info("No recent news found.")
            continue

        for a in articles:
            headline = a.get("headline", "No headline")
            url = a.get("url", "#")
            source = a.get("source", "Unknown")
            dt_str = "Unknown Date"
            try:
                dt = datetime.fromtimestamp(a["datetime"])
                dt_str = dt.strftime("%Y-%m-%d %H:%M")
            except Exception:
                pass

            st.markdown(f"**[{headline}]({url})**  \n*{source} — {dt_str}*")
