"""
Streamlit dashboard for the Worker Activity Monitor.

Run with:
    streamlit run dashboard/app.py
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import streamlit as st
import plotly.express as px

from src.logger import load_log, summarize, summarize_by_day

st.set_page_config(page_title="Worker Activity Monitor", layout="wide")
st.title("🖥️ Worker Activity Monitor")

log_file = st.sidebar.text_input("Log file path", "data/activity_log.csv")
df = load_log(log_file)

if df.empty:
    st.info("No data yet. Run `python main.py` to start logging activity.")
    st.stop()

# --- Overall summary ---
totals = summarize(df)
total_seconds = sum(totals.values())

st.subheader("Overall breakdown")
cols = st.columns(len(totals) if totals else 1)
for col, (state, secs) in zip(cols, sorted(totals.items(), key=lambda x: -x[1])):
    pct = secs / total_seconds * 100 if total_seconds else 0
    col.metric(state, f"{secs/60:.1f} min", f"{pct:.1f}%")

pie = px.pie(
    names=list(totals.keys()),
    values=list(totals.values()),
    title="Time distribution by state",
)
st.plotly_chart(pie, use_container_width=True)

# --- Daily breakdown ---
st.subheader("Daily breakdown")
daily = summarize_by_day(df)
daily["minutes"] = daily["duration_seconds"] / 60

bar = px.bar(
    daily,
    x="date",
    y="minutes",
    color="state",
    title="Minutes per state, per day",
    barmode="stack",
)
st.plotly_chart(bar, use_container_width=True)

# --- Raw log ---
with st.expander("Raw event log"):
    st.dataframe(df.sort_values("timestamp", ascending=False), use_container_width=True)
