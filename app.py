"""
MindMate Streamlit App
======================

A simple, empathetic mental wellness chat interface.
Run with: streamlit run app.py
"""

import streamlit as st
from chatbot import generate_reply, detect_intent_and_emotion
from datetime import datetime
from database import init_db, get_db_connection
from journal import analyze_emotion
from suggestions import get_suggestion
from mood_plot import plot_mood_trend

st.set_page_config(page_title="MindMate", page_icon="🧠", layout="centered")

st.title("MindMate 🧠💬")
st.caption("A simple, empathetic mental wellness companion")

# Ensure database exists for Journal/Mood pages
init_db()

page = st.sidebar.radio("Navigate", ["Chat", "Journal", "Mood Trends"], index=0)
reply_style = st.sidebar.selectbox("Reply Style", ["concise", "detailed"], index=1)
memory_enabled = st.sidebar.toggle("Enable memory hints", value=True)
source_filter = st.sidebar.multiselect("Trend Sources", ["chat", "journal"], default=["chat", "journal"]) if page == "Mood Trends" else None

if "messages" not in st.session_state:
    st.session_state.messages = []
if "last_intent" not in st.session_state:
    st.session_state.last_intent = None
if "last_emotion" not in st.session_state:
    st.session_state.last_emotion = None
if "last_achievement" not in st.session_state:
    st.session_state.last_achievement = None


if page == "Chat":
    for m in st.session_state.messages:
        with st.chat_message(m["role"]):
            st.markdown(m["content"])

    prompt = st.chat_input("Type a message")
    if prompt:
        # Detect context before generating reply
        ctx = detect_intent_and_emotion(prompt)
        # Handle explicit negations like "I'm not angry"
        if "not angry" in prompt.lower():
            ctx["intent"] = "none"
            ctx["emotion"] = "neutral"
        # Cache topic details
        if ctx["intent"] == "achievement":
            st.session_state.last_achievement = prompt
        st.session_state.last_intent = ctx["intent"]
        st.session_state.last_emotion = ctx["emotion"]

        st.session_state.messages.append({"role": "user", "content": prompt})
        # Log chat mood signal
        with get_db_connection() as conn:
            conn.execute(
                "INSERT INTO mood_signals (date, source, content, mood, polarity) VALUES (?, ?, ?, ?, ?)",
                (
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "chat",
                    prompt,
                    ctx["emotion"],
                    1.0 if ctx["emotion"] == "positive" else (-1.0 if ctx["emotion"] == "negative" else 0.0),
                ),
            )
        with st.chat_message("user"):
            st.markdown(prompt)
        # Build brief history for LLM context
        history = st.session_state.messages[-10:]
        base = generate_reply(prompt, history, style=reply_style)

        # Light short-term memory: weave recent context into the assistant reply
        # Throttle memory to avoid repetition; only show when changing topics/emotions
        if "_memory_hint_shown" not in st.session_state:
            st.session_state._memory_hint_shown = False

        memory_line = None
        if memory_enabled and st.session_state.last_intent in {"achievement", "overwhelm", "anger", "tiredness", "anxiety"}:
            hints = {
                "achievement": "Earlier you mentioned a win — congrats again.",
                "overwhelm": "Earlier you mentioned feeling overwhelmed.",
                "anger": "Earlier you mentioned feeling angry.",
                "tiredness": "Earlier you mentioned feeling worn out.",
                "anxiety": "Earlier you mentioned feeling anxious.",
            }
            if not st.session_state._memory_hint_shown:
                memory_line = hints[st.session_state.last_intent]
                # Enrich achievement with a brief reference (topic-aware memory)
                if st.session_state.last_intent == "achievement" and st.session_state.last_achievement:
                    snippet = st.session_state.last_achievement[:80]
                    memory_line += f" (about: ‘{snippet}{'…' if len(st.session_state.last_achievement)>80 else ''}’)"
                st.session_state._memory_hint_shown = True
        elif memory_enabled and st.session_state.last_emotion in {"positive", "negative"}:
            if not st.session_state._memory_hint_shown and ctx["emotion"] == st.session_state.last_emotion:
                memory_line = (
                    "I’m glad to hear your energy is up." if st.session_state.last_emotion == "positive" else
                    "I’m keeping things gentle since it sounded tough earlier."
                )
                st.session_state._memory_hint_shown = True

        reply = f"{memory_line} {base}".strip() if memory_line else base
        st.session_state.messages.append({"role": "assistant", "content": reply})
        with st.chat_message("assistant"):
            st.markdown(reply)

