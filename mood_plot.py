"""
mood_plot.py
============

This module provides a function to generate a mood trend chart from
journal entries stored in a SQLite database. The chart shows the
sentiment polarity over time, helping users visualize their emotional
patterns. The resulting image is saved to the static folder so it can be
served by Flask.

The plot uses Matplotlib and assigns numeric values to moods for
consistency: positive = 1, neutral = 0, negative = -1. Dates are
displayed on the x-axis, and mood values on the y-axis. If no data
exists yet, the function will skip chart creation and return None.
"""

import os
import sqlite3
from typing import Optional

import matplotlib.pyplot as plt


def _ensure_static_dir() -> str:
    """Ensure that the static directory exists and return its path."""
    static_dir = "static"
    if not os.path.isdir(static_dir):
        os.makedirs(static_dir)
    return static_dir


def plot_mood_trend() -> Optional[str]:
    """
    Generate a mood trend chart from the journal database.

    Reads all entries from the `journal_entries` table, converts the
    moods to numeric values, and plots them against their dates. The
    image is saved as mood_trend.png in the static directory. If there
    are no journal entries, returns None.

    Returns:
        Optional[str]: The relative path to the saved image, or None if
            no chart was generated.
    """
    conn = sqlite3.connect("database.db")
    cur = conn.cursor()
    # Prefer unified mood_signals if present, else fallback to journal_entries
    try:
        cur.execute("SELECT date, mood FROM mood_signals ORDER BY date ASC")
        rows = cur.fetchall()
        if not rows:
            raise ValueError("empty mood_signals")
    except Exception:
        cur.execute("SELECT date, mood FROM journal_entries ORDER BY date ASC")
        rows = cur.fetchall()
    conn.close()

    if not rows:
        # No data yet; skip chart creation
        return None

    dates = [row[0] for row in rows]
    mood_values = []
    for _, mood in rows:
        if mood.lower() == "positive":
            mood_values.append(1)
        elif mood.lower() == "negative":
            mood_values.append(-1)
        else:
            mood_values.append(0)

    # Create a new figure and plot the data
    plt.figure(figsize=(8, 4))
    plt.plot(dates, mood_values, marker="o", linestyle="-", linewidth=1.5)
    plt.title("Mood Trend Over Time")
    plt.xlabel("Date")
    plt.ylabel("Mood Value (positive=1, neutral=0, negative=-1)")
    plt.xticks(rotation=45)
    plt.grid(True, which="major", linestyle="--", linewidth=0.5)
    plt.tight_layout()

    static_dir = _ensure_static_dir()
    chart_filename = "mood_trend.png"
    chart_path = os.path.join(static_dir, chart_filename)
    plt.savefig(chart_path)
    plt.close()

    return os.path.join("static", chart_filename)