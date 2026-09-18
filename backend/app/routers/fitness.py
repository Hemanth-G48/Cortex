from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import (
    DietPlan,
    Exercise,
    Expense,
    FitnessGoal,
    MuscleGroup,
    PersonalRecord,
    User,
    Workout,
    WorkoutSplit,
)
from app.schemas.fitness import (
    WorkoutCreate, WorkoutResponse,
    FitnessGoalCreate, FitnessGoalResponse,
    ExerciseCreate, ExerciseResponse,
    MuscleGroupCreate, MuscleGroupResponse,
    WorkoutSplitCreate, WorkoutSplitResponse,
    ExpenseCreate, ExpenseResponse, ExpenseSummary,
    PersonalRecordCreate, PersonalRecordResponse,
    DietPlanCreate, DietPlanResponse,
)
from app.services.fitness_hub import expenses_summary, weight_progress, membership_info, week_actuals

router = APIRouter(prefix="/api", tags=["fitness"])


def _first_user(db: Session) -> Optional[User]:
    return db.query(User).order_by(User.id).first()


# ── Workouts ──
@router.get("/workouts", response_model=List[WorkoutResponse])
def list_workouts(db: Session = Depends(get_db)):
    return db.query(Workout).order_by(Workout.date.desc()).all()


@router.get("/fitness/week-actuals")
def get_week_actuals(
    week_start: Optional[str] = Query(None, description="ISO date (Monday) to start the week."),
    db: Session = Depends(get_db),
):
    """Per-day actuals for the current week (audit defect #84).

    Overlays what was actually trained on each Mon-Sat card — ``Workout`` rows
    plus whether the vault's ``daily-life/YYYY-MM-DD.md`` note mentions a
    workout — on the configured split.
    """
    start = None
    if week_start:
        try:
            start = date.fromisoformat(week_start)
        except ValueError:
            raise HTTPException(400, "week_start must be an ISO date (YYYY-MM-DD)")
    return week_actuals(db, _first_user(db), start)


@router.post("/workouts", response_model=WorkoutResponse)
def create_workout(data: WorkoutCreate, db: Session = Depends(get_db)):
    workout = Workout(**data.model_dump())
    db.add(workout)
    db.commit()
    db.refresh(workout)
    return workout


@router.delete("/workouts/{workout_id}")
def delete_workout(workout_id: int, db: Session = Depends(get_db)):
    workout = db.query(Workout).filter(Workout.id == workout_id).first()
    if not workout:
        raise HTTPException(404, "Workout not found")
    db.delete(workout)
    db.commit()
    return {"ok": True}


# ── Fitness Goals ──
@router.get("/fitness-goals", response_model=List[FitnessGoalResponse])
def list_fitness_goals(db: Session = Depends(get_db)):
    return db.query(FitnessGoal).all()


@router.post("/fitness-goals", response_model=FitnessGoalResponse)
def create_fitness_goal(data: FitnessGoalCreate, db: Session = Depends(get_db)):
    goal = FitnessGoal(**data.model_dump())
    db.add(goal)
    db.commit()
    db.refresh(goal)
    return goal


@router.put("/fitness-goals/{goal_id}", response_model=FitnessGoalResponse)
def update_fitness_goal(goal_id: int, data: FitnessGoalCreate, db: Session = Depends(get_db)):
    goal = db.query(FitnessGoal).filter(FitnessGoal.id == goal_id).first()
    if not goal:
        raise HTTPException(404, "Fitness goal not found")
    for key, val in data.model_dump().items():
        setattr(goal, key, val)
    db.commit()
    db.refresh(goal)
    return goal


@router.delete("/fitness-goals/{goal_id}")
def delete_fitness_goal(goal_id: int, db: Session = Depends(get_db)):
    goal = db.query(FitnessGoal).filter(FitnessGoal.id == goal_id).first()
    if not goal:
        raise HTTPException(404, "Fitness goal not found")
    db.delete(goal)
    db.commit()
    return {"ok": True}


# ── Exercises (Phase 25) ──
@router.get("/exercises", response_model=List[ExerciseResponse])
def list_exercises(
    muscle_group_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
):
    q = db.query(Exercise)
    if muscle_group_id is not None:
        q = q.filter(Exercise.muscle_group_id == muscle_group_id)
    return q.order_by(Exercise.id).all()


@router.post("/exercises", response_model=ExerciseResponse)
def create_exercise(data: ExerciseCreate, db: Session = Depends(get_db)):
    exercise = Exercise(**data.model_dump())
    db.add(exercise)
    db.commit()
    db.refresh(exercise)
    return exercise


