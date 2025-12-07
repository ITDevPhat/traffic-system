from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from app.core.database import get_session
from app.models.violation_type import ViolationType, ViolationTypeCreate, ViolationTypeUpdate
from typing import List

router = APIRouter()


@router.get("/", response_model=List[ViolationType])
async def get_violation_types(
    session: Session = Depends(get_session)
):
    """
    Lấy danh sách tất cả loại vi phạm.
    
    Returns:
        List[ViolationType]: Danh sách loại vi phạm
    """
    violation_types = session.exec(select(ViolationType)).all()
    return violation_types


@router.get("/{code}", response_model=ViolationType)
async def get_violation_type_by_code(
    code: str,
    session: Session = Depends(get_session)
):
    """
    Lấy chi tiết một loại vi phạm theo mã.
    
    Args:
        code: Mã loại vi phạm
        session: Database session
    
    Returns:
        ViolationType: Chi tiết loại vi phạm
    """
    violation_type = session.exec(
        select(ViolationType).where(ViolationType.violation_type_code == code)
    ).first()
    
    if not violation_type:
        raise HTTPException(status_code=404, detail="Không tìm thấy loại vi phạm")
    
    return violation_type


@router.post("/", response_model=ViolationType)
async def create_violation_type(
    violation_type_data: ViolationTypeCreate,
    session: Session = Depends(get_session)
):
    """
    Tạo loại vi phạm mới.
    
    Args:
        violation_type_data: Dữ liệu loại vi phạm
        session: Database session
    
    Returns:
        ViolationType: Loại vi phạm vừa tạo
    """
    # Kiểm tra xem mã đã tồn tại chưa
    existing = session.exec(
        select(ViolationType).where(
            ViolationType.violation_type_code == violation_type_data.violation_type_code
        )
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=400, 
            detail=f"Mã loại vi phạm '{violation_type_data.violation_type_code}' đã tồn tại"
        )
    
    # Validate severity
    if violation_type_data.severity not in ['low', 'medium', 'high']:
        raise HTTPException(
            status_code=400,
            detail="Mức độ phải là 'low', 'medium' hoặc 'high'"
        )
    
    # Tạo mới
    violation_type = ViolationType(**violation_type_data.model_dump())
    session.add(violation_type)
    session.commit()
    session.refresh(violation_type)
    
    return violation_type


@router.put("/{code}", response_model=ViolationType)
async def update_violation_type(
    code: str,
    violation_type_data: ViolationTypeUpdate,
    session: Session = Depends(get_session)
):
    """
    Cập nhật thông tin loại vi phạm.
    
    Args:
        code: Mã loại vi phạm
        violation_type_data: Dữ liệu cập nhật
        session: Database session
    
    Returns:
        ViolationType: Loại vi phạm sau khi cập nhật
    """
    violation_type = session.exec(
        select(ViolationType).where(ViolationType.violation_type_code == code)
    ).first()
    
    if not violation_type:
        raise HTTPException(status_code=404, detail="Không tìm thấy loại vi phạm")
    
    # Validate severity
    if violation_type_data.severity not in ['low', 'medium', 'high']:
        raise HTTPException(
            status_code=400,
            detail="Mức độ phải là 'low', 'medium' hoặc 'high'"
        )
    
    # Cập nhật
    violation_type.description = violation_type_data.description
    violation_type.fine_amount = violation_type_data.fine_amount
    violation_type.severity = violation_type_data.severity
    
    session.add(violation_type)
    session.commit()
    session.refresh(violation_type)
    
    return violation_type


@router.delete("/{code}")
async def delete_violation_type(
    code: str,
    session: Session = Depends(get_session)
):
    """
    Xóa loại vi phạm.
    
    Lưu ý: Không nên xóa nếu có vi phạm đang tham chiếu đến loại này.
    
    Args:
        code: Mã loại vi phạm
        session: Database session
    
    Returns:
        dict: Thông báo xác nhận
    """
    violation_type = session.exec(
        select(ViolationType).where(ViolationType.violation_type_code == code)
    ).first()
    
    if not violation_type:
        raise HTTPException(status_code=404, detail="Không tìm thấy loại vi phạm")
    
    # Kiểm tra xem có vi phạm nào đang sử dụng loại này không
    from app.models.violation import Violation
    violations_count = len(session.exec(
        select(Violation).where(Violation.violation_type_code == code)
    ).all())
    
    if violations_count > 0:
        raise HTTPException(
            status_code=400,
            detail=f"Không thể xóa loại vi phạm này vì có {violations_count} vi phạm đang sử dụng"
        )
    
    session.delete(violation_type)
    session.commit()
    
    return {
        "message": "Đã xóa loại vi phạm thành công",
        "violation_type_code": code
    }
