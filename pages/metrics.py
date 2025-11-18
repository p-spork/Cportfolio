import json
from datetime import date, timedelta
from pathlib import Path

import altair as alt
import numpy as np
import pandas as pd
import streamlit as st
import yfinance as yf
from storage import load_users, save_users

st.set_page_config(page_title="Cportfolio - Metrics", page_icon="", layout="wide")

USERS = load_users()

# ensure login to access portfolio metrics
if "user" not in st.session_state or st.session_state.user is None:
    st.warning("Please log in to access portfolio metrics.")
    st.switch_page("home.py")

user = st.session_state.user
portfolio = USERS.get(user, {}).get("portfolio", {})

st.title("Portfolio Metrics")
st.caption("Run historical performance analytics on your holdings.")

if not portfolio:
    st.info(
        "No holdings found for your account. Add positions on the dashboard to begin."
    )
    st.stop()


@st.cache_data
def fetch_history(tickers: tuple[str, ...], start: date, end: date) -> pd.DataFrame:
    """Download adjusted close prices for the provided tickers."""
    if not tickers:
        return pd.DataFrame()

    frames = []
    labels = []
    # yfinance treats the end date as exclusive, so include an extra day
    end_plus_one = end + timedelta(days=1)

    for ticker in tickers:
        try:
            history = yf.download(
                ticker,
                start=start,
                end=end_plus_one,
                progress=False,
            )
        except Exception:
            continue
        if history is None or history.empty:
            continue
        series = history.get("Adj Close")
        if series is None or series.dropna().empty:
            series = history.get("Close")
        if series is None or series.dropna().empty:
            continue
        frames.append(series.dropna())
        labels.append(ticker)

    if not frames:
        return pd.DataFrame()

    prices = pd.concat(frames, axis=1)
    prices.columns = labels
    prices = prices.sort_index().ffill()
    return prices.dropna(how="all")


today = date.today()
default_start = today - timedelta(days=365)

col_period, col_benchmark = st.columns([2, 1])
with col_period:
    date_range = st.date_input(
        "Backtest period",
        (default_start, today),
        max_value=today,
    )
# three main chosen benchmarks, can easily be changed but these represent the overall market well
with col_benchmark:
    benchmark_map = {
        "Vanguard 500 Index (VFINX)": "VFINX",
        "SPDR S&P 500 ETF (SPY)": "SPY",
        "Vanguard Total Market ETF (VTI)": "VTI",
    }
    benchmark_label = st.selectbox(
        "Benchmark",
        list(benchmark_map.keys()),
        index=0,
    )
benchmark_ticker = benchmark_map[benchmark_label]

if not isinstance(date_range, tuple) or len(date_range) != 2:
    st.error("Please select a start and end date for the backtest.")
    st.stop()

start_date, end_date = date_range

if start_date >= end_date:
    st.error("The start date must be earlier than the end date.")
    st.stop()

portfolio_tickers = tuple(portfolio.keys())
price_history = fetch_history(portfolio_tickers, start_date, end_date)
benchmark_history = fetch_history((benchmark_ticker,), start_date, end_date)

if price_history.empty:
    st.error("Unable to download price history for your portfolio holdings.")
    st.stop()

if benchmark_history.empty:
    st.error(f"Unable to download price history for benchmark {benchmark_ticker}.")
    st.stop()

# restrict to tickers we successfully retrieved
available_tickers = [col for col in portfolio_tickers if col in price_history.columns]
if not available_tickers:
    st.error("No overlapping price data found for your holdings in the selected range.")
    st.stop()

shares = pd.Series(portfolio, dtype=float).loc[available_tickers]
prices = price_history[available_tickers]

# calculate the portfolio value through time
portfolio_values = prices.multiply(shares, axis=1).sum(axis=1)
portfolio_values = portfolio_values.dropna()

benchmark_series = benchmark_history.iloc[:, 0].dropna()

