"""Revise an existing workout plan using the user's feedback."""
import os

from app.gemini_generator import DEFAULT_WORKOUT_MODEL, clean_text, generate_text


def update_workout_plan(original_plan: str, user_feedback: str) -> str:
    prompt = f"""You are a professional fitness trainer assistant.

Here is the current 7-day workout plan:
{original_plan}

User feedback:
"{user_feedback}"

Based on the feedback, revise the relevant parts of the workout plan. Keep the same format
(Day 1 to Day 7, with Warm-up, Main Workout, Cooldown) and leave the rest of the plan unchanged
where no change is needed. Return the complete updated plan in plain text with no markdown symbols
(no asterisks, no # headings)."""
    model = os.getenv("WORKOUT_MODEL", DEFAULT_WORKOUT_MODEL)
    return clean_text(generate_text(prompt, "workout", model))
