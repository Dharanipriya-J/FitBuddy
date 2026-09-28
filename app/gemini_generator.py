"""Gemini client + workout plan generator.

Uses the current `google-genai` SDK (the old `google-generativeai` package is
deprecated) and current stable models. Gemini 1.5 has been shut down, so the
model names live in .env and there is an automatic fallback chain: if a model
is retired or unavailable, the next one is tried, and finally the API's own
model list is searched. This keeps the app working as Google rotates models.
"""
import logging
import os
import re
from pathlib import Path

from dotenv import load_dotenv
from google import genai

ROOT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(ROOT_DIR / ".env")

log = logging.getLogger("fitbuddy.gemini")

DEFAULT_WORKOUT_MODEL = "gemini-3.6-flash"
DEFAULT_TIP_MODEL = "gemini-3.5-flash-lite"
FALLBACK_MODELS = [
    "gemini-3.6-flash",
    "gemini-3.5-flash",
    "gemini-3.5-flash-lite",
    "gemini-flash-latest",
    "gemini-2.5-flash",
]


class GeminiError(Exception):
    """Raised when no Gemini model could produce a response."""


_client = None
_working_model = {}  # role -> model that last succeeded


def get_client():
    global _client
    if _client is None:
        key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
        if not key or key.startswith("your_"):
            raise GeminiError("No Gemini API key found. Add GOOGLE_API_KEY to the .env file and restart the server.")
        _client = genai.Client(api_key=key)
    return _client


def _discover_models(client):
    """Ask the API which text models this key can use (last-resort fallback)."""
    found = []
    try:
        for m in client.models.list():
            name = (m.name or "").replace("models/", "")
            actions = getattr(m, "supported_actions", None) or []
            if (name.startswith("gemini-") and "flash" in name and "generateContent" in actions
                    and not any(x in name for x in ("image", "tts", "live", "audio", "embedding", "robotics", "preview"))):
                found.append(name)
    except Exception as e:  # noqa: BLE001
        log.warning("Could not list models: %s", e)
    return sorted(found, reverse=True)


def _is_auth_error(msg: str) -> bool:
    m = msg.lower()
    return any(s in m for s in ("api key not valid", "api_key_invalid", "permission_denied", "unauthenticated"))


def generate_text(prompt: str, role: str, preferred: str) -> str:
    client = get_client()
    candidates = []
    for m in [_working_model.get(role), preferred, *FALLBACK_MODELS]:
        if m and m not in candidates:
            candidates.append(m)

    errors = []

    def attempt(model):
        resp = client.models.generate_content(model=model, contents=prompt)
        text = (resp.text or "").strip()
        if not text:
            raise ValueError("empty response")
        _working_model[role] = model
        return text

    for model in candidates:
        try:
            return attempt(model)
        except Exception as e:  # noqa: BLE001
            errors.append(f"{model}: {e}")
            log.warning("Gemini model %s failed: %s", model, e)
            if _is_auth_error(str(e)):
                raise GeminiError("Your Gemini API key was rejected. Check GOOGLE_API_KEY in .env.") from e

    for model in _discover_models(client):
        if model in candidates:
            continue
        try:
            return attempt(model)
        except Exception as e:  # noqa: BLE001
            errors.append(f"{model}: {e}")

    raise GeminiError("Gemini could not generate a response right now. Last error: " + errors[-1][:300])


def clean_text(text: str) -> str:
    """Strip markdown symbols so the plan reads cleanly inside a <pre> block."""
    text = text.replace("**", "").replace("__", "")
    text = re.sub(r"^\s*#{1,6}\s*", "", text, flags=re.M)
    text = re.sub(r"^(\s*)[\*\-]\s+", r"\1• ", text, flags=re.M)
    return text.strip()


def generate_workout_gemini(user_input: dict) -> str:
    """Generate a 7-day workout plan. user_input needs goal + intensity; age/weight are optional."""
    extra = ""
    if user_input.get("age"):
        extra += f"\nAge: {user_input['age']}"
    if user_input.get("weight"):
        extra += f"\nWeight: {user_input['weight']} kg"

    prompt = f"""You are a professional fitness trainer.

Create a personalized, structured 7-day workout plan.
Fitness goal: "{user_input['goal']}"
Preferred intensity: {user_input['intensity']}{extra}

Each day must include:
- Warm-up (5-10 mins)
- Main Workout (targeted exercises with sets and reps)
- Cooldown or recovery tip

Include rest or active-recovery days where appropriate for the intensity.

Format exactly like this, in plain text with no markdown symbols (no asterisks, no # headings):
Day 1: <focus>
Warm-up: ...
Main Workout:
- Exercise: sets x reps
Cooldown: ...
(Repeat for Day 2 to Day 7)

Finish with a short "Notes" section (2-3 lines) on form, progression and consulting a doctor before starting."""

    model = os.getenv("WORKOUT_MODEL", DEFAULT_WORKOUT_MODEL)
    return clean_text(generate_text(prompt, "workout", model))
