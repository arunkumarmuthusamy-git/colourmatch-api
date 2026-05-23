"""
AI Colour Matching App — Authentication Service
JWT tokens, password hashing, and user registration
"""
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session as DbSession
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import get_settings
from models import User, Subscription, get_db

settings = get_settings()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)

def create_access_token(user_id: str, email: str) -> str:
    expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    return jwt.encode({"sub": user_id, "email": email, "type": "access", "exp": expire}, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

def create_refresh_token(user_id: str) -> str:
    expire = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    return jwt.encode({"sub": user_id, "type": "refresh", "exp": expire}, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

def get_current_user(token: str = Depends(oauth2_scheme), db: DbSession = Depends(get_db)) -> User:
    payload = decode_token(token)
    if payload.get("type") != "access":
        raise HTTPException(status_code=401, detail="Invalid token type")
    user = db.query(User).filter(User.id == payload.get("sub")).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account deactivated")
    if user.is_suspended:
        raise HTTPException(status_code=403, detail="Account suspended")
    return user

def create_user_with_trial(db: DbSession, email: str, password: str, full_name: str,
                           company_name: Optional[str] = None, role: str = "merchandiser", country: Optional[str] = None) -> User:
    existing = db.query(User).filter(User.email == email.lower().strip()).first()
    if existing:
        raise HTTPException(status_code=409, detail="Email already registered")
    user = User(email=email.lower().strip(), password_hash=hash_password(password),
                full_name=full_name, company_name=company_name, role=role, country=country)
    db.add(user)
    db.flush()
    trial_start = datetime.utcnow()
    sub = Subscription(user_id=user.id, plan="free_trial", status="active",
                       trial_start_date=trial_start, trial_end_date=trial_start + timedelta(days=settings.FREE_TRIAL_DAYS),
                       sessions_used=0, sessions_limit=settings.FREE_TRIAL_SESSIONS)
    db.add(sub)
    db.commit()
    db.refresh(user)
    return user
