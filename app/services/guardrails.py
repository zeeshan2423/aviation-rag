"""
Aviation SOP Response Guardrails.
Implements signal-based validation for grounding, uncertainty, and quality.
"""

from typing import Dict, Any, List

# Secondary uncertainty check patterns
BANNED_PATTERNS = [
    "i think",
    "i assume",
    "maybe",
    "possibly",
    "it seems",
    "i am an ai",
    "i don't have enough information",
    "i'm not sure",
    "i believe"
]

def contains_uncertain_language(text: str) -> bool:
    """Checks if the text contains any predefined uncertainty patterns."""
    text_lower = text.lower()
    return any(pattern in text_lower for pattern in BANNED_PATTERNS)

def validate_response(answer: str, confidence: float, sources: List[Any]) -> Dict[str, Any]:
    """
    Executes a suite of fast, rule-based checks on the generated response.
    Returns a status dict with validation flags and optional warnings.
    """
    checks = {
        "has_sources": len(sources) > 0,
        "no_uncertainty": not contains_uncertain_language(answer),
        "sufficient_length": len(answer.split()) >= 10,
        "high_confidence": confidence >= 0.6
    }

    is_valid = True
    warning = None
    reason = None

    # 1. Critical Fail: No Sources
    if not checks["has_sources"]:
        is_valid = False
        reason = "missing_sources"
        warning = "No direct SOP source found for this answer."

    # 2. Safety Warning: Uncertain Language
    elif not checks["no_uncertainty"]:
        warning = "This answer contains uncertain language. Please cross-verify with original SOP."
        reason = "uncertain_language"

    # 3. Quality Warning: Too short
    elif not checks["sufficient_length"]:
        warning = "This answer is unusually brief. Full context may be missing."
        reason = "short_answer"

    # 4. Confidence Warning: Medium Tier (0.3 - 0.6)
    elif not checks["high_confidence"]:
        warning = "Confidence in this grounding is moderate. Verify details."
        reason = "medium_confidence"

    return {
        "is_valid": is_valid,
        "warning": warning,
        "reason": reason,
        "checks": checks
    }
