import streamlit as st
import json
from pathlib import Path
import pandas as pd
import requests
import yfinance as yf
from datetime import date, timedelta, datetime
import altair as alt
from storage import load_users, save_users

st.set_page_config(page_title="Dashboard - Cportfolio", page_icon="", layout="wide")

# load in user data
data_path = Path(__file__).parent.parent / "data" / "users.json"
USERS = load_users()

# check login status
if "user" not in st.session_state or st.session_state.user is None:
    st.warning("Please log in first.")
    st.switch_page("home.py")

#load user portfolio
user = st.session_state.user
portfolio = USERS[user]["portfolio"]
tickers = list(portfolio.keys())

stocks = list(portfolio.items())

# code for the sidebar
st.sidebar.success(f"Logged in as {user}")
if st.sidebar.button("Log out", use_container_width=True):
    st.session_state.user = None
    st.switch_page("home.py")

st.title(f"{user.capitalize()}'s Portfolio Dashboard ")


# portfolio management

def style_pnl(value):
    if pd.isnull(value):
        return ""
    if value > 0:
        return "color: #16c784;"
    if value < 0:
        return "color: #ff4d4f;"
    return ""
# might be an issue here w loading in data for empty portfolio user. either gotta open account w min. 1 stock or adjust this page

st.subheader("Your Portfolio")
@st.cache_data
def fetch_prices(ticker_list):
    tickers = (
        [ticker_list]
        if isinstance(ticker_list, str)
        else list(ticker_list or [])
    )
    prices = {}
    for ticker in tickers:
        try:
            data = yf.download(
                ticker,
                period="2d",
                interval="1d",
                progress=False,
                group_by="ticker",
            )
        except Exception:
            continue
        if data is None or getattr(data, "empty", True):
            continue
        try:
            closes = data["Close"].dropna()
        except KeyError:
            # yfinance sometimes nests with MultiIndex
            if isinstance(data.columns, pd.MultiIndex):
                try:
                    closes = data.xs("Close", level=-1, axis=1).iloc[:, 0].dropna()
                except Exception:
                    continue
            else:
                continue
        if closes.empty:
            continue
        current = float(closes.iloc[-1])
        prev = float(closes.iloc[-2]) if len(closes) > 1 else float("nan")
        prices[ticker] = {"price": current, "prev_close": prev}
    return prices

price_map = fetch_prices(tickers)

rows = []
for ticker, shares in portfolio.items():
    price_info = price_map.get(ticker, {})
    price = price_info.get("price")
    prev_close = price_info.get("prev_close")
    value = shares * price if price is not None else None
    daily_pnl = (
        shares * (price - prev_close)
        if price is not None
        and prev_close is not None
        and not pd.isna(prev_close)
    else None
    )
    rows.append(
        {
            "Ticker": ticker,
            "Shares": shares,
            "Price": price,
            "Value": value,
            "Daily PnL": daily_pnl,
        }
    )

df = pd.DataFrame(rows)

if df.empty:
    st.info("Your portfolio is empty. Add positions to view analytics.")
    # add new stock form
    st.markdown("### Add a New Stock")

    with st.form("add_stock_form"):
        new_ticker = st.text_input("Stock Symbol (e.g., AAPL, MSFT, TSLA)").upper().strip()
        new_shares = st.number_input("Number of Shares", min_value=1, step=1)
        submitted = st.form_submit_button("Add Stock", use_container_width=True)

    if submitted:
        if not new_ticker:
            st.error("Please enter a valid stock symbol.")
        else:
            # if the stock already exists, add shares
            if new_ticker in portfolio:
                portfolio[new_ticker] += int(new_shares)
                st.success(f"Added {new_shares} more shares of {new_ticker}.")
            else:
                portfolio[new_ticker] = int(new_shares)
                st.success(f"Added {new_ticker} with {new_shares} shares to your portfolio.")

            # save info back to users.json
            USERS[user]["portfolio"] = portfolio
            save_users(USERS)

            # force UI refresh
            st.rerun()
    st.stop()

df["Portfolio %"] = float("nan")
if df["Value"].notna().any():
    total_value = df["Value"].sum()
    if total_value:
        df["Portfolio %"] = df["Value"] / total_value * 100

numeric_cols = ["Price", "Value", "Daily PnL", "Portfolio %"]

for col in numeric_cols:
    if col in df.columns:
        df[col] = pd.to_numeric(df[col], errors="coerce")

total_value = df["Value"].sum(skipna=True) if "Value" in df else 0.0
daily_pnl_total = df["Daily PnL"].sum(skipna=True) if "Daily PnL" in df else 0.0
metrics_col1, metrics_col2 = st.columns(2)
with metrics_col1:
    st.metric("Total Portfolio Value", f"${total_value:,.2f}")
