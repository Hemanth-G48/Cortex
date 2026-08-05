from app.schemas.user import UserBase, UserCreate, UserUpdate, UserResponse, UserSignup, UserLogin
from app.schemas.course import CourseBase, CourseCreate, CourseResponse
from app.schemas.assignment import (
    AssignmentBase,
    AssignmentCreate,
    AssignmentResponse,
    AssignmentUpdate,
    AssignmentStatusUpdate,
    ExamBase,
    ExamCreate,
    ExamResponse,
)
from app.schemas.note import NoteBase, NoteCreate, NoteResponse, GoalBase, GoalCreate, GoalResponse
from app.schemas.task import (
    TaskBase, TaskCreate, TaskResponse,
    ReminderBase, ReminderCreate, ReminderUpdate, ReminderResponse,
    ScheduleBase, ScheduleCreate, ScheduleResponse,
)
from app.schemas.habit import HabitBase, HabitCreate, HabitResponse, HabitLogBase, HabitLogCreate, HabitLogResponse
from app.schemas.pomodoro import PomodoroSessionBase, PomodoroSessionCreate, PomodoroSessionResponse
from app.schemas.fitness import (
    WorkoutBase, WorkoutCreate, WorkoutResponse,
    FitnessGoalBase, FitnessGoalCreate, FitnessGoalResponse,
    ExerciseBase, ExerciseCreate, ExerciseResponse,
    MuscleGroupBase, MuscleGroupCreate, MuscleGroupResponse,
    WorkoutSplitBase, WorkoutSplitCreate, WorkoutSplitResponse,
    ExpenseBase, ExpenseCreate, ExpenseResponse, ExpenseSummary,
    PersonalRecordBase, PersonalRecordCreate, PersonalRecordResponse,
    DietPlanBase, DietPlanCreate, DietPlanResponse,
)
from app.schemas.journal import JournalEntryBase, JournalEntryCreate, JournalEntryResponse
from app.schemas.quest import QuestBase, QuestCreate, QuestResponse, QuestTaskBase, QuestTaskCreate, QuestTaskResponse
from app.schemas.project import ProjectBase, ProjectCreate, ProjectResponse, ProjectTaskBase, ProjectTaskCreate, ProjectTaskResponse
from app.schemas.life_area import LifeAreaBase, LifeAreaCreate, LifeAreaUpdate, LifeAreaResponse
from app.schemas.character import CharacterBase, CharacterCreate, CharacterUpdate, CharacterResponse, AddXpRequest
from app.schemas.reward import RewardBase, RewardCreate, RewardUpdate, RewardResponse, ClaimRewardResponse
from app.schemas.schedule_event import ScheduleEventBase, ScheduleEventCreate, ScheduleEventUpdate, ScheduleEventResponse
from app.schemas.mission import (
    MissionBase, MissionCreate, MissionUpdate, MissionResponse,
    MissionTaskBase, MissionTaskCreate, MissionTaskUpdate, MissionTaskResponse,
)
from app.schemas.daily_log import DailyLogBase, DailyLogCreate, DailyLogUpdate, DailyLogResponse
from app.schemas.event import EventBase, EventCreate, EventUpdate, EventResponse
from app.schemas.grade import (
    GradeBase, GradeCreate, GradeResponse,
    CourseWeightBase, CourseWeightCreate, CourseWeightUpdate, CourseWeightResponse,
    GradeCalculateRequest, GradeCalculateResponse,
    NeededOnFinalRequest, NeededOnFinalResponse,
    GPACourse, GPAResponse,
)
from app.schemas.flashcard import (
    FlashcardBase, FlashcardCreate, FlashcardUpdate, FlashcardResponse,
    FlashcardDeckBase, FlashcardDeckCreate, FlashcardDeckUpdate, FlashcardDeckResponse,
    FlashcardDeckSummary,
)
from app.schemas.study_plan import StudyPlanBase, StudyPlanCreate, StudyPlanResponse, StudyPlanWeek
from app.schemas.mood import (
    MoodCreate,
    MoodResponse,
    MoodAnalytics,
    MoodDistributionItem,
    MoodDailyPoint,
    MoodWeekly,
    MoodInsight,
    SessionParams,
)
from app.schemas.sleep import (
    SleepCreate,
    SleepUpdate,
    SleepResponse,
    SleepAnalytics,
    SleepDayPoint,
    SleepSummary,
    SleepRecommendation,
)
from app.schemas.book import (
    BookBase, BookCreate, BookUpdate, BookResponse, BookInsights,
)
from app.schemas.braindump import BrainDumpCreate, BrainDumpResponse
from app.schemas.daily_schedule import (
    DailyScheduleItemBase, DailyScheduleItemCreate, DailyScheduleItemUpdate,
    DailyScheduleItemResponse, DailyScheduleStats,
)
from app.schemas.notification import (
    NotificationCreate, NotificationResponse, NotificationUnreadCount,
)
from app.schemas.study_stats import (
    CourseAnalytics, OverallAnalytics, AssignmentAnalyticsResponse,
)

