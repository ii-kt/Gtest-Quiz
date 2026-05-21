from typing import List

from pydantic import BaseModel, Field


class QuestionDTO(BaseModel):
    id: str
    domain: str
    chapter_group: str
    chapter_id: str
    difficulty: str
    question: str
    choices: List[str] = Field(min_length=4, max_length=4)
    correct_index: int
    explanation: str


class AnswerRequest(BaseModel):
    question_id: str
    selected_index: int


class AnswerResult(BaseModel):
    correct: bool
    correct_index: int
    explanation: str


class RegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=40)


class RegisterResponse(BaseModel):
    username: str
    token: str


class LoginRequest(BaseModel):
    username: str = Field(min_length=3, max_length=40)


class LoginResponse(BaseModel):
    username: str
    token: str
