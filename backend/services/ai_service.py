"""
AI Service for OpenAI API integration.
Improved title cleaning (remove dates/time words from title)
and smarter inline subtask extraction.
Works with or without OpenAI configured.
"""

from __future__ import annotations

import os
import json
import re
from datetime import datetime
from typing import Dict, List, Optional

from dateutil import parser as date_parser
from .translation_service import translation_service


# -----------------------------
# Helpers
# -----------------------------

_MONTHS = (
    "january|february|march|april|may|june|july|august|september|october|november|december|"
    "jan|feb|mar|apr|jun|jul|aug|sep|sept|oct|nov|dec"
)

_TIME_WORDS = r"\b(?:am|pm|morning|afternoon|evening|tonight|noon|midnight|at\s+\d{1,2}(:\d{2})?)\b"
_RELATIVE_DAY_WORDS = r"\b(?:today|tomorrow|tonight|yesterday|next\s+\w+|this\s+\w+|coming\s+\w+)\b"

# Common verbs used for inline lists
_INLINE_VERBS = r"(buy|invite|book|call|email|draft|prepare|arrange|order|purchase|schedule|send|create|reserve|confirm|pay|register|plan|finish|review|submit|read|watch|practice|study)"

def _strip_ordinals(text: str) -> str:
    return re.sub(r"(\d+)(st|nd|rd|th)\b", r"\1", text, flags=re.I)


def _clean_title_phrase(title: str) -> str:
    """Remove polite prefixes and trim punctuation."""
    if not title:
        return ""
    low = title.lower().strip()
    prefixes = [
        "add a reminder to ",
        "remind me to ",
        "set a reminder to ",
        "please ",
        "i need to ",
        "i should ",
        "have to ",
        "don't forget to ",
    ]
    cut = 0
    for p in prefixes:
        if low.startswith(p):
            cut = max(cut, len(p))
    cleaned = title[cut:].strip(" .,-\n\t")
    return cleaned


def _post_clean_title_english(title: str) -> str:
    """Trim trailing priority/deadline hints and reduce length."""
    if not title:
        return ""
    low = title.lower()
    stop_words = [
        "by ", "before ", "due ", "deadline", "at ", "on ", "in ", "this ",
        "priority", "urgent", "high priority", "low priority", "medium priority"
    ]
    cut = len(title)
    for w in stop_words:
        idx = low.find(w)
        if idx != -1:
            cut = min(cut, idx)
    # keep first clause if still long
    candidate = title[:cut].split('.')[0].strip()
    # enforce shortness (6-8 words)
    parts = candidate.split()
    if len(parts) > 8:
        candidate = " ".join(parts[:8])
    return candidate.strip(" ,.-")


_DATE_REGEXES = [
    # "on 20 December", "20 Dec 2025", "20/12/2025", "2025-12-20"
    rf"\b(on\s+)?\d{{1,2}}(?:st|nd|rd|th)?\s+(of\s+)?(?:{_MONTHS})\b",
    rf"\b(?:{_MONTHS})\s+\d{{1,2}}(?:st|nd|rd|th)?(?:,\s*\d{{4}})?\b",
    r"\b\d{1,2}[/-]\d{1,2}(?:[/-]\d{2,4})?\b",
    r"\b\d{4}-\d{2}-\d{2}\b",
    _TIME_WORDS,
    _RELATIVE_DAY_WORDS,
    r"\b(?:on\s+the\s+\d{1,2}(?:st|nd|rd|th)?)\b",
    r"\b(?:next\s+(?:week|month|year))\b",
]


def remove_date_phrases(text: str) -> str:
    """Remove likely date/time phrases from text to make title date-free."""
    if not text:
        return ""
    s = _strip_ordinals(text)
    # remove bracketed dates
    s = re.sub(r"\[.*?\]|\(.*?\)", " ", s)
    # remove common date patterns
    for rx in _DATE_REGEXES:
        s = re.sub(rx, " ", s, flags=re.I)
    # Also remove leftover phrases like 'on', 'at' that may remain
    s = re.sub(r"\b(on|at|by|before|due|around|about|this|next|coming)\b", " ", s, flags=re.I)
    # collapse whitespace and punctuation
    s = re.sub(r"\s{2,}", " ", s)
    return s.strip(" ,.-\n\t")


