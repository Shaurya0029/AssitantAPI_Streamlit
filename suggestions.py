"""
suggestions.py
===============

This module defines simple suggestion logic for MindMate. Based on the
detected mood from the journal entry, a short piece of advice or a
motivational prompt is generated. These suggestions are intentionally
general and non‑medical; they do not replace professional therapy or
psychiatric care.

The `get_suggestion` function accepts a mood label ("positive",
"negative", "neutral") and returns a string with an appropriate
suggestion. Additional mood types can be added by extending the
dictionary below.
"""


def get_suggestion(mood: str) -> str:
    """
    Provide a helpful suggestion based on the mood.

    Args:
        mood (str): One of "positive", "negative", or "neutral".

    Returns:
        str: A user‑friendly suggestion string.
    """
    suggestions = {
        "positive": (
            "Keep up the positive energy! Consider writing down three things you're grateful for."
        ),
        "negative": (
            "It might help to take a few deep breaths or go for a short walk. Reflect on what made you feel this way."
        ),
        "neutral": (
            "Perhaps try a short meditation or note one thing that went well today."
        ),
    }
    return suggestions.get(mood.lower(), "Take a moment to reflect on how you're feeling and write about it.")