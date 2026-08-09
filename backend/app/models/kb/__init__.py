"""Knowledge Core models (Second Brain Phase 1 + Phase 2)."""

from app.models.kb.source import KbSource
from app.models.kb.document import KbDocument
from app.models.kb.chunk import KbChunk
from app.models.kb.tag import KbTag
from app.models.kb.document_tag import KbDocumentTag
from app.models.kb.edge import KbEdge
from app.models.kb.concept import KbConcept
from app.models.kb.version import KbVersion
from app.models.kb.job import KbJob
from app.models.kb.embedding import KbEmbedding
from app.models.kb.eval_run import KbEvalRun
from app.models.kb.search_event import KbSearchEvent
# Phase 4 (Note Intelligence & Content Generation)
from app.models.kb.summary import KbSummary
from app.models.kb.quiz_link import KbQuizLink
from app.models.kb.flashcard_candidate import KbFlashcardCandidate
from app.models.kb.citation import KbCitation
from app.models.kb.quality_suggestion import KbQualitySuggestion
from app.models.kb.generation_log import KbGenerationLog
# Phase 5 (Subject Management Core, Ideas 41–50)
from app.models.kb.subject_profile import SubjectProfile
from app.models.kb.topic import Topic
from app.models.kb.roadmap import Roadmap
from app.models.kb.topic_dependency import TopicDependency
# Phase 6 (Study Planning & Execution, Ideas 51–60)
from app.models.kb.revision_schedule import RevisionSchedule
from app.models.kb.learning_event import LearningEvent
from app.models.kb.lab import Lab
from app.models.kb.attendance import Attendance
from app.models.kb.micro_session import MicroSession
# Phase 7 (AI Tutor & Assessment, Ideas 61–70)
from app.models.kb.tutor_session import TutorSession, TutorMessage
from app.models.kb.practice_question import PracticeQuestion
from app.models.kb.mock_test import MockTest, MockTestAttempt
from app.models.kb.interview_session import InterviewSession
from app.models.kb.adaptive_state import AdaptiveState
from app.models.kb.mistake_analysis import MistakeAnalysis
from app.models.kb.capture_xp_grant import CaptureXpGrant
from app.models.kb.user_skill import UserSkill
# Phase 8 (Personalization & Learning Memory, Ideas 71–80)
from app.models.kb.user_preference import UserPreference
from app.models.kb.user_memory import UserMemory
from app.models.kb.missing_note_suggestion import MissingNoteSuggestion
from app.models.kb.outdated_note import OutdatedNote
# Phase 9 (Automation, Ideas 81–90)
from app.models.kb.categorize_suggestion import CategorizeSuggestion
# Phase 10 (Advanced AI, Analytics & Platform, Ideas 91–100)
from app.models.kb.agent_run import AgentRun
from app.models.kb.episodic_memory import EpisodicMemory
from app.models.kb.reflection import Reflection
from app.models.kb.ai_log import AiLog
from app.models.kb.prompt_version import PromptVersion
from app.models.kb.context_override import ContextOverride

__all__ = [
    "KbChunk",
    "KbCitation",
    "KbConcept",
    "KbDocument",
    "KbDocumentTag",
    "KbEdge",
    "KbEmbedding",
    "KbEvalRun",
    "KbFlashcardCandidate",
    "KbGenerationLog",
    "KbJob",
    "KbQualitySuggestion",
    "KbQuizLink",
    "KbSearchEvent",
    "KbSource",
    "KbSummary",
    "KbTag",
    "KbVersion",
    "Roadmap",
    "SubjectProfile",
    "Topic",
    "TopicDependency",
    "RevisionSchedule",
    "LearningEvent",
    "Lab",
    "Attendance",
    "MicroSession",
    "TutorSession",
    "TutorMessage",
    "PracticeQuestion",
    "MockTest",
    "MockTestAttempt",
    "InterviewSession",
    "AdaptiveState",
    "MistakeAnalysis",
    "CaptureXpGrant",
    "UserSkill",
    "UserPreference",
    "UserMemory",
    "MissingNoteSuggestion",
    "OutdatedNote",
    "CategorizeSuggestion",
    "AgentRun",
    "EpisodicMemory",
    "Reflection",
    "AiLog",
    "PromptVersion",
    "ContextOverride",
]
