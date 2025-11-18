from __future__ import annotations

from typing import List, Optional
from pydantic import BaseModel, Field

# StudySnap core schema definitions.
# Convention: Class name => collection name lowercased (e.g., Study => "study")

class Study(BaseModel):
    filename: str
    mime_type: str
    topics: List[str] = []
    subtopics: List[str] = []
    key_terms: List[str] = []
    summary: str = ""

class PlanItem(BaseModel):
    day: int = Field(..., ge=1)
    title: str
    priority: str
    micro_goals: List[str] = []
    suggested_minutes: int = 30

class StudyPlan(BaseModel):
    study_id: Optional[str] = None
    items: List[PlanItem] = []

class Explanation(BaseModel):
    level: str  # short | normal | deep
    content: str

class Tip(BaseModel):
    subject: str
    tips: List[str] = []

class MCQOption(BaseModel):
    text: str
    correct: bool = False

class MCQ(BaseModel):
    question: str
    options: List[MCQOption]
    explanation: Optional[str] = None

class AnalyzeResponse(BaseModel):
    study: Study
    plan: StudyPlan
    explanations: List[Explanation]
    tips: Tip
    quiz: List[MCQ]
