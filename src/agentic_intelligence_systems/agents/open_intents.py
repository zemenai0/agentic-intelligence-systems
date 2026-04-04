"""Heuristics for open-domain conversational intents."""

from __future__ import annotations

from dataclasses import dataclass


GREETING_WORDS = {"hi", "hey", "hello", "good morning", "good afternoon", "good evening"}
IDENTITY_PHRASES = {
    "who are you",
    "what are you",
    "what can you do",
    "introduce yourself",
}
HOSTILE_WORDS = {
    "fuck", "stupid", "idiot", "useless", "damn", "shit", "hate",
}
QUESTION_WORDS = {
    "who", "what", "when", "where", "why",
    "how", "which", "is", "are", "can", "could", "do", "does", "did",
}
OPEN_HELP_PHRASES = {
    "help", "help me",
    "please tell me", "tell me",
    "can you help me", "could you help me",
    "i need help", "assist me",
}
KNOWLEDGE_LEADS = {
    "explain", "define",
    "tell me about", "give me an overview of",
}


@dataclass(slots=True)
class OpenIntentMatch:
    """Open-domain planner hint."""

    intent: str
    agent_name: str
    confidence: float


def detect_open_intent(message: str) -> OpenIntentMatch | None:
    """Detect non-task conversational intents."""

    normalized = " ".join(message.lower().split())
    if _is_greeting(normalized):
        return OpenIntentMatch("greeting", "InteractionAgent", 0.95)
    if _contains_phrase(normalized, IDENTITY_PHRASES):
        return OpenIntentMatch("identity", "InteractionAgent", 0.95)
    if _contains_hostility(normalized):
        return OpenIntentMatch("hostile_repair", "InteractionAgent", 0.88)
    if normalized in OPEN_HELP_PHRASES or _contains_phrase(normalized, {"help me", "can you help"}):
        return OpenIntentMatch("general_support", "InteractionAgent", 0.72)
    if _contains_phrase(normalized, KNOWLEDGE_LEADS):
        return OpenIntentMatch("general_knowledge", "SearchKnowledgeAgent", 0.8)
    if _looks_like_question(normalized):
        return OpenIntentMatch("general_knowledge", "SearchKnowledgeAgent", 0.78)
    return None


def _is_greeting(normalized: str) -> bool:
    if normalized in GREETING_WORDS:
        return True
    return any(normalized.startswith(f"{word} ") for word in GREETING_WORDS)


def _contains_phrase(normalized: str, phrases: set[str]) -> bool:
    return any(phrase in normalized for phrase in phrases)


def _contains_hostility(normalized: str) -> bool:
    return any(word in normalized for word in HOSTILE_WORDS)


def _looks_like_question(normalized: str) -> bool:
    tokens = normalized.split()
    if not tokens:
        return False
    if normalized.endswith("?"):
        return True
    return tokens[0] in QUESTION_WORDS
