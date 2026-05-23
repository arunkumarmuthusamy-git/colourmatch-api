"""
AI Colour Matching App — Pydantic Schemas
Request/Response models for the API
"""

from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional, List
from datetime import datetime


# ──────────────────────────────────────────────
# Auth Schemas
# ──────────────────────────────────────────────
class RegisterRequest(BaseModel):
    email: str = Field(..., min_length=5, max_length=255)
    password: str = Field(..., min_length=6, max_length=128)
    full_name: str = Field(..., min_length=1, max_length=100)
    company_name: Optional[str] = None
    role: Optional[str] = "merchandiser"
    country: Optional[str] = None

    @field_validator("email")
    @classmethod
    def validate_email(cls, v):
        if "@" not in v or "." not in v:
            raise ValueError("Invalid email format")
        return v.lower().strip()


class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds


class UserResponse(BaseModel):
    id: str
    email: str
    full_name: str
    company_name: Optional[str] = None
    role: str
    country: Optional[str] = None
    auth_provider: str
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class UserProfileUpdate(BaseModel):
    full_name: Optional[str] = None
    company_name: Optional[str] = None
    role: Optional[str] = None
    country: Optional[str] = None


# ──────────────────────────────────────────────
# Subscription Schemas
# ──────────────────────────────────────────────
class SubscriptionResponse(BaseModel):
    plan: str
    status: str
    trial_start_date: Optional[datetime] = None
    trial_end_date: Optional[datetime] = None
    sessions_used: int
    sessions_limit: int
    subscription_start: Optional[datetime] = None
    subscription_end: Optional[datetime] = None
    grace_period_end: Optional[datetime] = None

    class Config:
        from_attributes = True


class LicenseValidation(BaseModel):
    is_valid: bool
    plan: str
    status: str
    sessions_remaining: int
    days_remaining: Optional[int] = None
    features: dict  # {colour_match: true, dye_recipe: false, pdf_export: false, ...}
    message: str


# ──────────────────────────────────────────────
# Session Schemas
# ──────────────────────────────────────────────
class SessionCreate(BaseModel):
    session_name: Optional[str] = None
    session_type: str = "colour_match"
    lighting_condition: str = "indoor"

    @field_validator("session_type")
    @classmethod
    def validate_session_type(cls, v):
        if v not in ["colour_match", "dye_recipe"]:
            raise ValueError("session_type must be 'colour_match' or 'dye_recipe'")
        return v

    @field_validator("lighting_condition")
    @classmethod
    def validate_lighting(cls, v):
        if v not in ["indoor", "outdoor"]:
            raise ValueError("lighting_condition must be 'indoor' or 'outdoor'")
        return v


class SessionSummary(BaseModel):
    id: str
    session_name: Optional[str] = None
    session_type: str
    lighting_condition: str
    status: str
    is_starred: bool
    source_hex: Optional[str] = None
    best_match_percent: Optional[float] = None
    nearest_pantone_1: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class ComparisonCaseResponse(BaseModel):
    id: str
    case_name: Optional[str] = None
    case_number: int
    lighting_condition: str
    avg_lab_l: Optional[float] = None
    avg_lab_a: Optional[float] = None
    avg_lab_b: Optional[float] = None
    case_hex: Optional[str] = None
    delta_e: Optional[float] = None
    match_percent: Optional[float] = None
    delta_l: Optional[float] = None
    delta_a: Optional[float] = None
    delta_b: Optional[float] = None
    interpretation: Optional[str] = None
    recommendation: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class PhotoResponse(BaseModel):
    id: str
    photo_type: str
    s3_url: Optional[str] = None
    local_path: Optional[str] = None
    lighting_condition: str
    raw_lab_l: Optional[float] = None
    raw_lab_a: Optional[float] = None
    raw_lab_b: Optional[float] = None
    corrected_lab_l: Optional[float] = None
    corrected_lab_a: Optional[float] = None
    corrected_lab_b: Optional[float] = None
    photo_order: int
    created_at: datetime

    class Config:
        from_attributes = True


class SessionDetail(BaseModel):
    id: str
    session_name: Optional[str] = None
    session_type: str
    lighting_condition: str
    status: str
    is_starred: bool
    source_lab_l: Optional[float] = None
    source_lab_a: Optional[float] = None
    source_lab_b: Optional[float] = None
    source_hex: Optional[str] = None
    nearest_pantone_1: Optional[str] = None
    nearest_pantone_2: Optional[str] = None
    nearest_pantone_3: Optional[str] = None
    confidence_score: Optional[float] = None
    best_match_percent: Optional[float] = None
    created_at: datetime
    updated_at: datetime
    photos: List[PhotoResponse] = []
    cases: List[ComparisonCaseResponse] = []

    class Config:
        from_attributes = True


# ──────────────────────────────────────────────
# Comparison Case Schemas
# ──────────────────────────────────────────────
class CaseCreate(BaseModel):
    case_name: Optional[str] = None
    lighting_condition: str = "indoor"


# ──────────────────────────────────────────────
# Photo Upload Schemas
# ──────────────────────────────────────────────
class PhotoUploadRequest(BaseModel):
    photo_type: str  # source / comparison
    case_id: Optional[str] = None  # Required for comparison photos
    lighting_condition: str = "indoor"
    roi_x: Optional[int] = None
    roi_y: Optional[int] = None
    roi_width: Optional[int] = None
    roi_height: Optional[int] = None


class PresignedUrlResponse(BaseModel):
    upload_url: str
    s3_key: str
    expires_in: int


# ──────────────────────────────────────────────
# Colour Science Schemas
# ──────────────────────────────────────────────
class LabColour(BaseModel):
    L: float = Field(..., ge=0, le=100)
    a: float = Field(..., ge=-128, le=127)
    b: float = Field(..., ge=-128, le=127)


class ColourMatchResult(BaseModel):
    delta_e: float
    match_percent: float
    delta_l: float
    delta_a: float
    delta_b: float
    interpretation: str
    recommendation: str
    source_lab: LabColour
    case_lab: LabColour


# ──────────────────────────────────────────────
# Feedback Schemas
# ──────────────────────────────────────────────
class FeedbackCreate(BaseModel):
    feedback_type: str = "colour_match"
    star_rating: Optional[int] = Field(None, ge=1, le=5)
    comment: Optional[str] = None
    lighting_correct: Optional[bool] = None
    corrected_lighting: Optional[str] = None
    attributes: Optional[dict] = None  # {darker, lighter, more_red, etc.}
    used_in_bulk: bool = False


class FeedbackResponse(BaseModel):
    id: str
    feedback_type: str
    star_rating: Optional[int] = None
    comment: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


# ──────────────────────────────────────────────
# Paginated Response
# ──────────────────────────────────────────────
class PaginatedSessions(BaseModel):
    items: List[SessionSummary]
    total: int
    page: int
    page_size: int
    total_pages: int
