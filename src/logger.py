"""
logger.py
---------
CSV-based event logging for the activity tracker, plus helpers for
summarizing a log file (used by the dashboard and CLI reports).
"""

import csv
import os
from datetime import datetime
from collections import defaultdict
from typing import Dict, List
import pandas as pd


class CSVActivityLogger:
    def __init__(self, log_file: str):
        self.log_file = log_file
        os.makedirs(os.path.dirname(log_file) or ".", exist_ok=True)
        is_new = not os.path.exists(log_file)
        self._f = open(log_file, "a", newline="")
        self._writer = csv.writer(self._f)
        if is_new:
            self._writer.writerow(["timestamp", "state", "duration_seconds"])

    def log(self, state: str, duration_seconds: float) -> None:
        self._writer.writerow([
            datetime.now().isoformat(timespec="seconds"),
            state,
            round(duration_seconds, 1),
        ])
        self._f.flush()

    def close(self) -> None:
        self._f.close()


def load_log(log_file: str) -> pd.DataFrame:
    if not os.path.exists(log_file):
        return pd.DataFrame(columns=["timestamp", "state", "duration_seconds"])
    df = pd.read_csv(log_file, parse_dates=["timestamp"])
    df["date"] = df["timestamp"].dt.date
    return df


def summarize(df: pd.DataFrame) -> Dict[str, float]:
    """Total seconds per state across the whole log."""
    if df.empty:
        return {}
    return df.groupby("state")["duration_seconds"].sum().to_dict()


def summarize_by_day(df: pd.DataFrame) -> pd.DataFrame:
    """Seconds per state, per day — handy for the dashboard's daily chart."""
    if df.empty:
        return pd.DataFrame(columns=["date", "state", "duration_seconds"])
    return df.groupby(["date", "state"])["duration_seconds"].sum().reset_index()


def print_summary(log_file: str) -> None:
    df = load_log(log_file)
    totals = summarize(df)
    total = sum(totals.values())
    print("--- Activity Log Summary ---")
    if total == 0:
        print("No data recorded yet.")
        return
    for state, secs in sorted(totals.items(), key=lambda x: -x[1]):
        pct = secs / total * 100
        print(f"{state:10s}: {secs/60:6.1f} min ({pct:5.1f}%)")
    print(f"{'TOTAL':10s}: {total/60:6.1f} min")
