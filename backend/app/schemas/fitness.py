from datetime import date
from typing import Optional

from pydantic import BaseModel, ConfigDict


# ── Fitness Hub schemas (99-phase plan, Phases 17-20) ──

class ExerciseBase(BaseModel):
    name: str
    muscle_group_id: Optional[int] = None
    sets: int = 3
    reps: int = 10
    weight: float = 0.0


class ExerciseCreate(ExerciseBase):
    user_id: int = 1


class ExerciseResponse(ExerciseBase):
    id: int
    user_id: int
    muscle_group_id: Optional[int] = None
    model_config = ConfigDict(from_attributes=True)


class MuscleGroupBase(BaseModel):
    name: str
    body_part: str = "Upper"
    image_3d_url: Optional[str] = None
    sort_order: int = 0


class MuscleGroupCreate(MuscleGroupBase):
    user_id: int = 1


class MuscleGroupResponse(MuscleGroupBase):
    id: int
    user_id: int
    model_config = ConfigDict(from_attributes=True)


class WorkoutSplitBase(BaseModel):
    day_of_week: int = 0
    split_name: str = "PUSH"
    exercise_list: Optional[str] = None
    week_number: int = 1


class WorkoutSplitCreate(WorkoutSplitBase):
    user_id: int = 1


class WorkoutSplitResponse(WorkoutSplitBase):
    id: int
    user_id: int
    model_config = ConfigDict(from_attributes=True)


class ExpenseBase(BaseModel):
    title: str
    cost: float = 0.0
    date: date
    category: str = "Supplement"


class ExpenseCreate(ExpenseBase):
    user_id: int = 1


class ExpenseResponse(ExpenseBase):
    id: int
    user_id: int
    model_config = ConfigDict(from_attributes=True)


class ExpenseSummary(BaseModel):
    total: float
    by_category: dict[str, float]


class PersonalRecordBase(BaseModel):
    exercise_name: str
    current_weight: float = 0.0
    target_weight: float = 0.0
    unit: str = "kg"


class PersonalRecordCreate(PersonalRecordBase):
    user_id: int = 1


class PersonalRecordResponse(PersonalRecordBase):
    id: int
    user_id: int
    model_config = ConfigDict(from_attributes=True)


class DietPlanBase(BaseModel):
    title: str
    is_active: bool = False
    sort_order: int = 0


class DietPlanCreate(DietPlanBase):
    user_id: int = 1


class DietPlanResponse(DietPlanBase):
    id: int
    user_id: int
    model_config = ConfigDict(from_attributes=True)


class WorkoutBase(BaseModel):
    date: date
    type: str
    duration_minutes: int
    calories: Optional[int] = None
    notes: Optional[str] = None


class WorkoutCreate(WorkoutBase):
    user_id: int


class WorkoutResponse(WorkoutBase):
    id: int
    user_id: int
    model_config = ConfigDict(from_attributes=True)


class FitnessGoalBase(BaseModel):
    name: str
    target: float
    current: float = 0.0
    unit: Optional[str] = None


class FitnessGoalCreate(FitnessGoalBase):
    user_id: int


class FitnessGoalResponse(FitnessGoalBase):
    id: int
    user_id: int
    model_config = ConfigDict(from_attributes=True)
