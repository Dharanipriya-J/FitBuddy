"""SQLAlchemy models and DB helpers (SQLite: fitbuddy.db in the project root)."""
from pathlib import Path
from typing import Optional

from sqlalchemy import Column, Float, ForeignKey, Integer, String, Text, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

ROOT_DIR = Path(__file__).resolve().parent.parent
DATABASE_URL = f"sqlite:///{ROOT_DIR / 'fitbuddy.db'}"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
Base = declarative_base()


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    age = Column(Integer)
    weight = Column(Float)
    goal = Column(String)
    intensity = Column(String)
    schedule = Column(Integer, default=7)


class WorkoutPlan(Base):
    __tablename__ = "plans"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    original_plan = Column(Text, nullable=False)
    updated_plan = Column(Text, nullable=True)


def init_db():
    Base.metadata.create_all(bind=engine)


def save_user(user_id: int, name: str, age: int, weight: float, goal: str, intensity: str):
    db = SessionLocal()
    try:
        existing = db.query(User).filter_by(id=user_id).first()
        if existing:
            existing.name, existing.age, existing.weight = name, age, weight
            existing.goal, existing.intensity = goal, intensity
        else:
            db.add(User(id=user_id, name=name, age=age, weight=weight,
                        goal=goal, intensity=intensity, schedule=7))
        db.commit()
    finally:
        db.close()


def save_plan(user_id: int, plan: str):
    """Store a freshly generated plan. Regenerating replaces the old plan and clears any update."""
    db = SessionLocal()
    try:
        existing = db.query(WorkoutPlan).filter_by(user_id=user_id).first()
        if existing:
            existing.original_plan = plan
            existing.updated_plan = None
        else:
            db.add(WorkoutPlan(user_id=user_id, original_plan=plan))
        db.commit()
    finally:
        db.close()


def update_plan(user_id: int, updated_text: str):
    db = SessionLocal()
    try:
        workout = db.query(WorkoutPlan).filter_by(user_id=user_id).first()
        if workout:
            workout.updated_plan = updated_text
            db.commit()
    finally:
        db.close()


def get_original_plan(user_id: int) -> Optional[str]:
    db = SessionLocal()
    try:
        plan = db.query(WorkoutPlan).filter(WorkoutPlan.user_id == user_id).first()
        return plan.original_plan if plan else None
    finally:
        db.close()


def get_current_plan(user_id: int) -> Optional[str]:
    """Latest version of the plan: the updated one if it exists, otherwise the original."""
    db = SessionLocal()
    try:
        plan = db.query(WorkoutPlan).filter(WorkoutPlan.user_id == user_id).first()
        if not plan:
            return None
        return plan.updated_plan or plan.original_plan
    finally:
        db.close()


def get_user(user_id: int) -> Optional[User]:
    db = SessionLocal()
    try:
        return db.query(User).filter(User.id == user_id).first()
    finally:
        db.close()


def get_all_users():
    db = SessionLocal()
    try:
        return db.query(User).order_by(User.id).all()
    finally:
        db.close()


def get_all_plans():
    db = SessionLocal()
    try:
        return db.query(WorkoutPlan).all()
    finally:
        db.close()


def delete_user(user_id: int):
    db = SessionLocal()
    try:
        db.query(WorkoutPlan).filter(WorkoutPlan.user_id == user_id).delete()
        db.query(User).filter(User.id == user_id).delete()
        db.commit()
    finally:
        db.close()
