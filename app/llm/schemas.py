from pydantic import BaseModel, Field
from typing import List, Optional


class TenderRequirements(BaseModel):
    role: Optional[str] = None
    domain: Optional[str] = None
    skills_required: List[str] = Field(default_factory=list)
    preferred_skills: List[str] = Field(default_factory=list)
    experience_required: Optional[int] = None
    qualifications: List[str] = Field(default_factory=list)
    responsibilities: List[str] = Field(default_factory=list)


class ResumeProfile(BaseModel):
    candidate_name: Optional[str] = None
    role: Optional[str] = None
    domain: Optional[str] = None
    skills: List[str] = Field(default_factory=list)
    experience_years: Optional[int] = None
    qualifications: List[str] = Field(default_factory=list)
    projects: List[str] = Field(default_factory=list)