"""
Simple emotion-aware chatbot for MindMate.

Public API:
- get_response(text: str) -> str
"""
from textblob import TextBlob
import re
import os
import json
import requests

# Optional OpenAI import; keep app functional if not installed
try:
    from openai import OpenAI  # type: ignore
except Exception:  # pragma: no cover
    OpenAI = None  # type: ignore

POS_THRESHOLD = 0.3
NEG_THRESHOLD = -0.3


def get_emotion(text: str) -> str:
    blob = TextBlob(text)
    polarity = blob.sentiment.polarity
    if polarity > POS_THRESHOLD:
        return "positive"
    if polarity < NEG_THRESHOLD:
        return "negative"
    return "neutral"


def _contains_any(text: str, phrases: list[str]) -> bool:
    return any(p in text for p in phrases)


def _question_like(text: str) -> bool:
    if "?" in text:
        return True
    return bool(re.match(r"\b(what|why|how|when|where|who|can|should|could|would|is|are|do|does)\b", text))


def detect_intent_and_emotion(user_input: str) -> dict:
    """Return a lightweight context dict with 'emotion' and 'intent'.

    intent values: achievement, gratitude, apology, anger, tiredness,
    overwhelm, confusion, loneliness, anxiety, journal, breathing,
    capability, greet, none
    """
    text = user_input.lower().strip()

    # Negation-aware emotion adjustments (e.g., "not happy" -> negative)
    positive_terms = [
        "happy", "good", "great", "excited", "okay", "ok", "fine", "positive", "calm", "content"
    ]
    negative_terms = [
        "sad", "down", "depressed", "anxious", "angry", "stressed", "worried", "upset"
    ]

    def _has_negated(terms: list[str]) -> bool:
        # Patterns: not X, not so X, not that X, not feeling X, don't feel X, do not feel X, no longer X
        for t in terms:
            patterns = [
                rf"\bnot (?:so |that )?{re.escape(t)}\b",
                rf"\bnot feeling (?:so |that )?{re.escape(t)}\b",
                rf"\bdon't feel (?:so |that )?{re.escape(t)}\b",
                rf"\bdo not feel (?:so |that )?{re.escape(t)}\b",
                rf"\bno longer (?:feel(?:ing)? )?{re.escape(t)}\b",
            ]
            for p in patterns:
                if re.search(p, text):
                    return True
        return False

    # Base emotion from TextBlob
    emotion = get_emotion(text)
    # Override with negation logic where applicable
    if _has_negated(positive_terms):
        emotion = "negative"
    elif _has_negated(negative_terms):
        # Flip strong negatives to neutral when negated
        emotion = "neutral"

    if _contains_any(text, [
        "i made", "i built", "i created", "i achieved", "i accomplished",
        "promotion", "got hired", "won", "passed", "nailed it",
        "big achievement", "proud of", "shipped"
    ]):
        intent = "achievement"
    elif _contains_any(text, ["thank you", "thanks", "appreciate it", "grateful"]):
        intent = "gratitude"
    elif _contains_any(text, ["sorry", "apologies", "my fault", "apologize"]):
        intent = "apology"
    elif _contains_any(text, ["angry", "mad", "furious", "pissed", "rage"]):
        intent = "anger"
    elif _contains_any(text, ["tired", "exhausted", "drained", "fatigued", "sleepy", "burnt out", "burned out"]):
        intent = "tiredness"
    elif _contains_any(text, ["overwhelmed", "too much", "can’t handle", "cant handle", "overloaded"]):
        intent = "overwhelm"
    elif _contains_any(text, ["confused", "don’t know", "dont know", "unsure", "uncertain"]):
        intent = "confusion"
    elif _contains_any(text, ["lonely", "alone", "isolated"]):
        intent = "loneliness"
    elif _contains_any(text, ["anxious", "anxiety", "worried", "stress", "stressed"]):
        intent = "anxiety"
    elif "journal" in text or _contains_any(text, ["write", "diary", "journaling", "notes"]):
        intent = "journal"
    elif _contains_any(text, ["breathe", "breathing", "grounding", "relax", "calm down"]):
        intent = "breathing"
    elif _contains_any(text, ["who are you", "what are you", "what can you do", "help me", "how can you help", "what can i do"]):
        intent = "capability"
    elif _contains_any(text, ["hello", "hi", "hey", "good morning", "good evening", "good afternoon"]):
        intent = "greet"
    else:
        intent = "none"

    return {"emotion": emotion, "intent": intent}


