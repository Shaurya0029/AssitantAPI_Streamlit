"""
journal.py
==========

This module contains utility functions for analyzing journal entries.
Because the environment used for this project may not have access to
external packages like TextBlob, we implement a very simple sentiment
analysis method using curated lists of positive and negative words.

The `analyze_emotion` function counts how many words from the entry
match the positive and negative lists, computes a basic polarity score,
and categorizes the mood accordingly. While not as sophisticated as
dedicated sentiment libraries, this approach avoids external
dependencies and still provides meaningful feedback for a student
project.
"""

from __future__ import annotations

import re
from typing import Tuple

# Curated lists of positive and negative words. These lists are not
# exhaustive but cover common emotions relevant for our mini project.
POSITIVE_WORDS = {
    "happy",
    "joy",
    "joyful",
    "good",
    "great",
    "love",
    "excited",
    "wonderful",
    "delighted",
    "content",
    "fortunate",
    "grateful",
    "calm",
}

NEGATIVE_WORDS = {
    "sad",
    "depressed",
    "down",
    "angry",
    "frustrated",
    "unhappy",
    "anxious",
    "nervous",
    "worried",
    "bad",
    "upset",
    "fear",
    "lonely",
    "hopeless",
}


def analyze_emotion(entry_text: str) -> Tuple[str, float]:
    """
    Analyze a journal entry and return the mood and basic polarity.

    The sentiment analysis is performed by tokenizing the input text,
    counting occurrences of positive and negative words, computing a
    normalized polarity value, and determining the mood category.

    Args:
        entry_text: The journal entry text written by the user.

    Returns:
        Tuple[str, float]: A tuple containing the mood category
            ("positive", "negative", or "neutral") and a polarity
            score between ‑1.0 and +1.0. A score of +1.0 indicates only
            positive words were found, ‑1.0 indicates only negative
            words, and 0.0 indicates no words from either list were
            found or equal amounts of both.
    """
    # Lowercase and tokenize the entry into words
    tokens = re.findall(r"\b\w+\b", entry_text.lower())
    pos_count = sum(1 for token in tokens if token in POSITIVE_WORDS)
    neg_count = sum(1 for token in tokens if token in NEGATIVE_WORDS)
    total = pos_count + neg_count

    # Compute a simple polarity score
    if total == 0:
        polarity = 0.0
    else:
        polarity = (pos_count - neg_count) / total

    # Determine mood category
    if polarity > 0.1:
        mood = "positive"
    elif polarity < -0.1:
        mood = "negative"
    else:
        mood = "neutral"

    return mood, polarity