if portfolio_values.empty or benchmark_series.empty:
    st.error("Not enough data to run the backtest over the selected dates.")
    st.stop()

combined_index = pd.concat(
    [portfolio_values.rename("Portfolio"), benchmark_series.rename("Benchmark")],
    axis=1,
    join="inner",
).dropna()

if combined_index.empty:
    st.error("Portfolio and benchmark did not share overlapping trading days.")
    st.stop()

normalized = combined_index / combined_index.iloc[0] * 100
normalized = normalized.reset_index().rename(columns={"index": "Date"})
normalized = normalized.melt(
    id_vars="Date", value_vars=["Portfolio", "Benchmark"], var_name="Series", value_name="Value"
)

line_chart = (
    alt.Chart(normalized)
    .mark_line()
    .encode(
        x=alt.X("Date:T"),
        y=alt.Y("Value:Q", title="Growth of $100"),
        color=alt.Color("Series:N", title=""),
        tooltip=[
            alt.Tooltip("Date:T"),
            alt.Tooltip("Series:N"),
            alt.Tooltip("Value:Q", title="Indexed Value", format=".2f"),
        ],
    )
    .properties(height=420)
)

# performance metrics
daily_returns = combined_index.pct_change().dropna()
portfolio_daily = daily_returns["Portfolio"]
benchmark_daily = daily_returns["Benchmark"]

total_return = combined_index["Portfolio"].iloc[-1] / combined_index["Portfolio"].iloc[0] - 1
benchmark_total_return = (
    combined_index["Benchmark"].iloc[-1] / combined_index["Benchmark"].iloc[0] - 1
)

trading_days = len(portfolio_daily)

if trading_days > 0:
    annualization_factor = 252 / trading_days
    annual_return = (1 + total_return) ** annualization_factor - 1
    benchmark_annual_return = (1 + benchmark_total_return) ** annualization_factor - 1
    annual_volatility = portfolio_daily.std(ddof=0) * np.sqrt(252)
    benchmark_volatility = benchmark_daily.std(ddof=0) * np.sqrt(252)
    if not np.isnan(annual_volatility) and not np.isclose(annual_volatility, 0.0):
        sharpe = (portfolio_daily.mean() * 252) / annual_volatility
    else:
        sharpe = np.nan
    tracking_error = (
        (portfolio_daily - benchmark_daily).std(ddof=0) * np.sqrt(252)
        if not benchmark_daily.empty
        else np.nan
    )
else:
    annual_return = benchmark_annual_return = np.nan
    annual_volatility = benchmark_volatility = np.nan
    sharpe = tracking_error = np.nan

def format_pct(x: float) -> str:
    return "—" if pd.isna(x) else f"{x * 100:.2f}%"


def format_ratio(x: float) -> str:
    return "—" if pd.isna(x) else f"{x:.2f}"


metrics_display = pd.DataFrame(
    {
        "Portfolio": [
            format_pct(total_return),
            format_pct(annual_return),
            format_pct(annual_volatility),
            format_ratio(sharpe),
            format_pct(tracking_error),
        ],
        "Benchmark": [
            format_pct(benchmark_total_return),
            format_pct(benchmark_annual_return),
            format_pct(benchmark_volatility),
            "—",
            "—",
        ],
    },
    index=[
        "Total Return",
        "Annualized Return",
        "Annualized Volatility",
        "Sharpe Ratio",
        "Tracking Error vs Benchmark",
    ],
)

st.subheader("Performance Backtest")
st.altair_chart(line_chart, use_container_width=True)

st.subheader("Backtest Metrics")
st.dataframe(
    metrics_display,
    use_container_width=True,
)


st.caption(
    "Performance metrics assume a constant allocation with no fees or dividends, "
    "and use adjusted closing prices where available."
)

# code for the sidebar
st.sidebar.success(f"Logged in as {user}")
if st.sidebar.button("Log out", use_container_width=True):
    st.session_state.user = None
    st.switch_page("home.py")