def get_response(user_input: str) -> str:
    if not user_input or not user_input.strip():
        return "I'm here to listen. How are you feeling today?"

    text = user_input.lower()
    ctx = detect_intent_and_emotion(text)
    emotion = ctx["emotion"]

    # Highly specific intents first
    if ctx["intent"] == "achievement":
        return "That’s amazing — congratulations! What part of this achievement makes you most proud?"
    if ctx["intent"] == "gratitude":
        return "You’re very welcome. I’m glad to be here for you."
    if ctx["intent"] == "apology":
        return "It’s okay to make mistakes. What would help you be kinder to yourself right now?"
    if ctx["intent"] == "anger":
        return "Anger can feel intense. Would a short grounding exercise help you release some of that tension?"
    if ctx["intent"] == "tiredness":
        return "You sound worn out. A quick rest, water, or a short walk might help. Want to plan a tiny break?"
    if ctx["intent"] == "overwhelm":
        return "Feeling overwhelmed is tough. Let’s break things into one small next step—what’s the first doable action?"
    if ctx["intent"] == "confusion":
        return "It’s okay to not have all the answers. What options are you considering right now?"
    if ctx["intent"] == "loneliness":
        return "You’re not alone. I’m here with you. Would reaching out to someone or journaling help right now?"
    if ctx["intent"] == "anxiety":
        return "Deep breathing can help. Want me to guide you through a short exercise?"
    if _contains_any(text, ["sad", "down", "depressed", "blue"]) or emotion == "negative":
        return "I'm here for you. Would you like to try a breathing exercise or write a journal entry?"
    if _contains_any(text, ["happy", "joy", "excited", "great", "good", "awesome", "fantastic", "grateful"]) or emotion == "positive":
        return "That's wonderful! Want to share what made your day so good?"
    if ctx["intent"] == "journal":
        return "Sure! Head to the Journal tab and write down your thoughts."
    if ctx["intent"] == "breathing":
        return "Try this: inhale for 4, hold for 4, exhale for 6 — repeat 4 times. How do you feel after that?"
    # Bot capability / meta questions
    if ctx["intent"] == "capability":
        return "I’m MindMate—here to listen, reflect, and offer gentle suggestions like journaling or simple breathing exercises. What would help most right now?"
    # Greetings (placed after specific intents so they don’t override)
    if ctx["intent"] == "greet":
        return "Hello! How are you feeling right now?"

    # Neutral and sentiment fallbacks
    if emotion == "positive":
        return "I love your positive energy. Would you like to capture this in your journal?"
    if emotion == "negative":
        return "That sounds tough. I'm here for you. Want to talk more or write about it?"
    if _question_like(text):
        return "That’s a thoughtful question. What outcome would feel right for you? Sometimes writing your thoughts helps clarify."
    return "I'm listening. Tell me a bit more about what’s on your mind."


def llm_available() -> bool:
    # Either OpenAI or Ollama should make us available
    if os.getenv("OPENAI_API_KEY") and OpenAI is not None:
        return True
    # Ollama URL (default local) can be used without key
    return bool(os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"))


def get_llm_response(user_input: str, history: list[dict] | None = None, style: str = "concise") -> str | None:
    """Return an LLM-generated response if configured, else None.

    Expects history as a list of {"role": "user"|"assistant", "content": str}.
    """
    if not llm_available():
        return None
    openai_key = os.getenv("OPENAI_API_KEY")
    use_openai = bool(openai_key and OpenAI is not None)
    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini") if use_openai else os.getenv("OLLAMA_MODEL", "llama3.2")

    if style == "detailed":
        system_prompt = (
            "You are MindMate, an empathetic mental wellness companion. "
            "Be warm, validating, and human-like. Write a fuller response (2-4 short paragraphs). "
            "1) Acknowledge and reflect the user's message in your own words. "
            "2) Offer 1-2 practical, gentle suggestions (e.g., journaling prompts, breathing, small next steps). "
            "3) End with exactly one open-ended question to keep the conversation going. "
            "Avoid medical diagnoses or judgments. Keep language simple, hopeful, and grounded. "
            "If appropriate, connect to recent parts of the conversation without repeating the same line."
        )
    else:
        system_prompt = (
            "You are MindMate, an empathetic mental wellness companion. "
            "Be warm, supportive, non-judgmental. Keep replies concise (1-2 short paragraphs). "
            "Offer gentle suggestions like journaling or breathing, and ask at most one follow-up question."
        )

    messages = [{"role": "system", "content": system_prompt}]
    if history:
        # cap the context to last 10 turns for efficiency
        for m in history[-10:]:
            role = m.get("role", "user")
            content = m.get("content", "")
            if content:
                messages.append({"role": role, "content": content})
    messages.append({"role": "user", "content": user_input})

    try:
        if use_openai:
            client = OpenAI()
            resp = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=float(os.getenv("OPENAI_TEMPERATURE", "0.7")),
                max_tokens=int(os.getenv("OPENAI_MAX_TOKENS", "500")),
            )
            return resp.choices[0].message.content.strip() if resp.choices else None
        else:
            # Ollama chat via HTTP API
            base = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
            url = f"{base.rstrip('/')}/api/chat"
            payload = {
                "model": model,
                "messages": messages,
                "stream": False,
                "options": {
                    "temperature": float(os.getenv("OLLAMA_TEMPERATURE", "0.7"))
                }
            }
            r = requests.post(url, json=payload, timeout=60)
            r.raise_for_status()
            data = r.json()
            # Ollama returns {message:{role, content}}
            content = data.get("message", {}).get("content") or data.get("response")
            return content.strip() if content else None
    except Exception:
        return None


def generate_reply(user_input: str, history: list[dict] | None = None, style: str = "concise") -> str:
    """Unified reply generator: prefer LLM if available, else rule-based."""
    llm = get_llm_response(user_input, history, style=style)
    if llm:
        return llm
    return get_response(user_input)