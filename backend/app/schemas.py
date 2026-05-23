from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


class APIModel(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")


class QuestionDTO(APIModel):
    id: str
    domain: str
    chapter_group: str
    chapter_id: str
    difficulty: str
    question: str
    choices: List[str] = Field(min_length=4, max_length=4)
    learning: Dict[str, Any] = Field(default_factory=dict)


class AnswerRequest(APIModel):
    question_id: str
    selected_index: int = Field(ge=0, le=3)
    elapsed_ms: Optional[int] = Field(default=None, ge=0, le=3_600_000)


class AnswerResult(APIModel):
    correct: bool
    selected_index: int
    correct_index: int
    correct_choice: str
    explanation: str
    learning: Dict[str, Any] = Field(default_factory=dict)


class StartSessionRequest(APIModel):
    display_name: Optional[str] = Field(default=None, max_length=60)


class SessionResponse(APIModel):
    learner_id: str
    display_name: str
    token: str
    session_expires_at: str
    policy_variant: str


class LogoutResponse(APIModel):
    revoked: bool


class AccountProfile(APIModel):
    user_id: int
    learner_id: str
    display_name: str = ""
    policy_variant: str


class ImportBundleRequest(APIModel):
    bundle: Dict[str, Any]


class ImportBundleResult(APIModel):
    imported_answers: int
    imported_learning_items: int


class PolicyPreferenceRequest(APIModel):
    policy_variant: Literal["adaptive_mastery_v2", "chapter_balanced_v1", "random_baseline_v1"]


class PolicyPreferenceResponse(APIModel):
    policy_variant: str
    experiment: Dict[str, Any]
