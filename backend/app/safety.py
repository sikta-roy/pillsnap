"""Safety rules. Every user-facing response passes through here.

1. A disclaimer is attached to every result (English + Hindi).
2. Below the confidence threshold, or with no readable imprint, we never give a
   single answer: we show the top matches and ask the user to confirm.
3. No doses, ever: generated text is filtered for dosing instructions, and dose
   questions get a fixed referral answer.
"""
from __future__ import annotations

import re

from app.config import CONFIDENCE_THRESHOLD, NO_IMPRINT_CONFIDENCE_CAP

DISCLAIMER = {
    "en": "This is for information only. Do not take a pill based only on this app. Ask a pharmacist or doctor.",
    "hi": "यह जानकारी केवल सूचना के लिए है। केवल इस ऐप के आधार पर कोई गोली न लें। फार्मासिस्ट या डॉक्टर से पूछें।",
}

NO_DOSE_MESSAGE = {
    "en": "PillSnap never gives doses. How much and how often to take a medicine depends on your age, weight, health and other medicines. Please ask your doctor or pharmacist, or read the leaflet in the pack.",
    "hi": "PillSnap कभी भी खुराक नहीं बताता। दवा कितनी और कितनी बार लेनी है, यह आपकी उम्र, वज़न, सेहत और दूसरी दवाओं पर निर्भर करता है। कृपया अपने डॉक्टर या फार्मासिस्ट से पूछें, या पैक में दिया पर्चा पढ़ें।",
}

LOW_CONFIDENCE_MESSAGE = {
    "en": "We are not sure enough to name this pill. Check the top matches below, type the letters or numbers stamped on the pill, or scan the strip or box.",
    "hi": "हम इस गोली का नाम बताने के लिए पर्याप्त रूप से निश्चित नहीं हैं। नीचे दिए संभावित मिलान देखें, गोली पर छपे अक्षर या अंक टाइप करें, या पत्ता/डिब्बा स्कैन करें।",
}

_UNIT = r"(?:mg|mcg|µg|g|ml|mL|milligram|microgram|tablet|tablets|tab|tabs|capsule|capsules|cap|caps|pill|pills|puff|drops?|units?|iu)"
DOSE_PATTERNS = [
    re.compile(rf"\b(take|takes|taking|use|give|swallow|chew|dose|dosage|dosing|max(imum)?)\b[^.]*\b\d+(\.\d+)?\s*(-|to|–)?\s*\d*\s*{_UNIT}\b", re.I),
    re.compile(r"\b(once|twice|thrice|\d+\s*times)\s+(a|per|each)\s+(day|daily|week|night)\b", re.I),
    re.compile(r"\bevery\s+\d+\s*(-|to|–)?\s*\d*\s*hours?\b", re.I),
    re.compile(rf"\b\d+(\.\d+)?\s*{_UNIT}\s*(a|per|/|each)\s*(day|dose|kg|hour|night)\b", re.I),
    re.compile(r"\b(recommended|usual|starting|maximum|max)\s+(daily\s+)?(dose|dosage|amount)\b", re.I),
    re.compile(r"खुराक\s*[:：]?\s*\d", re.I),
]
DOSE_QUESTION = re.compile(r"\b(dose|dosage|how (much|many)|how often|mg should|times a day|per day|maximum|overdose limit)\b|खुराक|कितनी गोली|कितनी बार", re.I)


def contains_dose(text: str) -> bool:
    return any(p.search(text or "") for p in DOSE_PATTERNS)


def strip_doses(text: str) -> str:
    """Drop any sentence that looks like a dosing instruction."""
    if not text:
        return text
    sentences = re.split(r"(?<=[.!?।])\s+", text)
    kept = [s for s in sentences if not contains_dose(s)]
    return " ".join(kept).strip()


def is_dose_question(q: str) -> bool:
    return bool(DOSE_QUESTION.search(q or ""))


def decide(matches: list[dict], imprint_read: bool, imprint_match: float | None) -> tuple[str, list[dict]]:
    """Apply the confidence rules. Returns (status, matches with displayed confidence).

    status: "confident" | "needs_confirmation" | "no_match"
    """
    if not matches:
        return "no_match", []
    out = [dict(m) for m in matches]
    for m in out:  # never display certainty: a photo can always be wrong
        m["confidence"] = min(m["confidence"], 0.99)
    if not imprint_read or (imprint_match is not None and imprint_match < 0.8):
        # Without an imprint that agrees with the top match, colour + shape alone are not
        # enough to tell many white round tablets apart.
        for m in out:
            m["confidence"] = min(m["confidence"], NO_IMPRINT_CONFIDENCE_CAP)
    status = "confident" if out[0]["confidence"] >= CONFIDENCE_THRESHOLD else "needs_confirmation"
    return status, out
