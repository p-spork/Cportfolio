import streamlit as st
import json
from pathlib import Path
import pandas as pd
import requests
from datetime import date, timedelta

st.set_page_config(page_title="Dashboard - Cportfolio", page_icon="📈", layout="wide")

# load user data 
data_path = Path(__file__).parent.parent / "data" / "users.json"
with open(data_path) as f:
    # load from json
    USERS = json.load(f)

# check login status
if "user" not in st.session_state or st.session_state.user is None:
    st.warning("Please log in first.")
    st.switch_page("pages/home.py")

user = st.session_state.user
#once loggeed in, get their portfolio
portfolio = USERS[user]["portfolio"]
tickers = list(portfolio.keys())

# --- Sidebar ---
st.sidebar.success(f"Logged in as {user}")
if st.sidebar.button("Log out", use_container_width=True):
    st.session_state.user = None
    st.switch_page("pages/home.py")

st.title(f"{user.capitalize()}'s Portfolio Dashboard 📈")

# --- Display portfolio holdings ---
df = pd.DataFrame(list(portfolio.items()), columns=["Ticker", "Shares Owned"])
st.dataframe(df, use_container_width=True)
st.bar_chart(df.set_index("Ticker"))

#  stock News from API (finnhub)

# api key
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
        return r.json()[:5]  # top 5 news items
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
            source = a.get("source", "Unknown Source")
            datetime_str = a.get("datetime")
            # Finnhub datetime is a Unix timestamp
            try:
                from datetime import datetime
                dt = datetime.fromtimestamp(a["datetime"])
                date_str = dt.strftime("%Y-%m-%d %H:%M")
            except Exception:
                date_str = "Unknown Date"

            st.markdown(
                f"**[{headline}]({url})**  \n"
                f"*{source}* — {date_str}"
            )
