"""
MindMate Flask Application
===========================

This file defines the Flask web application for the MindMate project. The
application combines a simple rule‑based chatbot with an emotion‑aware
journal. Users can interact with the chatbot on the main page, submit
journal entries on the journal page, view mood trends on the mood page,
and receive suggestions based on the sentiment of their journal entries.

The application stores all journal data locally in a SQLite database,
avoiding any external network calls or cloud services. The project is
designed for educational purposes and does not attempt to diagnose or
treat mental health conditions. Instead, it provides basic self‑help
prompts and encourages users to reflect on their emotions.

To run the application locally, ensure you have installed the required
libraries listed in the requirements.txt file (Flask, TextBlob, NLTK,
Matplotlib, etc.). You can then start the server with `python app.py`
and visit http://localhost:5000/ in your browser.

Disclaimer:
    This project is a student‑built tool intended for self‑reflection.
    It is not a substitute for professional mental health care. If you
    are in crisis or need urgent assistance, please contact a qualified
    mental health professional.
"""

from datetime import datetime
import os
import sqlite3

from flask import Flask, request

from chatbot import get_bot_response
from journal import analyze_emotion
from mood_plot import plot_mood_trend
from suggestions import get_suggestion

# We no longer require NLTK for tokenization because sentiment
# analysis is implemented using simple word lists in journal.py. If
# additional NLP features are added in the future, the NLTK download
# call can be reinstated here.


def get_db_connection() -> sqlite3.Connection:
    """Return a connection to the local SQLite database.

    If the database file does not yet exist, it will be created
    automatically. We also enable row_factory so rows behave like
    dictionaries when accessed.

    Returns:
        sqlite3.Connection: A connection object to the SQLite database.
    """
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Create the journal_entries table if it does not already exist."""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS journal_entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            content TEXT NOT NULL,
            mood TEXT NOT NULL,
            polarity REAL NOT NULL
        )
        """
    )
    conn.commit()
    conn.close()


def ensure_static_dir() -> None:
    """Ensure the static directory exists for storing images."""
    if not os.path.isdir("static"):
        os.makedirs("static")


# Initialize the database and static directory at import time so that the
# application is ready to store data as soon as it starts. The calls
# happen once when this module is imported.
init_db()
ensure_static_dir()


app = Flask(__name__)


@app.route("/", methods=["GET", "POST"])
def index():
    """
    Display the main chatbot page.

    On GET requests, show the form for entering a message to the chatbot.
    On POST requests, process the user's input and generate a response
    using the rule‑based chatbot defined in chatbot.py. A link to the
    journal and mood pages is provided for easy navigation.

    Returns:
        str: Rendered HTML content.
    """
    response = ""
    if request.method == "POST":
        user_input = request.form.get("message", "")
        if user_input.strip():
            response = get_bot_response(user_input)
    # Construct minimal HTML. For a production app you would
    # typically use templates, but inline HTML keeps this example simple.
    content = []
    content.append("<h1>MindMate Chatbot</h1>")
    content.append("<p>A simple chatbot for mental wellness.</p>")
    content.append(
        "<form method='post'>"
        "<input type='text' name='message' placeholder='Type your message here' style='width: 70%;'/>"
        "<input type='submit' value='Send'/></form>"
    )
    if response:
        content.append(f"<p><strong>Bot:</strong> {response}</p>")
    content.append(
        "<p>Navigate: "
        "<a href='/journal'>Journal</a> | "
        "<a href='/mood'>Mood Trends</a>"
        "</p>"
    )
    # Disclaimer at bottom of the page
    content.append(
        "<small>This tool is for self‑help purposes only and does not replace professional mental health care.</small>"
    )
    return "\n".join(content)


@app.route("/journal", methods=["GET", "POST"])
def journal():
    """
    Display the journal entry page and process entries.

    Users can submit free‑text journal entries. The entry is analyzed
    for sentiment using TextBlob, stored in the SQLite database, and a
    simple suggestion is generated based on the detected mood. The
    detected mood and suggestion are displayed on the page along with
    navigation links.

    Returns:
        str: Rendered HTML content.
    """
    message = ""
    suggestion = ""
    detected_mood = ""
    if request.method == "POST":
        entry_text = request.form.get("entry", "").strip()
        if entry_text:
            mood, polarity = analyze_emotion(entry_text)
            # Store the entry in the database
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO journal_entries (date, content, mood, polarity) VALUES (?, ?, ?, ?)",
                (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), entry_text, mood, polarity),
            )
            conn.commit()
            conn.close()
            detected_mood = mood
            suggestion = get_suggestion(mood)
            message = "Entry saved successfully!"
    content = []
    content.append("<h1>Journal Entry</h1>")
    content.append("<form method='post'>")
    content.append(
        "<textarea name='entry' rows='5' cols='60' placeholder='Write your journal entry here'></textarea>"
    )
    content.append("<br><input type='submit' value='Submit Entry'/></form>")
    if message:
        content.append(f"<p style='color:green;'>{message}</p>")
    if detected_mood:
        content.append(f"<p><strong>Detected mood:</strong> {detected_mood}</p>")
    if suggestion:
        content.append(f"<p><strong>Suggestion:</strong> {suggestion}</p>")
    content.append(
        "<p>Navigate: "
        "<a href='/'>Chatbot</a> | "
        "<a href='/mood'>Mood Trends</a>"
        "</p>"
    )
    content.append(
        "<small>This tool is for self‑help purposes only and does not replace professional mental health care.</small>"
    )
    return "\n".join(content)


@app.route("/mood")
def mood():
    """
    Display the mood trend page.

    This route generates a PNG image of the user's mood over time
    using Matplotlib and reads it from the static folder. If there are
    no entries yet, a placeholder message is shown. The page also
    includes navigation back to other pages.

    Returns:
        str: Rendered HTML content.
    """
    # Generate the chart; the function will save the file into the static folder.
    chart_path = plot_mood_trend()
    content = []
    content.append("<h1>Mood Trend Over Time</h1>")
    if chart_path:
        content.append(
            f"<img src='/{chart_path}' alt='Mood trend chart' style='max-width:90%; height:auto;'/>"
        )
    else:
        content.append("<p>No journal entries yet. Add entries to see your mood trend.</p>")
    content.append(
        "<p>Navigate: "
        "<a href='/'>Chatbot</a> | "
        "<a href='/journal'>Journal</a>"
        "</p>"
    )
    content.append(
        "<small>This tool is for self‑help purposes only and does not replace professional mental health care.</small>"
    )
    return "\n".join(content)


if __name__ == "__main__":
    # When running this file directly, launch the Flask development server.
    app.run(debug=True)