"""
Colour Routes — Photo upload, colour extraction, and matching
"""
import os
import uuid
import io
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session as DbSession
import numpy as np
from PIL import Image
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from models import (User, Session, SessionPhoto, ComparisonCase, get_db)
from schemas import ColourMatchResult, LabColour, PhotoResponse
from services.auth_service import get_current_user
from services.colour_engine import (
    rgb_to_lab, lab_to_hex, ciede2000, delta_e_to_match_percent,
    get_interpretation, get_recommendation, apply_lighting_correction,
    extract_dominant_colour_from_roi, find_nearest_pantones
)

router = APIRouter(prefix="/api", tags=["Colour Science"])

UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)


@router.post("/sessions/{session_id}/source", response_model=PhotoResponse)
async def upload_source_photo(
    session_id: str,
    file: UploadFile = File(...),
    lighting_condition: str = Form("indoor"),
    roi_x: int = Form(None), roi_y: int = Form(None),
    roi_width: int = Form(None), roi_height: int = Form(None),
    photo_order: int = Form(1),
    user: User = Depends(get_current_user),
    db: DbSession = Depends(get_db),
):
    session = db.query(Session).filter(Session.id == session_id, Session.user_id == user.id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Save file locally
    ext = os.path.splitext(file.filename)[1] if file.filename else ".jpg"
    filename = f"{uuid.uuid4()}{ext}"
    filepath = os.path.join(UPLOAD_DIR, filename)
    content = await file.read()
    with open(filepath, "wb") as f:
        f.write(content)

    # Extract colour
    img = Image.open(io.BytesIO(content)).convert("RGB")
    img_array = np.array(img)
    roi = None
    if all(v is not None for v in [roi_x, roi_y, roi_width, roi_height]):
        roi = {"x": roi_x, "y": roi_y, "width": roi_width, "height": roi_height}
    r, g, b = extract_dominant_colour_from_roi(img_array, roi)
    raw_L, raw_a, raw_b = rgb_to_lab(r, g, b)
    corr_L, corr_a, corr_b = apply_lighting_correction(raw_L, raw_a, raw_b, lighting_condition)

    photo = SessionPhoto(
        session_id=session_id, photo_type="source", local_path=filepath,
        lighting_condition=lighting_condition,
        roi_x=roi_x, roi_y=roi_y, roi_width=roi_width, roi_height=roi_height,
        raw_lab_l=round(raw_L, 2), raw_lab_a=round(raw_a, 2), raw_lab_b=round(raw_b, 2),
        corrected_lab_l=round(corr_L, 2), corrected_lab_a=round(corr_a, 2), corrected_lab_b=round(corr_b, 2),
        photo_order=photo_order)
    db.add(photo)

    # Update session source colour (average of all source photos)
    db.flush()
    source_photos = db.query(SessionPhoto).filter(
        SessionPhoto.session_id == session_id, SessionPhoto.photo_type == "source").all()
    avg_L = sum(p.corrected_lab_l for p in source_photos) / len(source_photos)
    avg_a = sum(p.corrected_lab_a for p in source_photos) / len(source_photos)
    avg_b = sum(p.corrected_lab_b for p in source_photos) / len(source_photos)
    session.source_lab_l = round(avg_L, 2)
    session.source_lab_a = round(avg_a, 2)
    session.source_lab_b = round(avg_b, 2)
    session.source_hex = lab_to_hex(avg_L, avg_a, avg_b)

    # Find nearest Pantones
    pantones = find_nearest_pantones(avg_L, avg_a, avg_b, 3)
    if len(pantones) >= 1: session.nearest_pantone_1 = f"{pantones[0][0]} ({pantones[0][1]})"
    if len(pantones) >= 2: session.nearest_pantone_2 = f"{pantones[1][0]} ({pantones[1][1]})"
    if len(pantones) >= 3: session.nearest_pantone_3 = f"{pantones[2][0]} ({pantones[2][1]})"

    db.commit()
    db.refresh(photo)
    return photo


@router.post("/sessions/{session_id}/cases/{case_id}/photo", response_model=PhotoResponse)
async def upload_case_photo(
    session_id: str, case_id: str,
    file: UploadFile = File(...),
    lighting_condition: str = Form("indoor"),
    roi_x: int = Form(None), roi_y: int = Form(None),
    roi_width: int = Form(None), roi_height: int = Form(None),
    photo_order: int = Form(1),
    user: User = Depends(get_current_user),
    db: DbSession = Depends(get_db),
):
    session = db.query(Session).filter(Session.id == session_id, Session.user_id == user.id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    case = db.query(ComparisonCase).filter(ComparisonCase.id == case_id, ComparisonCase.session_id == session_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    ext = os.path.splitext(file.filename)[1] if file.filename else ".jpg"
    filename = f"{uuid.uuid4()}{ext}"
    filepath = os.path.join(UPLOAD_DIR, filename)
    content = await file.read()
    with open(filepath, "wb") as f:
        f.write(content)

    img = Image.open(io.BytesIO(content)).convert("RGB")
    img_array = np.array(img)
    roi = None
    if all(v is not None for v in [roi_x, roi_y, roi_width, roi_height]):
        roi = {"x": roi_x, "y": roi_y, "width": roi_width, "height": roi_height}
    r, g, b = extract_dominant_colour_from_roi(img_array, roi)
    raw_L, raw_a, raw_b = rgb_to_lab(r, g, b)
    corr_L, corr_a, corr_b = apply_lighting_correction(raw_L, raw_a, raw_b, lighting_condition)

    photo = SessionPhoto(
        session_id=session_id, photo_type="comparison", case_id=case_id,
        local_path=filepath, lighting_condition=lighting_condition,
        roi_x=roi_x, roi_y=roi_y, roi_width=roi_width, roi_height=roi_height,
        raw_lab_l=round(raw_L, 2), raw_lab_a=round(raw_a, 2), raw_lab_b=round(raw_b, 2),
        corrected_lab_l=round(corr_L, 2), corrected_lab_a=round(corr_a, 2), corrected_lab_b=round(corr_b, 2),
        photo_order=photo_order)
    db.add(photo)
    db.flush()

    # Update case average colour
    case_photos = db.query(SessionPhoto).filter(
        SessionPhoto.case_id == case_id, SessionPhoto.photo_type == "comparison").all()
    case.avg_lab_l = round(sum(p.corrected_lab_l for p in case_photos) / len(case_photos), 2)
    case.avg_lab_a = round(sum(p.corrected_lab_a for p in case_photos) / len(case_photos), 2)
    case.avg_lab_b = round(sum(p.corrected_lab_b for p in case_photos) / len(case_photos), 2)
    case.case_hex = lab_to_hex(case.avg_lab_l, case.avg_lab_a, case.avg_lab_b)

    db.commit()
    db.refresh(photo)
    return photo


@router.post("/sessions/{session_id}/compare", response_model=ColourMatchResult)
def run_comparison(session_id: str, case_id: str = None,
                   user: User = Depends(get_current_user),
                   db: DbSession = Depends(get_db)):
    session = db.query(Session).filter(Session.id == session_id, Session.user_id == user.id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if not session.source_lab_l:
        raise HTTPException(status_code=400, detail="No source colour captured yet")

    cases = [db.query(ComparisonCase).get(case_id)] if case_id else session.cases
    if not cases or cases[0] is None:
        raise HTTPException(status_code=400, detail="No comparison cases found")

    best_match = 0
    last_result = None
    source_lab = (session.source_lab_l, session.source_lab_a, session.source_lab_b)

    for case in cases:
        if not case.avg_lab_l:
            continue
        case_lab = (case.avg_lab_l, case.avg_lab_a, case.avg_lab_b)
        de = ciede2000(source_lab, case_lab)
        mp = delta_e_to_match_percent(de)
        dl = case.avg_lab_l - session.source_lab_l
        da = case.avg_lab_a - session.source_lab_a
        db_val = case.avg_lab_b - session.source_lab_b
        interp = get_interpretation(mp)
        rec = get_recommendation(dl, da, db_val, interp)

        case.delta_e = round(de, 2)
        case.match_percent = round(mp, 1)
        case.delta_l = round(dl, 2)
        case.delta_a = round(da, 2)
        case.delta_b = round(db_val, 2)
        case.interpretation = interp
        case.recommendation = rec
        if mp > best_match:
            best_match = mp

        last_result = ColourMatchResult(
            delta_e=round(de, 2), match_percent=round(mp, 1),
            delta_l=round(dl, 2), delta_a=round(da, 2), delta_b=round(db_val, 2),
            interpretation=interp, recommendation=rec,
            source_lab=LabColour(L=source_lab[0], a=source_lab[1], b=source_lab[2]),
            case_lab=LabColour(L=case_lab[0], a=case_lab[1], b=case_lab[2]))

    session.best_match_percent = round(best_match, 1)
    session.status = "completed"
    db.commit()

    if not last_result:
        raise HTTPException(status_code=400, detail="No valid case data to compare")
    return last_result
