"""Nutrition helpers. Static tips are used only if the Gemini call fails,
so the result page still renders something useful."""

_TIPS = {
    "loss": "Build meals around protein and vegetables, and drink a glass of water before eating. "
            "You'll feel full sooner and hold on to muscle while losing fat.",
    "gain": "Eat 20-40 g of protein within a couple of hours after training, "
            "with some carbs like rice or oats to help your muscles recover.",
    "general": "Aim for a mix of protein, whole grains, fruit and vegetables at each meal, "
               "drink water through the day, and get 7-9 hours of sleep to recover.",
}


def get_fallback_tip(goal: str) -> str:
    g = (goal or "").lower()
    if any(w in g for w in ("loss", "lose", "fat", "cut", "slim")):
        return _TIPS["loss"]
    if any(w in g for w in ("muscle", "gain", "bulk", "strength")):
        return _TIPS["gain"]
    return _TIPS["general"]
