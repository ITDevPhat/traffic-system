from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select
from app.core.database import get_session
from app.models.violation import Violation
from typing import Optional

router = APIRouter()


@router.get("/")
async def get_violations(
    skip: int = Query(0, ge=0, description="Số record bỏ qua"),
    limit: int = Query(100, ge=1, le=1000, description="Số record tối đa trả về"),
    violation_type: Optional[str] = Query(None, description="Lọc theo loại vi phạm"),
    video_job_id: Optional[int] = Query(None, description="Lọc theo video job ID"),
    session: Session = Depends(get_session)
):
    """
    Lấy danh sách các vi phạm đã phát hiện.
    
    Args:
        skip: Số record bỏ qua (pagination)
        limit: Số record tối đa trả về
        violation_type: Lọc theo loại vi phạm (optional)
        video_job_id: Lọc theo video job ID (optional)
        session: Database session
    
    Returns:
        JSON chứa danh sách vi phạm và metadata
    """
    query = select(Violation)
    
    # Apply filters
    if violation_type:
        query = query.where(Violation.violation_type == violation_type)
    if video_job_id:
        query = query.where(Violation.video_job_id == video_job_id)
    
    # Get total count
    total = len(session.exec(query).all())
    
    # Apply pagination
    violations = session.exec(query.offset(skip).limit(limit)).all()
    
    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "violations": violations
    }


@router.get("/{violation_id}")
async def get_violation_detail(
    violation_id: int,
    session: Session = Depends(get_session)
):
    """
    Lấy chi tiết một vi phạm cụ thể.
    
    Args:
        violation_id: ID của vi phạm
        session: Database session
    
    Returns:
        JSON chứa chi tiết vi phạm
    """
    violation = session.exec(
        select(Violation).where(Violation.id == violation_id)
    ).first()
    
    if not violation:
        raise HTTPException(status_code=404, detail="Không tìm thấy vi phạm")
    
    return violation


@router.delete("/{violation_id}")
async def delete_violation(
    violation_id: int,
    session: Session = Depends(get_session)
):
    """
    Xóa một vi phạm.
    
    Args:
        violation_id: ID của vi phạm cần xóa
        session: Database session
    
    Returns:
        JSON xác nhận xóa thành công
    """
    violation = session.exec(
        select(Violation).where(Violation.id == violation_id)
    ).first()
    
    if not violation:
        raise HTTPException(status_code=404, detail="Không tìm thấy vi phạm")
    
    session.delete(violation)
    session.commit()
    
    return {"message": "Đã xóa vi phạm thành công", "violation_id": violation_id}

