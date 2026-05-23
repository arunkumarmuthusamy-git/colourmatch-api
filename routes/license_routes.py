"""
License Routes — Subscription validation and feature flags
"""
from datetime import datetime
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session as DbSession
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from models import User, Subscription, FeatureFlag, get_db
from schemas import LicenseValidation, SubscriptionResponse
from services.auth_service import get_current_user

router = APIRouter(prefix="/api/license", tags=["License & Subscription"])

# Default feature access by plan
PLAN_FEATURES = {
    "free_trial": {
        "colour_match": True, "dye_recipe": False, "pdf_export": False,
        "multi_photo": True, "pantone_lookup": True, "max_cases": 3,
        "history_access": True, "feedback": True,
    },
    "basic": {
        "colour_match": True, "dye_recipe": False, "pdf_export": True,
        "multi_photo": True, "pantone_lookup": True, "max_cases": 5,
        "history_access": True, "feedback": True,
    },
    "pro": {
        "colour_match": True, "dye_recipe": True, "pdf_export": True,
        "multi_photo": True, "pantone_lookup": True, "max_cases": 10,
        "history_access": True, "feedback": True,
    },
    "enterprise": {
        "colour_match": True, "dye_recipe": True, "pdf_export": True,
        "multi_photo": True, "pantone_lookup": True, "max_cases": 999,
        "history_access": True, "feedback": True,
    },
}


@router.get("/validate", response_model=LicenseValidation)
def validate_license(user: User = Depends(get_current_user),
                     db: DbSession = Depends(get_db)):
    sub = db.query(Subscription).filter(Subscription.user_id == user.id).first()
    if not sub:
        return LicenseValidation(
            is_valid=False, plan="none", status="no_subscription",
            sessions_remaining=0, features={}, message="No subscription found")

    now = datetime.utcnow()
    days_remaining = None

    # Check trial expiry
    if sub.plan == "free_trial":
        if sub.trial_end_date and sub.trial_end_date < now:
            sub.status = "expired"
            db.commit()
        days_remaining = max(0, (sub.trial_end_date - now).days) if sub.trial_end_date else 0

    # Check paid subscription expiry
    elif sub.subscription_end and sub.subscription_end < now:
        if sub.grace_period_end and sub.grace_period_end > now:
            sub.status = "grace_period"
        else:
            sub.status = "expired"
        db.commit()

    is_valid = sub.status in ("active", "grace_period")
    sessions_remaining = max(0, sub.sessions_limit - sub.sessions_used) if sub.plan == "free_trial" else 999
    features = PLAN_FEATURES.get(sub.plan, PLAN_FEATURES["free_trial"])

    # Check for feature flag overrides
    flags = db.query(FeatureFlag).filter(FeatureFlag.plan == sub.plan).all()
    for flag in flags:
        features[flag.feature_key] = flag.is_enabled

    if not is_valid:
        msg = "Free trial expired. Upgrade to continue." if sub.plan == "free_trial" else "Subscription expired."
    elif sub.plan == "free_trial":
        msg = f"{sessions_remaining} sessions remaining in your free trial ({days_remaining} days left)"
    else:
        msg = f"Active {sub.plan} subscription"

    return LicenseValidation(
        is_valid=is_valid, plan=sub.plan, status=sub.status,
        sessions_remaining=sessions_remaining, days_remaining=days_remaining,
        features=features, message=msg)


@router.get("/subscription", response_model=SubscriptionResponse)
def get_subscription(user: User = Depends(get_current_user),
                     db: DbSession = Depends(get_db)):
    sub = db.query(Subscription).filter(Subscription.user_id == user.id).first()
    if not sub:
        raise Exception("No subscription found")
    return sub
