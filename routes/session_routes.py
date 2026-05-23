"""
Session Routes — CRUD for colour matching sessions
"""
import math
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session as DbSession
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from models import User, Session, Subscription, ComparisonCase, get_db
from schemas import (SessionCreate, SessionSummary, SessionDetail,
                     ComparisonCaseResponse, CaseCreate, PaginatedSessions)
from services.auth_service import get_current_user

router = APIRouter(prefix="/api/sessions", tags=["Sessions"])


def check_session_limit(user: User, db: DbSession):
    """Check if user has remaining sessions in their plan."""
    sub = db.query(Subscription).filter(Subscription.user_id == user.id).first()
    if not sub:
        raise HTTPException(status_code=403, detail="No active subscription")
    if sub.status != "active":
        raise HTTPException(status_code=403, detail="Subscription expired")
    if sub.plan == "free_trial":
        if sub.trial_end_date and sub.trial_end_date < datetime.utcnow():
            sub.status = "expired"
            db.commit()
            raise HTTPException(status_code=403, detail="Free trial expired")
        if sub.sessions_used >= sub.sessions_limit:
            raise HTTPException(status_code=403, detail="Session limit reached")
    return sub


@router.post("", response_model=SessionSummary)
def create_session(req: SessionCreate, user: User = Depends(get_current_user),
                   db: DbSession = Depends(get_db)):
    sub = check_session_limit(user, db)
    session = Session(
        user_id=user.id, session_name=req.session_name,
        session_type=req.session_type, lighting_condition=req.lighting_condition)
    db.add(session)
    sub.sessions_used += 1
    db.commit()
    db.refresh(session)
    return session


@router.get("", response_model=PaginatedSessions)
def list_sessions(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: str = Query("", max_length=200),
    session_type: str = Query("", max_length=20),
    starred: bool = Query(False),
    user: User = Depends(get_current_user),
    db: DbSession = Depends(get_db),
):
    q = db.query(Session).filter(Session.user_id == user.id)
    if search:
        q = q.filter(Session.session_name.ilike(f"%{search}%"))
    if session_type:
        q = q.filter(Session.session_type == session_type)
    if starred:
        q = q.filter(Session.is_starred == True)
    total = q.count()
    items = q.order_by(Session.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return PaginatedSessions(
        items=items, total=total, page=page, page_size=page_size,
        total_pages=math.ceil(total / page_size) if total > 0 else 1)


@router.get("/{session_id}", response_model=SessionDetail)
def get_session(session_id: str, user: User = Depends(get_current_user),
                db: DbSession = Depends(get_db)):
    session = db.query(Session).filter(
        Session.id == session_id, Session.user_id == user.id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


@router.delete("/{session_id}")
def delete_session(session_id: str, user: User = Depends(get_current_user),
                   db: DbSession = Depends(get_db)):
    session = db.query(Session).filter(
        Session.id == session_id, Session.user_id == user.id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    db.delete(session)
    db.commit()
    return {"message": "Session deleted"}


@router.patch("/{session_id}/star")
def toggle_star(session_id: str, user: User = Depends(get_current_user),
                db: DbSession = Depends(get_db)):
    session = db.query(Session).filter(
        Session.id == session_id, Session.user_id == user.id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    session.is_starred = not session.is_starred
    db.commit()
    return {"is_starred": session.is_starred}


@router.post("/{session_id}/cases", response_model=ComparisonCaseResponse)
def add_case(session_id: str, req: CaseCreate,
             user: User = Depends(get_current_user),
             db: DbSession = Depends(get_db)):
    session = db.query(Session).filter(
        Session.id == session_id, Session.user_id == user.id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    case_count = db.query(ComparisonCase).filter(
        ComparisonCase.session_id == session_id).count()
    case = ComparisonCase(
        session_id=session_id, case_name=req.case_name,
        case_number=case_count + 1, lighting_condition=req.lighting_condition)
    db.add(case)
    db.commit()
    db.refresh(case)
    return case
