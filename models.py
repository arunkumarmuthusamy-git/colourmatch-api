"""
AI Colour Matching App — Database Models
SQLAlchemy ORM models matching the blueprint schema
"""

import uuid
from datetime import datetime
from sqlalchemy import (
    Column, String, Float, Integer, Boolean, Text, DateTime,
    ForeignKey, JSON, create_engine, event
)
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
from config import get_settings

Base = declarative_base()


def generate_uuid():
    return str(uuid.uuid4())


# ──────────────────────────────────────────────
# User Model
# ──────────────────────────────────────────────
class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(100), nullable=False)
    company_name = Column(String(200), nullable=True)
    company_logo_url = Column(String(500), nullable=True)
    role = Column(String(50), default="merchandiser")  # merchandiser/buyer/dyemaster/qa/lab_tech/other
    country = Column(String(100), nullable=True)
    auth_provider = Column(String(20), default="email")  # email/google/apple
    auth_provider_id = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True)
    is_suspended = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    subscription = relationship("Subscription", back_populates="user", uselist=False)
    sessions = relationship("Session", back_populates="user", order_by="Session.created_at.desc()")
    feedbacks = relationship("Feedback", back_populates="user")


# ──────────────────────────────────────────────
# Subscription Model
# ──────────────────────────────────────────────
class Subscription(Base):
    __tablename__ = "subscriptions"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id"), unique=True, nullable=False)
    plan = Column(String(20), nullable=False, default="free_trial")  # free_trial/basic/pro/enterprise
    status = Column(String(20), default="active")  # active/expired/cancelled/suspended
    trial_start_date = Column(DateTime, nullable=True)
    trial_end_date = Column(DateTime, nullable=True)
    sessions_used = Column(Integer, default=0)
    sessions_limit = Column(Integer, default=20)
    subscription_start = Column(DateTime, nullable=True)
    subscription_end = Column(DateTime, nullable=True)
    grace_period_end = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="subscription")


# ──────────────────────────────────────────────
# Session Model (Colour matching sessions)
# ──────────────────────────────────────────────
class Session(Base):
    __tablename__ = "sessions"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    session_name = Column(String(200), nullable=True)
    session_type = Column(String(20), nullable=False, default="colour_match")  # colour_match / dye_recipe
    lighting_condition = Column(String(20), nullable=False, default="indoor")  # indoor / outdoor
    status = Column(String(20), default="in_progress")  # in_progress/completed/archived
    is_starred = Column(Boolean, default=False)

    # Source colour (averaged, corrected L*a*b*)
    source_lab_l = Column(Float, nullable=True)
    source_lab_a = Column(Float, nullable=True)
    source_lab_b = Column(Float, nullable=True)
    source_hex = Column(String(7), nullable=True)

    # Nearest Pantone matches
    nearest_pantone_1 = Column(String(50), nullable=True)
    nearest_pantone_2 = Column(String(50), nullable=True)
    nearest_pantone_3 = Column(String(50), nullable=True)

    confidence_score = Column(Float, nullable=True)  # 0-1 colour consistency
    best_match_percent = Column(Float, nullable=True)  # Highest case match % for history display

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="sessions")
    photos = relationship("SessionPhoto", back_populates="session", cascade="all, delete-orphan")
    cases = relationship("ComparisonCase", back_populates="session", cascade="all, delete-orphan",
                         order_by="ComparisonCase.case_number")
    feedbacks = relationship("Feedback", back_populates="session")


