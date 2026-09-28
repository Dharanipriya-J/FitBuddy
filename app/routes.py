"""All route handlers: HTML pages (Jinja2) and JSON API endpoints."""
import os

from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pydantic import ValidationError

from app.database import (delete_user, get_all_plans, get_all_users, get_current_plan,
                          get_original_plan, get_user, save_plan, save_user, update_plan)
from app.gemini_flash_generator import generate_nutrition_tip_with_flash
from app.gemini_generator import GeminiError, generate_workout_gemini
from app.schemas import FeedbackRequest, UserInput, WorkoutRequest
from app.updated_plan import update_workout_plan

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_DIR = os.path.join(BASE_DIR, "templates")
templates = Jinja2Templates(directory=TEMPLATE_DIR)

router = APIRouter()


def _first_error(e: ValidationError) -> str:
    err = e.errors()[0]
    field = ".".join(str(p) for p in err["loc"]) or "input"
    return f"Please check '{field}': {err['msg']}"


def _index(request: Request, error: str = None, values: dict = None, status: int = 200):
    return templates.TemplateResponse(request, "index.html",
                                      {"error": error, "values": values or {}}, status_code=status)


def _result(request: Request, user, plan: str, tip: str, message: str = None,
            error: str = None, updated: bool = False, original_plan: str = None):
    return templates.TemplateResponse(request, "result.html", {
        "username": user.name, "user_id": user.id, "age": user.age, "weight": user.weight,
        "goal": user.goal, "intensity": user.intensity,
        "workout_plan": plan, "nutrition_tip": tip,
        "message": message, "error": error, "updated": updated, "original_plan": original_plan,
    })


# ---------------------------------------------------------------- web pages
@router.get("/", response_class=HTMLResponse)
def home(request: Request):
    return _index(request)


@router.post("/generate-workout", response_class=HTMLResponse)
def generate_workout(request: Request,
                     username: str = Form(...), user_id: str = Form(...), age: str = Form(...),
                     weight: str = Form(...), goal: str = Form(...), intensity: str = Form(...)):
    values = {"username": username, "user_id": user_id, "age": age,
              "weight": weight, "goal": goal, "intensity": intensity}
    try:
        data = UserInput(username=username.strip(), user_id=user_id, age=age,
                         weight=weight, goal=goal.strip(), intensity=intensity)
    except ValidationError as e:
        return _index(request, _first_error(e), values, 400)

    try:
        plan = generate_workout_gemini({"goal": data.goal, "intensity": data.intensity,
                                        "age": data.age, "weight": data.weight})
    except GeminiError as e:
        return _index(request, str(e), values, 502)

    tip = generate_nutrition_tip_with_flash(data.goal)
    save_user(data.user_id, data.username, data.age, data.weight, data.goal, data.intensity)
    save_plan(data.user_id, plan)
    return _result(request, get_user(data.user_id), plan, tip)


@router.post("/submit-feedback", response_class=HTMLResponse)
def submit_feedback(request: Request, user_id: str = Form(...), feedback: str = Form(...)):
    try:
        uid = int(user_id)
        fb = FeedbackRequest(feedback=feedback.strip())
    except (ValueError, ValidationError):
        return _index(request, "Enter your numeric User ID and at least a few words of feedback.", status=400)

    user, current = get_user(uid), get_current_plan(uid)
    if not user or not current:
        return _index(request, f"No plan found for User ID {uid}. Generate a plan first.", status=404)

    original = get_original_plan(uid)
    try:
        revised = update_workout_plan(current, fb.feedback)
    except GeminiError as e:
        return _result(request, user, current, generate_nutrition_tip_with_flash(user.goal), error=str(e))

    update_plan(uid, revised)
    tip = generate_nutrition_tip_with_flash(user.goal)
    return _result(request, user, revised, tip, message="Your plan has been updated based on your feedback!",
                   updated=True, original_plan=original)


@router.get("/view-all-users", response_class=HTMLResponse)
def view_all_users(request: Request):
    plans = {p.user_id: p for p in get_all_plans()}
    rows = []
    for u in get_all_users():
        p = plans.get(u.id)
        rows.append({
            "id": u.id, "name": u.name, "age": u.age, "weight": u.weight,
            "goal": u.goal, "intensity": u.intensity,
            "original_plan": p.original_plan if p else "N/A",
            "updated_plan": p.updated_plan if p and p.updated_plan else "Not updated",
        })
    return templates.TemplateResponse(request, "all_users.html", {"users": rows})


@router.post("/delete-user/{user_id}")
def remove_user(user_id: int):
    delete_user(user_id)
    return RedirectResponse("/view-all-users", status_code=303)


# ------------------------------------------------------------------ JSON API
@router.post("/generate-workout/gemini")
def generate_gemini_workout(request: WorkoutRequest):
    try:
        result = generate_workout_gemini({"goal": request.goal, "intensity": request.intensity})
        return {"model": "gemini", "workout_plan": result}
    except GeminiError as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.get("/nutrition-tip")
def get_flash_tip(goal: str):
    return {"goal": goal, "nutrition_tip": generate_nutrition_tip_with_flash(goal)}


@router.post("/generate-plan")
def generate_plan(user_data: UserInput):
    try:
        plan = generate_workout_gemini({"goal": user_data.goal, "intensity": user_data.intensity,
                                        "age": user_data.age, "weight": user_data.weight})
    except GeminiError as e:
        raise HTTPException(status_code=502, detail=str(e))
    save_user(user_data.user_id, user_data.username, user_data.age,
              user_data.weight, user_data.goal, user_data.intensity)
    save_plan(user_data.user_id, plan)
    return {"message": "Workout plan generated and saved successfully!", "workout_plan": plan}


@router.post("/update-plan/{user_id}")
def update_user_plan(user_id: int, data: FeedbackRequest):
    current = get_current_plan(user_id)
    if not current:
        raise HTTPException(status_code=404, detail="Original plan not found for this user.")
    try:
        updated = update_workout_plan(current, data.feedback)
    except GeminiError as e:
        raise HTTPException(status_code=502, detail=str(e))
    update_plan(user_id, updated)
    return {"updated_plan": updated}
