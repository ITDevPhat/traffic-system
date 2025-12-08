import json
import logging
from datetime import datetime
from typing import Optional

from sqlmodel import Session

from app.core.database import engine
from app.models.bbox import BBox
from app.models.violation import Violation
from app.schemas.traffic_light_violation import TrafficLightViolationIn

logger = logging.getLogger(__name__)


def _resolve_violation_type_code(
    requested_code: Optional[str], label: Optional[str]
) -> str:
    """Resolve violation_type_code with bike/car defaults."""

    if requested_code:
        # Normalize engine-specific codes back to canonical names when needed
        if requested_code in {"RED_LIGHT_RUN", "RED_LIGHT_STOPLINE"}:
            return "RED_LIGHT"
        return requested_code

    if label and label.lower() == "bike":
        return "BIKE_RED_LIGHT"

    if label and label.lower() == "car":
        return "CAR_RED_LIGHT"

    # Default fallback
    return "CAR_RED_LIGHT"


def create_traffic_light_violation(
    payload: TrafficLightViolationIn, session: Session
) -> Violation:
    """Persist a traffic-light violation with optional bbox evidence."""

    timestamp = payload.timestamp or datetime.utcnow()
    violation_type_code = _resolve_violation_type_code(
        payload.violation_type_code, payload.label
    )

    evidence_img = None
    if payload.evidence_img_raw or payload.evidence_img_with_bbox:
        evidence_payload = {}
        if payload.evidence_img_with_bbox:
            evidence_payload["with_bbox"] = payload.evidence_img_with_bbox
        if payload.evidence_img_raw:
            evidence_payload["raw"] = payload.evidence_img_raw
        evidence_img = json.dumps(evidence_payload)

    violation = Violation(
        video_job_id=payload.video_job_id,
        vehicle_id=None,
        violation_type_code=violation_type_code,
        frame=payload.frame,
        timestamp=timestamp,
        roi_type=payload.roi_type or "traffic_light_stopline",
        evidence_img=evidence_img,
        plate=payload.plate or "UNKNOWN",
        confidence=payload.confidence,
        model_id=payload.model_id,
        verification_status="unverified",
        verified_source="ai",
    )

    session.add(violation)
    session.commit()
    session.refresh(violation)

    if payload.bbox:
        x1, y1, x2, y2 = payload.bbox
        bbox = BBox(
            violation_id=violation.violation_id,
            x1=float(x1),
            y1=float(y1),
            x2=float(x2),
            y2=float(y2),
            confidence=payload.confidence,
            label=payload.label,
        )
        session.add(bbox)
        session.commit()

    logger.info(
        "[TL-VIOLATION] Saved violation_id=%s type=%s frame=%s bbox=%s evidence=%s",
        violation.violation_id,
        violation.violation_type_code,
        violation.frame,
        payload.bbox,
        evidence_img,
    )

    return violation


def create_traffic_light_violation_with_session(
    payload: TrafficLightViolationIn,
) -> Violation:
    """Convenience wrapper to open a DB session for ingestion."""

    with Session(engine) as session:
        return create_traffic_light_violation(payload, session)