# ──────────────────────────────────────────────
# Session Photo Model
# ──────────────────────────────────────────────
class SessionPhoto(Base):
    __tablename__ = "session_photos"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    session_id = Column(String(36), ForeignKey("sessions.id"), nullable=False)
    photo_type = Column(String(20), nullable=False)  # source / comparison
    case_id = Column(String(36), ForeignKey("comparison_cases.id"), nullable=True)  # NULL for source photos
    s3_key = Column(String(500), nullable=True)
    s3_url = Column(String(500), nullable=True)
    local_path = Column(String(500), nullable=True)  # For local dev without S3
    lighting_condition = Column(String(20), nullable=False, default="indoor")

    # Region of Interest
    roi_x = Column(Integer, nullable=True)
    roi_y = Column(Integer, nullable=True)
    roi_width = Column(Integer, nullable=True)
    roi_height = Column(Integer, nullable=True)

    # Raw extracted L*a*b* (before correction)
    raw_lab_l = Column(Float, nullable=True)
    raw_lab_a = Column(Float, nullable=True)
    raw_lab_b = Column(Float, nullable=True)

    # Corrected L*a*b* (after lighting correction)
    corrected_lab_l = Column(Float, nullable=True)
    corrected_lab_a = Column(Float, nullable=True)
    corrected_lab_b = Column(Float, nullable=True)

    photo_order = Column(Integer, default=1)  # 1 or 2 (max 2 per source/case)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    session = relationship("Session", back_populates="photos")
    case = relationship("ComparisonCase", back_populates="photos")


# ──────────────────────────────────────────────
# Comparison Case Model
# ──────────────────────────────────────────────
class ComparisonCase(Base):
    __tablename__ = "comparison_cases"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    session_id = Column(String(36), ForeignKey("sessions.id"), nullable=False)
    case_name = Column(String(200), nullable=True)
    case_number = Column(Integer, nullable=False)
    lighting_condition = Column(String(20), nullable=False, default="indoor")

    # Averaged corrected L*a*b*
    avg_lab_l = Column(Float, nullable=True)
    avg_lab_a = Column(Float, nullable=True)
    avg_lab_b = Column(Float, nullable=True)
    case_hex = Column(String(7), nullable=True)

    # Match results
    delta_e = Column(Float, nullable=True)  # CIEDE2000
    match_percent = Column(Float, nullable=True)
    delta_l = Column(Float, nullable=True)
    delta_a = Column(Float, nullable=True)
    delta_b = Column(Float, nullable=True)

    interpretation = Column(String(50), nullable=True)  # excellent/good/marginal/poor/no_match
    recommendation = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    session = relationship("Session", back_populates="cases")
    photos = relationship("SessionPhoto", back_populates="case")


# ──────────────────────────────────────────────
# Feedback Model
# ──────────────────────────────────────────────
class Feedback(Base):
    __tablename__ = "feedback"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    session_id = Column(String(36), ForeignKey("sessions.id"), nullable=False)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    feedback_type = Column(String(20), nullable=False)  # colour_match / dye_recipe
    star_rating = Column(Integer, nullable=True)  # 1-5
    comment = Column(Text, nullable=True)
    actual_result_photo_url = Column(String(500), nullable=True)
    actual_lab_l = Column(Float, nullable=True)
    actual_lab_a = Column(Float, nullable=True)
    actual_lab_b = Column(Float, nullable=True)
    lighting_correct = Column(Boolean, nullable=True)
    corrected_lighting = Column(String(20), nullable=True)
    attributes = Column(JSON, nullable=True)  # {darker, lighter, more_red, more_blue, correct}
    used_in_bulk = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    session = relationship("Session", back_populates="feedbacks")
    user = relationship("User", back_populates="feedbacks")


# ──────────────────────────────────────────────
# Feature Flags Model
# ──────────────────────────────────────────────
class FeatureFlag(Base):
    __tablename__ = "feature_flags"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    plan = Column(String(20), nullable=False)
    feature_key = Column(String(50), nullable=False)
    is_enabled = Column(Boolean, default=True)
    limit_value = Column(Integer, nullable=True)


# ──────────────────────────────────────────────
# Database Engine & Session
# ──────────────────────────────────────────────
settings = get_settings()
engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {},
    echo=settings.DEBUG,
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """Dependency: yields a database session for each request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_tables():
    """Create all tables (for development)."""
    Base.metadata.create_all(bind=engine)


# Enable WAL mode for SQLite for better concurrency
@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    if "sqlite" in settings.DATABASE_URL:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.close()
