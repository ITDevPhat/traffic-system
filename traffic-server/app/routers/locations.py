from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select
from app.core.database import get_session
from app.models.location import Location, LocationCreate, LocationUpdate
from typing import List, Optional

router = APIRouter()


@router.get("/", response_model=List[Location])
async def get_locations(
    skip: int = Query(0, ge=0, description="Số record bỏ qua"),
    limit: int = Query(100, ge=1, le=1000, description="Số record tối đa trả về"),
    session: Session = Depends(get_session)
):
    """
    Lấy danh sách các vị trí.
    
    Args:
        skip: Số record bỏ qua (pagination)
        limit: Số record tối đa trả về
        session: Database session
    
    Returns:
        List[Location]: Danh sách vị trí
    """
    query = select(Location)
    locations = session.exec(query.offset(skip).limit(limit)).all()
    return locations


@router.get("/{location_id}", response_model=Location)
async def get_location_by_id(
    location_id: int,
    session: Session = Depends(get_session)
):
    """
    Lấy chi tiết một vị trí theo ID.
    
    Args:
        location_id: ID của vị trí
        session: Database session
    
    Returns:
        Location: Chi tiết vị trí
    """
    location = session.exec(
        select(Location).where(Location.location_id == location_id)
    ).first()
    
    if not location:
        raise HTTPException(status_code=404, detail="Không tìm thấy vị trí")
    
    return location


@router.post("/", response_model=Location)
async def create_location(
    location_data: LocationCreate,
    session: Session = Depends(get_session)
):
    """
    Tạo vị trí mới.
    
    Args:
        location_data: Dữ liệu vị trí
        session: Database session
    
    Returns:
        Location: Vị trí vừa tạo
    """
    # Kiểm tra trùng tọa độ
    if location_data.latitude and location_data.longitude:
        existing = session.exec(
            select(Location).where(
                Location.latitude == location_data.latitude,
                Location.longitude == location_data.longitude
            )
        ).first()
        
        if existing:
            raise HTTPException(
                status_code=400,
                detail="Vị trí với tọa độ này đã tồn tại"
            )
    
    # Tạo mới
    location = Location(**location_data.model_dump())
    session.add(location)
    session.commit()
    session.refresh(location)
    
    return location


@router.put("/{location_id}", response_model=Location)
async def update_location(
    location_id: int,
    location_data: LocationUpdate,
    session: Session = Depends(get_session)
):
    """
    Cập nhật thông tin vị trí.
    
    Args:
        location_id: ID của vị trí
        location_data: Dữ liệu cập nhật
        session: Database session
    
    Returns:
        Location: Vị trí sau khi cập nhật
    """
    location = session.exec(
        select(Location).where(Location.location_id == location_id)
    ).first()
    
    if not location:
        raise HTTPException(status_code=404, detail="Không tìm thấy vị trí")
    
    # Kiểm tra trùng tọa độ (nếu thay đổi)
    if location_data.latitude and location_data.longitude:
        if (location.latitude != location_data.latitude or 
            location.longitude != location_data.longitude):
            existing = session.exec(
                select(Location).where(
                    Location.latitude == location_data.latitude,
                    Location.longitude == location_data.longitude,
                    Location.location_id != location_id
                )
            ).first()
            
            if existing:
                raise HTTPException(
                    status_code=400,
                    detail="Vị trí với tọa độ này đã tồn tại"
                )
    
    # Cập nhật
    location.name = location_data.name
    location.address = location_data.address
    location.latitude = location_data.latitude
    location.longitude = location_data.longitude
    location.description = location_data.description
    
    session.add(location)
    session.commit()
    session.refresh(location)
    
    return location


@router.delete("/{location_id}")
async def delete_location(
    location_id: int,
    session: Session = Depends(get_session)
):
    """
    Xóa vị trí.
    
    Args:
        location_id: ID của vị trí
        session: Database session
    
    Returns:
        dict: Thông báo xác nhận
    """
    location = session.exec(
        select(Location).where(Location.location_id == location_id)
    ).first()
    
    if not location:
        raise HTTPException(status_code=404, detail="Không tìm thấy vị trí")
    
    # Kiểm tra xem có camera nào đang sử dụng vị trí này không
    from app.models.camera import Camera
    cameras_count = len(session.exec(
        select(Camera).where(Camera.location_id == location_id)
    ).all())
    
    if cameras_count > 0:
        raise HTTPException(
            status_code=400,
            detail=f"Không thể xóa vị trí này vì có {cameras_count} camera đang sử dụng"
        )
    
    session.delete(location)
    session.commit()
    
    return {
        "message": "Đã xóa vị trí thành công",
        "location_id": location_id
    }