__all__ = [
    "AddXpRequest",
    "AssignmentBase", "AssignmentCreate", "AssignmentResponse",
    "CharacterBase", "CharacterCreate", "CharacterUpdate", "CharacterResponse",
    "ClaimRewardResponse",
    "CourseBase", "CourseCreate", "CourseResponse",
    "DailyLogBase", "DailyLogCreate", "DailyLogUpdate", "DailyLogResponse",
    "EventBase", "EventCreate", "EventUpdate", "EventResponse",
    "RewardBase", "RewardCreate", "RewardUpdate", "RewardResponse",
    "ScheduleEventBase", "ScheduleEventCreate", "ScheduleEventUpdate", "ScheduleEventResponse",
    "ExamBase", "ExamCreate", "ExamResponse",
    "FitnessGoalBase", "FitnessGoalCreate", "FitnessGoalResponse",
    "ExerciseBase", "ExerciseCreate", "ExerciseResponse",
    "MuscleGroupBase", "MuscleGroupCreate", "MuscleGroupResponse",
    "WorkoutSplitBase", "WorkoutSplitCreate", "WorkoutSplitResponse",
    "ExpenseBase", "ExpenseCreate", "ExpenseResponse", "ExpenseSummary",
    "PersonalRecordBase", "PersonalRecordCreate", "PersonalRecordResponse",
    "DietPlanBase", "DietPlanCreate", "DietPlanResponse",
    "GoalBase", "GoalCreate", "GoalResponse",
    "HabitBase", "HabitCreate", "HabitResponse",
    "HabitLogBase", "HabitLogCreate", "HabitLogResponse",
    "JournalEntryBase", "JournalEntryCreate", "JournalEntryResponse",
    "LifeAreaBase", "LifeAreaCreate", "LifeAreaUpdate", "LifeAreaResponse",
    "MissionBase", "MissionCreate", "MissionUpdate", "MissionResponse",
    "MissionTaskBase", "MissionTaskCreate", "MissionTaskUpdate", "MissionTaskResponse",
    "MoodAnalytics", "MoodCreate", "MoodDailyPoint", "MoodDistributionItem",
    "MoodInsight", "MoodResponse", "MoodWeekly",
    "NoteBase", "NoteCreate", "NoteResponse",
    "PomodoroSessionBase", "PomodoroSessionCreate", "PomodoroSessionResponse",
    "ProjectBase", "ProjectCreate", "ProjectResponse",
    "ProjectTaskBase", "ProjectTaskCreate", "ProjectTaskResponse",
    "QuestBase", "QuestCreate", "QuestResponse",
    "QuestTaskBase", "QuestTaskCreate", "QuestTaskResponse",
    "ReminderBase", "ReminderCreate", "ReminderUpdate", "ReminderResponse",
    "ScheduleBase", "ScheduleCreate", "ScheduleResponse",
    "SessionParams",
    "SleepAnalytics", "SleepCreate", "SleepDayPoint", "SleepRecommendation",
    "SleepResponse", "SleepSummary", "SleepUpdate",
    "TaskBase", "TaskCreate", "TaskResponse",
    "UserBase", "UserCreate", "UserUpdate", "UserResponse", "UserSignup", "UserLogin",
    "WorkoutBase", "WorkoutCreate", "WorkoutResponse",
    "AssignmentUpdate", "AssignmentStatusUpdate",
    "BookBase", "BookCreate", "BookUpdate", "BookResponse", "BookInsights",
    "BrainDumpCreate", "BrainDumpResponse",
    "DailyScheduleItemBase", "DailyScheduleItemCreate", "DailyScheduleItemUpdate",
    "DailyScheduleItemResponse", "DailyScheduleStats",
    "NotificationCreate", "NotificationResponse", "NotificationUnreadCount",
    "CourseAnalytics", "OverallAnalytics", "AssignmentAnalyticsResponse",
]
