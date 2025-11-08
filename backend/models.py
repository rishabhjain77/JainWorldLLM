# backend/models.py

from pydantic import BaseModel, Field
from typing import List, Optional, Literal
from datetime import datetime


class UserProfile(BaseModel):
    """User profile and learning progress"""
    user_id: str
    knowledge_level: Literal["beginner", "intermediate", "advanced"] = "beginner"
    preferred_language: Literal["en", "hi", "mr"] = "en"
    preferred_mode: Literal["audio", "chat", "both"] = "chat"
    learning_interests: List[str] = []
    completed_modules: List[str] = []
    current_module: Optional[str] = None
    session_count: int = 0
    created_at: datetime = Field(default_factory=datetime.now)
    last_active: datetime = Field(default_factory=datetime.now)


class ChatMessage(BaseModel):
    """Single chat message"""
    role: Literal["user", "assistant", "system"]
    content: str
    timestamp: datetime = Field(default_factory=datetime.now)


class ChatRequest(BaseModel):
    """Request for chat completion"""
    message: str
    user_id: str
    session_id: Optional[str] = None
    include_audio: bool = False
    language: str = "en"


class ChatResponse(BaseModel):
    """Response from chat completion"""
    message: str
    sources: List[dict] = []  # RAG sources
    audio_url: Optional[str] = None
    session_id: str
    suggestions: List[str] = []  # Suggested follow-up questions


class OnboardingRequest(BaseModel):
    """User onboarding information"""
    knowledge_level: Literal["beginner", "intermediate", "advanced"]
    preferred_language: Literal["en", "hi", "mr"]
    preferred_mode: Literal["audio", "chat", "both"]
    interests: List[str] = []


class LearningModule(BaseModel):
    """A learning module/lesson"""
    module_id: str
    title: str
    description: str
    difficulty: Literal["beginner", "intermediate", "advanced"]
    category: Literal["philosophy", "stories", "practices", "scriptures"]
    estimated_duration: int  # minutes
    prerequisites: List[str] = []
    content: str
    language: str = "en"


class Document(BaseModel):
    """Document chunk for vector DB"""
    doc_id: str
    content: str
    metadata: dict
    source_url: Optional[str] = None