def extract_inline_subtasks(text: str) -> List[str]:
    """
    Extract subtasks from inline lists like:
      "Buy cake, decorations, and invite guests"
    -> ["Buy cake", "Buy decorations", "Invite guests"]
    Heuristic-driven; returns [] if nothing useful found.
    """
    if not text:
        return []

    s = text.strip()
    # Try pattern: Verb followed by list of nouns "Buy A, B and C"
    m = re.search(rf"\b{_INLINE_VERBS}\b\s+(.+)$", s, flags=re.I)
    subtasks: List[str] = []
    if m:
        verb = m.group(0).split()[0].lower()
        rest = m.group(1)
        # split by commas and ' and ' (preserve items)
        parts = re.split(r",|\band\b", rest, flags=re.I)
        for p in parts:
            item = p.strip(" .,-\n\t")
            if not item:
                continue
            # If item already starts with a verb, keep it; else prepend the main verb
            if re.match(rf"^{_INLINE_VERBS}\b", item, flags=re.I):
                subtasks.append(item.capitalize())
            else:
                subtasks.append(f"{verb.capitalize()} {item}")
        # remove duplicates and short nonsense
        seen = set()
        cleaned = []
        for st in subtasks:
            st2 = re.sub(r"\s{2,}", " ", st).strip()
            if len(st2) > 2 and st2.lower() not in seen:
                cleaned.append(st2)
                seen.add(st2.lower())
        return cleaned[:8]

    # Fallback: look for verb-noun sequences across the text
    verbs_found = re.findall(rf"\b{_INLINE_VERBS}\b\s+[^\.,;]+", s, flags=re.I)
    for vf in verbs_found:
        cleaned = vf.strip(" .,-\n\t")
        cleaned = cleaned[0].upper() + cleaned[1:]
        subtasks.append(cleaned)
    # If we have multiple comma-separated clauses without explicit verbs,
    # treat leading verb and apply to subsequent nouns:
    if not subtasks:
        # try to find "Buy cake, decorations and invite guests" split by comma,
        # then attempt to prepend verb of first clause to following standalone nouns when sensible
        parts = [p.strip() for p in re.split(r",|\band\b", s) if p.strip()]
        if len(parts) > 1:
            # inspect first part for verb
            first = parts[0]
            m2 = re.match(rf"^({_INLINE_VERBS})\b\s*(.+)$", first, flags=re.I)
            if m2:
                v = m2.group(1).lower()
                noun0 = m2.group(2).strip()
                subtasks.append(f"{v.capitalize()} {noun0}")
                for extra in parts[1:]:
                    # if extra starts with verb, use it; else use v
                    if re.match(rf"^{_INLINE_VERBS}\b", extra, flags=re.I):
                        subtasks.append(extra.capitalize())
                    else:
                        subtasks.append(f"{v.capitalize()} {extra}")
                seen = set()
                cleaned = []
                for st in subtasks:
                    st2 = re.sub(r"\s{2,}", " ", st).strip()
                    if len(st2) > 2 and st2.lower() not in seen:
                        cleaned.append(st2)
                        seen.add(st2.lower())
                return cleaned[:8]

    return []


def _strip_quotes(s: str) -> str:
    return s.strip().strip('\'"')


