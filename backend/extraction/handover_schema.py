"""
Pydantic Schemas for Standardized 9-Category Clinical Handover.
"""

from typing import List, Optional
from pydantic import BaseModel, Field

class PatientDemographics(BaseModel):
    bed: Optional[str] = None
    name: Optional[str] = None
    age: Optional[int] = None
    gender: Optional[str] = None
    doctor: Optional[str] = None

class HandoverCategoryOutput(BaseModel):
    patient_info: PatientDemographics = Field(default_factory=PatientDemographics)
    current_condition: List[str] = Field(default_factory=list)
    medical_history: List[str] = Field(default_factory=list)
    medications: List[str] = Field(default_factory=list)
    investigations: List[str] = Field(default_factory=list)
    clinical_events: List[str] = Field(default_factory=list)
    temporal_information: List[str] = Field(default_factory=list)
    pending_tasks: List[str] = Field(default_factory=list)
    follow_up: List[str] = Field(default_factory=list)