@router.put("/exercises/{exercise_id}", response_model=ExerciseResponse)
def update_exercise(exercise_id: int, data: ExerciseCreate, db: Session = Depends(get_db)):
    exercise = db.query(Exercise).filter(Exercise.id == exercise_id).first()
    if not exercise:
        raise HTTPException(404, "Exercise not found")
    for key, val in data.model_dump().items():
        setattr(exercise, key, val)
    db.commit()
    db.refresh(exercise)
    return exercise


@router.delete("/exercises/{exercise_id}")
def delete_exercise(exercise_id: int, db: Session = Depends(get_db)):
    exercise = db.query(Exercise).filter(Exercise.id == exercise_id).first()
    if not exercise:
        raise HTTPException(404, "Exercise not found")
    db.delete(exercise)
    db.commit()
    return {"ok": True}


# ── Muscle Groups (Phases 26-27) ──
@router.get("/muscle-groups", response_model=List[MuscleGroupResponse])
def list_muscle_groups(db: Session = Depends(get_db)):
    return db.query(MuscleGroup).order_by(MuscleGroup.sort_order, MuscleGroup.id).all()


@router.post("/muscle-groups", response_model=MuscleGroupResponse)
def create_muscle_group(data: MuscleGroupCreate, db: Session = Depends(get_db)):
    group = MuscleGroup(**data.model_dump())
    db.add(group)
    db.commit()
    db.refresh(group)
    return group


@router.put("/muscle-groups/{group_id}", response_model=MuscleGroupResponse)
def update_muscle_group(group_id: int, data: MuscleGroupCreate, db: Session = Depends(get_db)):
    group = db.query(MuscleGroup).filter(MuscleGroup.id == group_id).first()
    if not group:
        raise HTTPException(404, "Muscle group not found")
    for key, val in data.model_dump().items():
        setattr(group, key, val)
    db.commit()
    db.refresh(group)
    return group


@router.delete("/muscle-groups/{group_id}")
def delete_muscle_group(group_id: int, db: Session = Depends(get_db)):
    group = db.query(MuscleGroup).filter(MuscleGroup.id == group_id).first()
    if not group:
        raise HTTPException(404, "Muscle group not found")
    db.delete(group)
    db.commit()
    return {"ok": True}


@router.get("/muscle-groups/{group_id}/exercises", response_model=List[ExerciseResponse])
def muscle_group_exercises(group_id: int, db: Session = Depends(get_db)):
    group = db.query(MuscleGroup).filter(MuscleGroup.id == group_id).first()
    if not group:
        raise HTTPException(404, "Muscle group not found")
    return db.query(Exercise).filter(Exercise.muscle_group_id == group_id).all()


# ── Workout Splits (Phase 28) ──
@router.get("/workout-splits", response_model=List[WorkoutSplitResponse])
def list_workout_splits(
    week_number: Optional[int] = Query(None),
    db: Session = Depends(get_db),
):
    q = db.query(WorkoutSplit)
    if week_number is not None:
        q = q.filter(WorkoutSplit.week_number == week_number)
    return q.order_by(WorkoutSplit.week_number, WorkoutSplit.day_of_week).all()


@router.post("/workout-splits", response_model=WorkoutSplitResponse)
def create_workout_split(data: WorkoutSplitCreate, db: Session = Depends(get_db)):
    split = WorkoutSplit(**data.model_dump())
    db.add(split)
    db.commit()
    db.refresh(split)
    return split


@router.put("/workout-splits/{split_id}", response_model=WorkoutSplitResponse)
def update_workout_split(split_id: int, data: WorkoutSplitCreate, db: Session = Depends(get_db)):
    split = db.query(WorkoutSplit).filter(WorkoutSplit.id == split_id).first()
    if not split:
        raise HTTPException(404, "Workout split not found")
    for key, val in data.model_dump().items():
        setattr(split, key, val)
    db.commit()
    db.refresh(split)
    return split


@router.delete("/workout-splits/{split_id}")
def delete_workout_split(split_id: int, db: Session = Depends(get_db)):
    split = db.query(WorkoutSplit).filter(WorkoutSplit.id == split_id).first()
    if not split:
        raise HTTPException(404, "Workout split not found")
    db.delete(split)
    db.commit()
    return {"ok": True}


# ── Expenses (Phase 29) ──
@router.get("/expenses", response_model=List[ExpenseResponse])
def list_expenses(db: Session = Depends(get_db)):
    return db.query(Expense).order_by(Expense.date.desc()).all()