with metrics_col2:
    color_style = style_pnl(daily_pnl_total)  
    # html here to colour code the daily pnl since only deltas can be colour-coded with streamlit
    st.markdown(
        f"""
        <div style="display:flex;flex-direction:column;">
            <span style="font-size:0.9rem;opacity:0.7;">Daily PnL</span>
            <span style="font-size:2rem;font-weight:700;{color_style}">${daily_pnl_total:,.2f}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )  
    


def format_currency(x):
    return "—" if pd.isnull(x) else f"${x:,.2f}"


def format_percent(x):
    return "—" if pd.isnull(x) else f"{x:.1f}%"


def format_shares(x):
    return "—" if pd.isnull(x) else f"{x:,.0f}"


styled_df = (
    df.style.format(
        {
            "Shares": format_shares,
            "Price": format_currency,
            "Value": format_currency,
            "Portfolio %": format_percent,
            "Daily PnL": format_currency,
        }
    )
    .applymap(style_pnl, subset=["Daily PnL"])
    .hide(axis="index")
)

st.dataframe(styled_df, use_container_width=True)

chart_df = df.dropna(subset=["Value"])
if not chart_df.empty:
    bar_chart = (
        alt.Chart(chart_df)
        .mark_bar()
        .encode(
            x=alt.X("Ticker:N", title="Ticker"),
            y=alt.Y("Value:Q", title="Value", axis=alt.Axis(format="$,.0f")),
            tooltip=[
                alt.Tooltip(field="Ticker", type="nominal"),
                alt.Tooltip(field="Value", type="quantitative", format="$,.2f", title="Value"),
                alt.Tooltip(field="Price", type="quantitative", format="$,.2f", title="Price"),
                alt.Tooltip(field="Portfolio %", type="quantitative", format=".1f", title="Portfolio %"),
                alt.Tooltip(field="Daily PnL", type="quantitative", format="$,.2f", title="Daily PnL"),
            ],
        )
        .properties(height=320)
    )
    st.altair_chart(bar_chart, use_container_width=True)
else:
    st.info("No price data available to chart.")


# add new stock form
st.markdown("### Add a New Stock")

with st.form("add_stock_form"):
    new_ticker = st.text_input("Stock Symbol (e.g., AAPL, MSFT, TSLA)").upper().strip()
    new_shares = st.number_input("Number of Shares", min_value=1, step=1)
    submitted = st.form_submit_button("Add Stock", use_container_width=True)

if submitted:
    if not new_ticker:
        st.error("Please enter a valid stock symbol.")
    else:
        # if the stock already exists, add shares
        if new_ticker in portfolio:
            portfolio[new_ticker] += int(new_shares)
            st.success(f"Added {new_shares} more shares of {new_ticker}.")
        else:
            portfolio[new_ticker] = int(new_shares)
            st.success(f"Added {new_ticker} with {new_shares} shares to your portfolio.")

        # save info back to users.json
        USERS[user]["portfolio"] = portfolio
        save_users(USERS)

        # force UI refresh
        st.rerun()


# update/ remove a stock
st.divider()
st.subheader("Update or Remove a Stock")

stock_options = [f"{ticker} ({shares} shares)" for ticker, shares in stocks]

option = st.selectbox(
"Select Existing Stock to Update or Remove",
stock_options,
index=None,
placeholder="Select Stock...",
help="Remove Stock")
st.write("Current Selection:", option)
print(stocks) # debugging line to be removed later

if option is not None:
    if st.button("Remove Stock", use_container_width=True):
       
        ticker_to_remove = option.split(" ")[0]

        if ticker_to_remove in portfolio:
           
            del portfolio[ticker_to_remove]
            #write back into USERS
            USERS[user]["portfolio"] = portfolio
            #save to users.json
            save_users(USERS)
            #refresh UI
            st.rerun()
        else:
            st.error("Error ticker not found")
    st.divider()



#stock news from finnhub
FINNHUB_API_KEY = st.secrets.get("FINNHUB_API_KEY")

if FINNHUB_API_KEY:

    @st.cache_data(ttl=3600)
    def get_stock_news(ticker):
        """Fetch recent company news from Finnhub (last 7 days)."""
        to_date = date.today()
        from_date = to_date - timedelta(days=7)
        url = (
            f"https://finnhub.io/api/v1/company-news"
            f"?symbol={ticker}&from={from_date}&to={to_date}&token={FINNHUB_API_KEY}"
        )
        try:
            r = requests.get(url, timeout=10)
        except requests.RequestException:
            return []
        if r.status_code == 200:
            return r.json()[:5]
        return []
    
    st.subheader(" Latest News for Your Stocks")

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
else:
    st.subheader("Latest News for Your Stocks")
    st.info("Add `FINNHUB_API_KEY` to `.streamlit/secrets.toml` to enable stock news.")
