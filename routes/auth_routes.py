"""
Auth Routes — Register, Login, Token Refresh, Profile
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session as DbSession
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from models import User, get_db
from schemas import (RegisterRequest, LoginRequest, TokenResponse,
                     UserResponse, UserProfileUpdate)
from services.auth_service import (
    create_user_with_trial, verify_password, create_access_token,
    create_refresh_token, decode_token, get_current_user,
    get_settings
)

router = APIRouter(prefix="/api/auth", tags=["Authentication"])
settings = get_settings()


@router.post("/register", response_model=TokenResponse)
def register(req: RegisterRequest, db: DbSession = Depends(get_db)):
    user = create_user_with_trial(
        db, email=req.email, password=req.password,
        full_name=req.full_name, company_name=req.company_name,
        role=req.role or "merchandiser", country=req.country)
    access = create_access_token(user.id, user.email)
    refresh = create_refresh_token(user.id)
    return TokenResponse(
        access_token=access, refresh_token=refresh,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60)


@router.post("/login", response_model=TokenResponse)
def login(req: LoginRequest, db: DbSession = Depends(get_db)):
    user = db.query(User).filter(User.email == req.email.lower().strip()).first()
    if not user or not verify_password(req.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account deactivated")
    access = create_access_token(user.id, user.email)
    refresh = create_refresh_token(user.id)
    return TokenResponse(
        access_token=access, refresh_token=refresh,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60)


@router.get("/me", response_model=UserResponse)
def get_me(user: User = Depends(get_current_user)):
    return user


@router.post("/refresh", response_model=TokenResponse)
def refresh_token(refresh_tok: str, db: DbSession = Depends(get_db)):
    payload = decode_token(refresh_tok)
    if payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    user = db.query(User).filter(User.id == payload.get("sub")).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    access = create_access_token(user.id, user.email)
    new_refresh = create_refresh_token(user.id)
    return TokenResponse(
        access_token=access, refresh_token=new_refresh,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60)


@router.put("/profile", response_model=UserResponse)
def update_profile(update: UserProfileUpdate, user: User = Depends(get_current_user),
                   db: DbSession = Depends(get_db)):
    if update.full_name:
        user.full_name = update.full_name
    if update.company_name is not None:
        user.company_name = update.company_name
    if update.role:
        user.role = update.role
    if update.country is not None:
        user.country = update.country
    db.commit()
    db.refresh(user)
    return user