@router.get("/expenses/summary", response_model=ExpenseSummary)
def get_expenses_summary(db: Session = Depends(get_db)):
    return expenses_summary(db, _first_user(db))


@router.post("/expenses", response_model=ExpenseResponse)
def create_expense(data: ExpenseCreate, db: Session = Depends(get_db)):
    expense = Expense(**data.model_dump())
    db.add(expense)
    db.commit()
    db.refresh(expense)
    return expense


@router.delete("/expenses/{expense_id}")
def delete_expense(expense_id: int, db: Session = Depends(get_db)):
    expense = db.query(Expense).filter(Expense.id == expense_id).first()
    if not expense:
        raise HTTPException(404, "Expense not found")
    db.delete(expense)
    db.commit()
    return {"ok": True}


# ── Personal Records (Phase 30) ──
@router.get("/personal-records", response_model=List[PersonalRecordResponse])
def list_personal_records(db: Session = Depends(get_db)):
    return db.query(PersonalRecord).order_by(PersonalRecord.id).all()


@router.post("/personal-records", response_model=PersonalRecordResponse)
def create_personal_record(data: PersonalRecordCreate, db: Session = Depends(get_db)):
    record = PersonalRecord(**data.model_dump())
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


@router.put("/personal-records/{record_id}", response_model=PersonalRecordResponse)
def update_personal_record(record_id: int, data: PersonalRecordCreate, db: Session = Depends(get_db)):
    record = db.query(PersonalRecord).filter(PersonalRecord.id == record_id).first()
    if not record:
        raise HTTPException(404, "Personal record not found")
    for key, val in data.model_dump().items():
        setattr(record, key, val)
    db.commit()
    db.refresh(record)
    return record


@router.delete("/personal-records/{record_id}")
def delete_personal_record(record_id: int, db: Session = Depends(get_db)):
    record = db.query(PersonalRecord).filter(PersonalRecord.id == record_id).first()
    if not record:
        raise HTTPException(404, "Personal record not found")
    db.delete(record)
    db.commit()
    return {"ok": True}


# ── Diet Plans (Phase 31) ──
@router.get("/diet-plans", response_model=List[DietPlanResponse])
def list_diet_plans(db: Session = Depends(get_db)):
    return db.query(DietPlan).order_by(DietPlan.sort_order, DietPlan.id).all()


@router.get("/diet-plans/active", response_model=Optional[DietPlanResponse])
def get_active_diet_plan(db: Session = Depends(get_db)):
    return db.query(DietPlan).filter(DietPlan.is_active == True).first()  # noqa: E712


@router.post("/diet-plans", response_model=DietPlanResponse)
def create_diet_plan(data: DietPlanCreate, db: Session = Depends(get_db)):
    if data.is_active:
        db.query(DietPlan).update({DietPlan.is_active: False})
    plan = DietPlan(**data.model_dump())
    db.add(plan)
    db.commit()
    db.refresh(plan)
    return plan


@router.put("/diet-plans/{plan_id}", response_model=DietPlanResponse)
def update_diet_plan(plan_id: int, data: DietPlanCreate, db: Session = Depends(get_db)):
    plan = db.query(DietPlan).filter(DietPlan.id == plan_id).first()
    if not plan:
        raise HTTPException(404, "Diet plan not found")
    if data.is_active:
        db.query(DietPlan).update({DietPlan.is_active: False})
    for key, val in data.model_dump().items():
        setattr(plan, key, val)
    db.commit()
    db.refresh(plan)
    return plan


@router.delete("/diet-plans/{plan_id}")
def delete_diet_plan(plan_id: int, db: Session = Depends(get_db)):
    plan = db.query(DietPlan).filter(DietPlan.id == plan_id).first()
    if not plan:
        raise HTTPException(404, "Diet plan not found")
    db.delete(plan)
    db.commit()
    return {"ok": True}


# ── Weight Goal (Phase 32) ──
@router.get("/users/{user_id}/weight-goal")
def get_weight_goal(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(404, "User not found")
    return weight_progress(user) or {"initial": None, "current": None, "target": None, "percent": 0.0}


@router.put("/users/{user_id}/weight-goal")
def update_weight_goal(user_id: int, data: dict, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(404, "User not found")
    for key in ("initial_weight", "current_weight", "target_weight"):
        if key in data:
            setattr(user, key, data[key])
    db.commit()
    return weight_progress(user) or {"initial": None, "current": None, "target": None, "percent": 0.0}


# ── Membership (Phase 33) ──
@router.get("/users/{user_id}/membership")
def get_membership(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(404, "User not found")
    return membership_info(user)
