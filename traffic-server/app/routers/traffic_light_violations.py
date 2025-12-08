import logging

from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.core.database import get_session
from app.models.violation import Violation
from app.schemas.traffic_light_violation import TrafficLightViolationIn
from app.services.traffic_light_violation_service import (
    create_traffic_light_violation,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/traffic-light", tags=["Traffic Light Violations"])


@router.post("/violations", response_model=Violation)
def ingest_traffic_light_violation(
    payload: TrafficLightViolationIn, session: Session = Depends(get_session)
):
    """Ingest a traffic-light violation from the realtime pipeline."""

    violation = create_traffic_light_violation(payload, session)
    logger.info(
        "[TL-VIOLATION][API] Created violation_id=%s camera=%s type=%s",
        violation.violation_id,
        payload.camera_name or payload.camera_id,
        violation.violation_type_code,
    )
    return violation