# -----------------------------
# Main AIService
# -----------------------------
class AIService:
    @staticmethod
    def _model_name() -> str:
        return os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    @staticmethod
    def _detect_academic_category(text: str) -> Optional[str]:
        academic_keywords = ["assignment", "homework", "project", "lab report", "exam", "college", "university"]
        text_low = (text or "").lower()
        return "education" if any(k in text_low for k in academic_keywords) else None

    @staticmethod
    def _normalize_priority(value: Optional[str]) -> str:
        v = (value or "").strip().lower()
        if v in {"urgent", "high", "medium", "low"}:
            return v
        return "medium"

    @staticmethod
    def _normalize_category(value: Optional[str]) -> str:
        return (value or "general").strip().lower()

    @staticmethod
    def parse_natural_language_task(user_input: str) -> Dict:
        """
        Returns:
          - title (English, concise, date-free), title_en,
          - description (original text),
          - deadline (ISO minutes or None),
          - priority, category, subtasks (list),
          - ai_generated, detected_language
        """
        translation = translation_service.translate_to_english(user_input or "")
        original_text = translation.get("original_text") or user_input or ""
        english_text = translation.get("translated_text") or original_text
        src_lang = translation.get("source_language", "unknown")

        multilingual_defaults = {}
        try:
            multilingual_defaults = translation_service.extract_multilingual_features(original_text, src_lang)
        except Exception:
            multilingual_defaults = {}

        client = None
        api_key = os.getenv("OPENAI_API_KEY")
        if api_key:
            try:
                from openai import OpenAI
                os.environ["OPENAI_API_KEY"] = api_key
                client = OpenAI()
            except Exception:
                client = None

        # Heuristic-only path (no OpenAI)
        if not client:
            # Title: remove dates, polite prefixes, and post-clean
            title_candidate = remove_date_phrases(english_text)
            title_candidate = _clean_title_phrase(title_candidate[:140])
            title_en = _post_clean_title_english(title_candidate) or "Untitled task"

            # Extract inline subtasks if present
            inline_subs = extract_inline_subtasks(english_text)
            # If inline_subs empty, try to find imperative sentences separated by semicolons/periods/newlines
            if not inline_subs:
                sentences = re.split(r"[;\.\n]", english_text)
                # select short sentences which start with a verb
                for s in sentences:
                    s2 = s.strip()
                    if re.match(rf"^{_INLINE_VERBS}\b", s2, flags=re.I):
                        inline_subs.append(s2.capitalize())

            # deadline detection
            deadline = None
            try:
                guessed = None
                try:
                    guessed = date_parser.parse(_strip_ordinals(english_text), fuzzy=True, dayfirst=True)
                except Exception:
                    guessed = None
                if guessed:
                    # if time not specified default to 23:59
                    if guessed.hour == 0 and guessed.minute == 0 and not re.search(r"\d{1,2}:\d{2}|\b(am|pm)\b", english_text, re.I):
                        guessed = guessed.replace(hour=23, minute=59)
                    if guessed.tzinfo:
                        guessed = guessed.astimezone(tz=None).replace(tzinfo=None)
                    deadline = guessed.isoformat(timespec="minutes")
            except Exception:
                deadline = None

            return {
                "title": title_en,
                "title_en": title_en,
                "description": original_text,
                "deadline": deadline,
                "priority": AIService._normalize_priority(multilingual_defaults.get("priority") if isinstance(multilingual_defaults, dict) else None),
                "category": AIService._normalize_category(AIService._detect_academic_category(english_text) or (multilingual_defaults.get("category") if isinstance(multilingual_defaults, dict) else None)),
                "subtasks": inline_subs[:8],
                "ai_generated": False,
                "detected_language": src_lang,
            }

        # OpenAI-enabled path
        try:
            now = datetime.now()
            prompt = (
                "Output VALID JSON only with keys: title, description, deadline, priority, category, subtasks.\n"
                "- Title: short actionable English phrase (no dates/times inside the title).\n"
                "- Deadline: any human date/time or empty string.\n"
                "- Priority: one of low, medium, high, urgent (default medium)\n"
                "- Subtasks: 3-7 short imperative steps when useful; otherwise [].\n\n"
                f"Today: {now.strftime('%A, %B %d, %Y')}\n"
                f'Input (EN): "{_strip_ordinals(english_text)}"\n'
            )

            resp = client.chat.completions.create(
                model=AIService._model_name(),
                messages=[
                    {"role": "system", "content": "You must respond with VALID JSON only (no commentary, no code fences)."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.2,
            )

            raw = (resp.choices[0].message.content or "").strip()
            # strip fences/prefix
            raw = raw.strip("`")
            if raw.lower().startswith("json"):
                raw = raw[4:].strip()

            parsed = {}
            try:
                parsed = json.loads(raw)
            except Exception:
                m = re.search(r"\{.*\}", raw, flags=re.S)
                parsed = json.loads(m.group(0)) if m else {}

            # Post-process title: always remove dates/time phrases even if the model included them
            model_title = (parsed.get("title") or english_text).strip()
            model_title = remove_date_phrases(model_title)
            model_title = _clean_title_phrase(model_title)
            title_en = _post_clean_title_english(model_title) or "Untitled task"

            # Subtasks: prefer inline list extraction if user wrote inline list; otherwise model subtasks
            inline_subs = extract_inline_subtasks(english_text)
            model_subs = parsed.get("subtasks") or []
            if not isinstance(model_subs, list):
                model_subs = []

            subtasks = inline_subs if inline_subs else [s.strip() for s in model_subs if isinstance(s, str) and s.strip()]

            # If still empty and description contains comma-separated actions starting with verbs, try extract
            if not subtasks:
                subtasks = extract_inline_subtasks(parsed.get("description") or english_text) or []

            # Deadline normalization using dateutil
            deadline_raw = parsed.get("deadline") or None
            deadline = None
            if deadline_raw:
                try:
                    dt = date_parser.parse(_strip_ordinals(str(deadline_raw)), fuzzy=True, dayfirst=True)
                    if dt.hour == 0 and dt.minute == 0 and not re.search(r"\d{1,2}:\d{2}|\b(am|pm)\b", str(deadline_raw), re.I):
                        dt = dt.replace(hour=23, minute=59)
                    if dt.tzinfo:
                        dt = dt.astimezone(tz=None).replace(tzinfo=None)
                    deadline = dt.isoformat(timespec="minutes")
                except Exception:
                    deadline = None
            else:
                # try guess from text
                try:
                    guessed = date_parser.parse(_strip_ordinals(english_text), fuzzy=True, dayfirst=True)
                    if guessed:
                        if guessed.hour == 0 and guessed.minute == 0 and not re.search(r"\d{1,2}:\d{2}|\b(am|pm)\b", english_text, re.I):
                            guessed = guessed.replace(hour=23, minute=59)
                        if guessed.tzinfo:
                            guessed = guessed.astimezone(tz=None).replace(tzinfo=None)
                        deadline = guessed.isoformat(timespec="minutes")
                except Exception:
                    deadline = None

            category = parsed.get("category") or AIService._detect_academic_category(english_text) or "general"
            priority = AIService._normalize_priority(parsed.get("priority"))

            return {
                "title": title_en,
                "title_en": title_en,
                "description": original_text,
                "deadline": deadline,
                "priority": priority,
                "category": AIService._normalize_category(category),
                "subtasks": subtasks[:8],
                "ai_generated": True,
                "detected_language": src_lang,
            }

        except Exception as e:
            print(f"[AIService] OpenAI parse error, falling back: {e}")
            # graceful fallback (heuristic-only)
            title_candidate = remove_date_phrases(english_text)
            title_candidate = _clean_title_phrase(title_candidate[:120])
            title_en = _post_clean_title_english(title_candidate) or "Untitled task"
            inline_subs = extract_inline_subtasks(english_text)
            return {
                "title": title_en,
                "title_en": title_en,
                "description": original_text,
                "deadline": None,
                "priority": AIService._normalize_priority(None),
                "category": "general",
                "subtasks": inline_subs[:8],
                "ai_generated": False,
                "detected_language": src_lang,
            }

    @staticmethod
    def suggest_subtasks(title: str, description: str = "") -> Dict:
        """
        Suggest subtasks for a given title + optional description.
        Strategy:
          1. Translate title to English (using translation_service).
          2. Use simple rule-based fallbacks for common categories.
          3. If OpenAI is configured, ask the model to return JSON with subtasks.
          4. Always return a dict with keys: suggested_subtasks, suggested_category, suggested_priority
        """
        try:
            # Ensure we have an english title to work with
            trans = translation_service.translate_to_english(title or "")
            eng_title = (trans.get("translated_text") or title or "").strip()

            # Quick rule-based fallbacks (very fast and reliable)
            fallback_map = {
                "meeting": (["Create agenda", "Send invites", "Prepare notes", "Conduct meeting", "Share minutes"], "work", "medium"),
                "assignment": (["Understand requirements", "Prepare outline", "Write draft", "Revise draft", "Submit assignment"], "education", "high"),
                "email": (["Draft message", "Proofread", "Add attachments if any", "Send", "Follow up"], "work", "medium"),
                "report": (["Collect data", "Analyze data", "Write draft", "Create visuals", "Review & submit"], "work", "high"),
                "party": (["Create guest list", "Book venue", "Buy cake & decorations", "Send invitations", "Arrange food/music"], "personal", "medium"),
                "birthday": (["Create guest list", "Buy cake & decorations", "Send invitations", "Arrange venue/food", "Confirm RSVPs"], "personal", "medium"),
                "study": (["Decide topics", "Create study plan", "Gather resources", "Group discussion", "Revise & test"], "education", "high"),
            }

            low_title = eng_title.lower()
            for key, (subs, cat, pr) in fallback_map.items():
                if key in low_title:
                    return {
                        "suggested_subtasks": subs,
                        "suggested_category": cat,
                        "suggested_priority": pr,
                    }

            # If OpenAI not configured -> generic fallback
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                # If inline actionable items exist in description/title, try to extract them
                inline = extract_inline_subtasks(f"{eng_title}. {description}".strip())
                if inline:
                    return {
                        "suggested_subtasks": inline,
                        "suggested_category": "general",
                        "suggested_priority": "medium",
                    }
                return {
                    "suggested_subtasks": ["Plan task", "Execute", "Review"],
                    "suggested_category": "general",
                    "suggested_priority": "medium",
                }

            # If OpenAI configured, attempt to generate 3-6 subtasks via model
            try:
                from openai import OpenAI
                os.environ["OPENAI_API_KEY"] = api_key
                client = OpenAI()

                prompt = (
                    "Return ONLY valid JSON with keys: subtasks (array), category, priority.\n"
                    "Subtasks must be 3-6 short imperative English steps.\n"
                    f'Title: "{eng_title}"\n'
                    f'Description: "{(description or "").strip()}"\n'
                )

                resp = client.chat.completions.create(
                    model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
                    messages=[
                        {"role": "system", "content": "Valid JSON only. No extra commentary."},
                        {"role": "user", "content": prompt},
                    ],
                    temperature=0.3,
                )

                raw = (resp.choices[0].message.content or "").strip()
                # strip code fences/prefix text if present
                raw = raw.strip("`")
                if raw.lower().startswith("json"):
                    raw = raw[4:].strip()

                parsed = {}
                try:
                    parsed = json.loads(raw)
                except Exception:
                    # extract JSON object if model added commentary
                    m = re.search(r"\{.*\}", raw, flags=re.S)
                    parsed = json.loads(m.group(0)) if m else {}

                subs_in = parsed.get("subtasks", []) or []
                subs = [s.strip() for s in subs_in if isinstance(s, str) and s.strip()]
                if not subs:
                    # model failed to produce clean list -> fallback
                    inline = extract_inline_subtasks(f"{eng_title}. {description}".strip())
                    return {
                        "suggested_subtasks": inline or ["Plan task", "Execute", "Review"],
                        "suggested_category": (parsed.get("category") or "general"),
                        "suggested_priority": (parsed.get("priority") or "medium"),
                    }

                return {
                    "suggested_subtasks": subs[:8],
                    "suggested_category": (parsed.get("category") or "general"),
                    "suggested_priority": (parsed.get("priority") or "medium"),
                }

            except Exception as openai_err:
                # OpenAI exception -> fallback sensible defaults
                print(f"[AIService][suggest_subtasks] OpenAI error: {openai_err}")
                inline = extract_inline_subtasks(f"{eng_title}. {description}".strip())
                return {
                    "suggested_subtasks": inline or ["Plan task", "Execute", "Review"],
                    "suggested_category": "general",
                    "suggested_priority": "medium",
                }

        except Exception as e:
            # Catch-all fallback
            print(f"[AIService][suggest_subtasks] Fallback due to: {e}")
            return {
                "suggested_subtasks": ["Plan task", "Execute", "Review"],
                "suggested_category": "general",
                "suggested_priority": "medium",
            }

    @staticmethod
    def prioritize_tasks(tasks: List[Dict]) -> List[Dict]:
        order = {"urgent": 3, "high": 2, "medium": 1, "low": 0}
        return sorted(tasks, key=lambda t: order.get((t or {}).get("priority", "medium").lower(), 1), reverse=True)

    @staticmethod
    def generate_summary(tasks: List[Dict], period: str = "daily") -> str:
        completed = sum(1 for t in tasks if (t or {}).get("status") == "completed")
        active = sum(1 for t in tasks if (t or {}).get("status") in {"pending", "in_progress"})
        urgent = sum(1 for t in tasks if (t or {}).get("priority") == "urgent")
        high = sum(1 for t in tasks if (t or {}).get("priority") == "high")
        return f"{period.capitalize()}: {completed} completed, {active} active ({urgent} urgent, {high} high)."
