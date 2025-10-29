"""
AI Service for OpenAI API integration.
Handles task parsing, prioritization, and summary generation.
"""

from __future__ import annotations

import os
import json
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from dateutil import parser as date_parser  # For deadline normalization
from .translation_service import translation_service

# -----------------------------
# Helpers
# -----------------------------

def _strip_ordinals(text: str) -> str:
    return re.sub(r"(\d+)(st|nd|rd|th)\b", r"\1", text, flags=re.I)

def _clean_title_phrase(title: str) -> str:
    """
    Remove introductory phrases like:
    - "add a reminder to"
    - "please"
    - "remind me to"
    - "i should"
    And trim commas, periods, extra space.
    """
    title = title.lower()
    cleanup_rules = [
        r"^(add a reminder to\s*)",
        r"^(remind me to\s*)",
        r"^(set a reminder to\s*)",
        r"^(please\s*)",
        r"^(i need to\s*)",
        r"^(i should\s*)",
        r"^(have to\s*)",
    ]
    for rule in cleanup_rules:
        title = re.sub(rule, "", title, flags=re.I)

    title = title.strip(" .,-").strip()
    return title

def normalize_deadline(deadline_str: Optional[str]) -> Optional[str]:
    if not deadline_str:
        return None
    try:
        s = _strip_ordinals(str(deadline_str).strip())
        dt = date_parser.parse(s, dayfirst=True, fuzzy=True)
        return dt.isoformat()
    except Exception:
        return None

def _guess_deadline_from_text(text: str) -> Optional[str]:
    if not text:
        return None
    s = _strip_ordinals(text)

    for dayfirst in (True, False):
        try:
            dt = date_parser.parse(s, dayfirst=dayfirst, fuzzy=True)
            if dt.hour == 0 and dt.minute == 0 and not re.search(r"\d{1,2}:\d{2}|\b(am|pm)\b", s, re.I):
                dt = dt.replace(hour=23, minute=59)
            return dt.isoformat()
        except Exception:
            continue
    return None

def get_openai_client():
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("[AIService] OpenAI API key not configured")
        return None

    try:
        from openai import OpenAI
        os.environ["OPENAI_API_KEY"] = api_key
        return OpenAI()
    except Exception as e:
        print(f"[AIService] Failed to create OpenAI client: {e}")
        return None

# -----------------------------
# Service
# -----------------------------

class AIService:

    @staticmethod
    def _model_name() -> str:
        return os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    @staticmethod
    def _post_clean_title_english(title: str) -> str:
        """Make English title concise."""
        # Remove trailing deadlines/priority parts
        stop_words = [
            "by ", "before ", "due ", "deadline", "priority", "urgent",
            "high priority", "low priority", "medium priority"
        ]
        low = title.lower()
        for w in stop_words:
            if w in low:
                title = title[: low.index(w)]
        return title.strip(" ,.-")

    @staticmethod
    def _detect_academic_category(text: str) -> Optional[str]:
        academic_keywords = ["assignment", "homework", "project", "lab report", "exam", "college", "university"]
        text_low = text.lower()
        return "education" if any(k in text_low for k in academic_keywords) else None

    @staticmethod
    def parse_natural_language_task(user_input: str) -> Dict:
        translation = translation_service.translate_to_english(user_input)
        original_text = translation["original_text"]
        english_text = translation["translated_text"]
        source_lang = translation["source_language"]

        multilingual_defaults = translation_service.extract_multilingual_features(
            original_text, source_lang
        )

        client = get_openai_client()
        if not client:
            deadline = _guess_deadline_from_text(english_text) or _guess_deadline_from_text(original_text)
            priority = multilingual_defaults.get("priority", "medium")
            category = AIService._detect_academic_category(english_text) or multilingual_defaults.get("category", "general")

            title_en = _clean_title_phrase(english_text[:60])
            title_en = AIService._post_clean_title_english(title_en)

            return {
                "title": title_en,
                "description": original_text,
                "deadline": deadline,
                "priority": priority,
                "category": category or "general",
                "subtasks": [],
                "ai_generated": False
            }

        # When OpenAI available:
        try:
            now = datetime.now()
            prompt = f"""
            Extract a clean task title that clearly states the action.
            Title must be short and actionable (e.g., "Submit machine learning assignment").
            Do NOT include words like "remind", "add", "please", "high priority", or deadlines in the title.

            Parse into JSON with keys:
            title, description, deadline, priority, category, subtasks.

            Today: {now.strftime('%A, %B %d, %Y')}
            English text: "{english_text}"
            """

            resp = client.chat.completions.create(
                model=AIService._model_name(),
                messages=[{"role": "system", "content": "Respond with VALID JSON only."},
                          {"role": "user", "content": prompt}],
                temperature=0.2,
            )
            result = json.loads(resp.choices[0].message.content)

            title_en = _clean_title_phrase(result.get("title", english_text[:50]))
            title_en = AIService._post_clean_title_english(title_en)

            # Smarter category override
            category = AIService._detect_academic_category(english_text) or \
                       result.get("category") or \
                       multilingual_defaults.get("category") or "general"

            deadline = normalize_deadline(result.get("deadline")) \
                or _guess_deadline_from_text(english_text) \
                or _guess_deadline_from_text(original_text)

            return {
                "title": title_en,
                "description": original_text,
                "deadline": deadline,
                "priority": (result.get("priority") or multilingual_defaults.get("priority") or "medium"),
                "category": category,
                "subtasks": result.get("subtasks", []),
                "ai_generated": True
            }

        except Exception:
            title_en = _clean_title_phrase(english_text[:60])
            title_en = AIService._post_clean_title_english(title_en)
            return {
                "title": title_en,
                "description": original_text,
                "deadline": _guess_deadline_from_text(english_text),
                "priority": multilingual_defaults.get("priority", "medium"),
                "category": AIService._detect_academic_category(english_text)
                            or multilingual_defaults.get("category")
                            or "general",
                "subtasks": [],
                "ai_generated": False
            }

    @staticmethod
    def prioritize_tasks(tasks: List[Dict]) -> List[Dict]:
        return sorted(tasks, key=lambda t: ["low", "medium", "high", "urgent"].index(t.get("priority", "medium")))

    @staticmethod
    def generate_summary(tasks: List[Dict], period: str = "daily") -> str:
        completed = [t for t in tasks if t.get("status") == "completed"]
        pending = [t for t in tasks if t.get("status") in ("pending", "in_progress")]
        return f"Completed {len(completed)} tasks. {len(pending)} still pending."


