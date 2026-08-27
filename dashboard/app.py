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

from src.logger import load_log, summarize, summarize_by_day, summarize_by_person

st.set_page_config(page_title="Worker Activity Monitor", layout="wide")
st.title("🖥️ Worker Activity Monitor")

log_file = st.sidebar.text_input("Log file path", "data/activity_log.csv")
df = load_log(log_file)

if df.empty:
    st.info("No data yet. Run `python main.py` to start logging activity.")
    st.stop()

is_multi_person = "person_id" in df.columns

if is_multi_person:
    people = sorted(df["person_id"].dropna().unique().tolist())
    selected = st.sidebar.selectbox("Person", ["All"] + [str(p) for p in people])
    if selected != "All":
        df = df[df["person_id"].astype(str) == selected]

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

# --- Per-person breakdown (multi-person mode only) ---
if is_multi_person and selected == "All":
    st.subheader("Per-person breakdown")
    by_person = summarize_by_person(df)
    by_person["minutes"] = by_person["duration_seconds"] / 60
    by_person["person_id"] = by_person["person_id"].astype(str)
    person_bar = px.bar(
        by_person,
        x="person_id",
        y="minutes",
        color="state",
        title="Minutes per state, per person",
        barmode="stack",
    )
    st.plotly_chart(person_bar, use_container_width=True)

# --- Raw log ---
with st.expander("Raw event log"):
    st.dataframe(df.sort_values("timestamp", ascending=False), use_container_width=True)
