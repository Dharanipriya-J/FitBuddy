"""Fast, lightweight model for short nutrition / recovery tips."""
import logging
import os

from app.gemini_generator import DEFAULT_TIP_MODEL, GeminiError, clean_text, generate_text
from app.nutrition import get_fallback_tip

log = logging.getLogger("fitbuddy.flash")


def generate_nutrition_tip_with_flash(goal: str) -> str:
    """Generate one nutrition or recovery tip for the user's goal.

    Falls back to a built-in tip if Gemini is unavailable so the page still works.
    """
    prompt = (
        f'Give one clear, helpful nutrition or recovery tip for someone whose fitness goal is "{goal}". '
        "Keep it to 2 sentences, practical, friendly and easy to understand. Plain text only, no markdown."
    )
    model = os.getenv("TIP_MODEL", DEFAULT_TIP_MODEL)
    try:
        return clean_text(generate_text(prompt, "tip", model))
    except GeminiError as e:
        log.warning("Using fallback nutrition tip: %s", e)
        return get_fallback_tip(goal)
