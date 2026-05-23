"""
Create test user accounts for the Colour Matching App.
Run this script to seed the database with login credentials.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from models import create_tables, SessionLocal, User, Subscription
from services.auth_service import hash_password
from datetime import datetime, timedelta
from config import get_settings

settings = get_settings()

def create_user(email, password, full_name, company_name=None, role="merchandiser", country="India"):
    db = SessionLocal()
    try:
        # Check if user already exists
        existing = db.query(User).filter(User.email == email.lower().strip()).first()
        if existing:
            print(f"  [!] User '{email}' already exists (ID: {existing.id})")
            return existing
        
        # Create user
        user = User(
            email=email.lower().strip(),
            password_hash=hash_password(password),
            full_name=full_name,
            company_name=company_name,
            role=role,
            country=country,
        )
        db.add(user)
        db.flush()
        
        # Create free trial subscription
        trial_start = datetime.utcnow()
        sub = Subscription(
            user_id=user.id,
            plan="free_trial",
            status="active",
            trial_start_date=trial_start,
            trial_end_date=trial_start + timedelta(days=settings.FREE_TRIAL_DAYS),
            sessions_used=0,
            sessions_limit=settings.FREE_TRIAL_SESSIONS,
        )
        db.add(sub)
        db.commit()
        db.refresh(user)
        
        print(f"  [OK] User created successfully!")
        print(f"     User ID  : {user.id}")
        print(f"     Email    : {user.email}")
        print(f"     Name     : {user.full_name}")
        print(f"     Plan     : Free Trial (30 days, 20 sessions)")
        return user
    finally:
        db.close()


if __name__ == "__main__":
    print("")
    print("=" * 55)
    print("  Colour Match AI -- User Account Setup")
    print("=" * 55)
    
    # Ensure tables exist
    create_tables()
    print("\n[*] Database tables ready.\n")
    
    # --- User 1: Admin / Owner ---
    print("-" * 45)
    print("  Creating User 1: Admin")
    print("-" * 45)
    create_user(
        email="admin@colourmatch.ai",
        password="Admin@123",
        full_name="Arun Kumar",
        company_name="ColourMatch AI",
        role="merchandiser",
        country="India",
    )
    
    # --- User 2: Demo / Test User ---
    print("")
    print("-" * 45)
    print("  Creating User 2: Demo User")
    print("-" * 45)
    create_user(
        email="demo@colourmatch.ai",
        password="Demo@123",
        full_name="Demo User",
        company_name="Test Company",
        role="dyemaster",
        country="India",
    )
    
    print("")
    print("=" * 55)
    print("  LOGIN CREDENTIALS")
    print("=" * 55)
    print("")
    print("  +---------------------------------------------+")
    print("  |  User 1 (Admin):                            |")
    print("  |    Email    : admin@colourmatch.ai           |")
    print("  |    Password : Admin@123                      |")
    print("  |                                              |")
    print("  |  User 2 (Demo):                              |")
    print("  |    Email    : demo@colourmatch.ai            |")
    print("  |    Password : Demo@123                       |")
    print("  +---------------------------------------------+")
    print("")
    print("  Use these credentials in the mobile app login screen.")
    print("  Make sure the backend server is running: python main.py")
    print("")
