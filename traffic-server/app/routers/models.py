from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select
from app.core.database import get_session
from app.models.model import Model, ModelCreate, ModelUpdate
from typing import List, Optional

router = APIRouter()


@router.get("/", response_model=List[Model])
async def get_models(
    skip: int = Query(0, ge=0, description="Số record bỏ qua"),
    limit: int = Query(100, ge=1, le=1000, description="Số record tối đa trả về"),
    model_type: Optional[str] = Query(None, description="Lọc theo loại mô hình"),
    session: Session = Depends(get_session)
):
    """
    Lấy danh sách các mô hình AI.
    
    Args:
        skip: Số record bỏ qua (pagination)
        limit: Số record tối đa trả về
        model_type: Lọc theo loại mô hình (optional)
        session: Database session
    
    Returns:
        List[Model]: Danh sách mô hình
    """
    query = select(Model)
    
    # Apply filter
    if model_type:
        query = query.where(Model.model_type == model_type)
    
    # Apply pagination
    models = session.exec(query.offset(skip).limit(limit)).all()
    
    return models


@router.get("/{model_id}", response_model=Model)
async def get_model_by_id(
    model_id: int,
    session: Session = Depends(get_session)
):
    """
    Lấy chi tiết một mô hình theo ID.
    
    Args:
        model_id: ID của mô hình
        session: Database session
    
    Returns:
        Model: Chi tiết mô hình
    """
    model = session.exec(
        select(Model).where(Model.model_id == model_id)
    ).first()
    
    if not model:
        raise HTTPException(status_code=404, detail="Không tìm thấy mô hình")
    
    return model


@router.post("/", response_model=Model)
async def create_model(
    model_data: ModelCreate,
    session: Session = Depends(get_session)
):
    """
    Tạo mô hình mới.
    
    Args:
        model_data: Dữ liệu mô hình
        session: Database session
    
    Returns:
        Model: Mô hình vừa tạo
    """
    # Validate model_type
    valid_types = ['vehicle', 'plate', 'ocr', 'traffic_light', 'violation']
    if model_data.model_type not in valid_types:
        raise HTTPException(
            status_code=400,
            detail=f"Loại mô hình phải là một trong: {', '.join(valid_types)}"
        )
    
    # Validate confidence_threshold
    if not (0 <= model_data.confidence_threshold <= 1):
        raise HTTPException(
            status_code=400,
            detail="Ngưỡng confidence phải từ 0 đến 1"
        )
    
    # Tạo mới
    model = Model(**model_data.model_dump())
    session.add(model)
    session.commit()
    session.refresh(model)
    
    return model


@router.put("/{model_id}", response_model=Model)
async def update_model(
    model_id: int,
    model_data: ModelUpdate,
    session: Session = Depends(get_session)
):
    """
    Cập nhật thông tin mô hình.
    
    Args:
        model_id: ID của mô hình
        model_data: Dữ liệu cập nhật
        session: Database session
    
    Returns:
        Model: Mô hình sau khi cập nhật
    """
    model = session.exec(
        select(Model).where(Model.model_id == model_id)
    ).first()
    
    if not model:
        raise HTTPException(status_code=404, detail="Không tìm thấy mô hình")
    
    # Validate model_type
    valid_types = ['vehicle', 'plate', 'ocr', 'traffic_light', 'violation']
    if model_data.model_type not in valid_types:
        raise HTTPException(
            status_code=400,
            detail=f"Loại mô hình phải là một trong: {', '.join(valid_types)}"
        )
    
    # Validate confidence_threshold
    if not (0 <= model_data.confidence_threshold <= 1):
        raise HTTPException(
            status_code=400,
            detail="Ngưỡng confidence phải từ 0 đến 1"
        )
    
    # Cập nhật
    model.name = model_data.name
    model.model_type = model_data.model_type
    model.file_path = model_data.file_path
    model.version = model_data.version
    model.framework = model_data.framework
    model.confidence_threshold = model_data.confidence_threshold
    model.description = model_data.description
    
    session.add(model)
    session.commit()
    session.refresh(model)
    
    return model


@router.delete("/{model_id}")
async def delete_model(
    model_id: int,
    session: Session = Depends(get_session)
):
    """
    Xóa mô hình.
    
    Lưu ý: Không nên xóa nếu có vi phạm đang tham chiếu đến mô hình này.
    
    Args:
        model_id: ID của mô hình
        session: Database session
    
    Returns:
        dict: Thông báo xác nhận
    """
    model = session.exec(
        select(Model).where(Model.model_id == model_id)
    ).first()
    
    if not model:
        raise HTTPException(status_code=404, detail="Không tìm thấy mô hình")
    
    # Kiểm tra xem có vi phạm nào đang sử dụng mô hình này không
    from app.models.violation import Violation
    violations_count = len(session.exec(
        select(Violation).where(Violation.model_id == model_id)
    ).all())
    
    if violations_count > 0:
        raise HTTPException(
            status_code=400,
            detail=f"Không thể xóa mô hình này vì có {violations_count} vi phạm đang sử dụng"
        )
    
    session.delete(model)
    session.commit()
    
    return {
        "message": "Đã xóa mô hình thành công",
        "model_id": model_id
    }