elif page == "Journal":
    st.subheader("Journal Entry")
    with st.form("journal_form", clear_on_submit=True):
        entry = st.text_area("Write your thoughts", placeholder="What's on your mind today?", height=150)
        submitted = st.form_submit_button("Save Entry")
        if submitted and entry.strip():
            mood, polarity = analyze_emotion(entry)
            with get_db_connection() as conn:
                conn.execute(
                    "INSERT INTO journal_entries (date, content, mood, polarity) VALUES (?, ?, ?, ?)",
                    (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), entry, mood, polarity),
                )
                conn.execute(
                    "INSERT INTO mood_signals (date, source, content, mood, polarity) VALUES (?, ?, ?, ?, ?)",
                    (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "journal", entry, mood, polarity),
                )
            st.success("Entry saved!")
            st.info(f"Detected mood: {mood} | Polarity: {polarity:.2f}")
            st.write(get_suggestion(mood))

    # Recent entries preview
    conn = get_db_connection()
    rows = conn.execute("SELECT date, mood, content FROM journal_entries ORDER BY date DESC LIMIT 5").fetchall()
    conn.close()
    if rows:
        st.divider()
        st.caption("Recent entries")
        for r in rows:
            st.markdown(f"- {r['date']} — {r['mood']}: {r['content'][:80]}{'…' if len(r['content'])>80 else ''}")
    else:
        st.caption("No entries yet. Your first one will appear here.")

elif page == "Mood Trends":
    st.subheader("Mood Trend Over Time")
    # Optional source filtering by user choice
    if source_filter and set(source_filter) != {"chat", "journal"}:
        # On-the-fly filter: generate a filtered trend image by reading DB directly
        # For simplicity, reuse plot_mood_trend() when all sources; otherwise render inline using pandas
        import sqlite3
        import matplotlib.pyplot as plt
        import os

        conn = sqlite3.connect("database.db")
        cur = conn.cursor()
        qmarks = ",".join(["?"] * len(source_filter)) or "?"
        cur.execute(f"SELECT date, mood FROM mood_signals WHERE source IN ({qmarks}) ORDER BY date ASC", source_filter)
        rows = cur.fetchall()
        conn.close()

        if rows:
            dates = [r[0] for r in rows]
            vals = [1 if r[1].lower()=="positive" else (-1 if r[1].lower()=="negative" else 0) for r in rows]
            plt.figure(figsize=(8, 4))
            plt.plot(dates, vals, marker="o", linestyle="-", linewidth=1.5)
            plt.title("Mood Trend (Filtered)")
            plt.xlabel("Date")
            plt.ylabel("Mood Value (positive=1, neutral=0, negative=-1)")
            plt.xticks(rotation=45)
            plt.grid(True, linestyle="--", linewidth=0.5)
            plt.tight_layout()
            out = os.path.join("static", "mood_trend_filtered.png")
            os.makedirs("static", exist_ok=True)
            plt.savefig(out)
            plt.close()
            st.image(out, caption="Mood trend (filtered)", use_column_width=True)
        else:
            st.info("No mood data for the selected source(s). Try chatting or adding a journal entry.")
    else:
        path = plot_mood_trend()
        if path:
            st.image(path, caption="Mood trend", use_column_width=True)
        else:
            st.info("No mood data yet. Chat or add journal entries to see your trend.")