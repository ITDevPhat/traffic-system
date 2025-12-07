from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select
from app.core.database import get_session
from app.models.camera import Camera, CameraCreate, CameraUpdate
from typing import List, Optional

router = APIRouter()


@router.get("/", response_model=List[Camera])
async def get_cameras(
    skip: int = Query(0, ge=0, description="Số record bỏ qua"),
    limit: int = Query(100, ge=1, le=1000, description="Số record tối đa trả về"),
    status: Optional[str] = Query(None, description="Lọc theo trạng thái"),
    location_id: Optional[int] = Query(None, description="Lọc theo vị trí"),
    session: Session = Depends(get_session)
):
    """
    Lấy danh sách các camera.
    
    Args:
        skip: Số record bỏ qua (pagination)
        limit: Số record tối đa trả về
        status: Lọc theo trạng thái (optional)
        location_id: Lọc theo vị trí (optional)
        session: Database session
    
    Returns:
        List[Camera]: Danh sách camera
    """
    query = select(Camera)
    
    # Apply filters
    if status:
        query = query.where(Camera.status == status)
    if location_id:
        query = query.where(Camera.location_id == location_id)
    
    cameras = session.exec(query.offset(skip).limit(limit)).all()
    return cameras


@router.get("/{camera_id}", response_model=Camera)
async def get_camera_by_id(
    camera_id: int,
    session: Session = Depends(get_session)
):
    """
    Lấy chi tiết một camera theo ID.
    
    Args:
        camera_id: ID của camera
        session: Database session
    
    Returns:
        Camera: Chi tiết camera
    """
    camera = session.exec(
        select(Camera).where(Camera.camera_id == camera_id)
    ).first()
    
    if not camera:
        raise HTTPException(status_code=404, detail="Không tìm thấy camera")
    
    return camera


@router.post("/", response_model=Camera)
async def create_camera(
    camera_data: CameraCreate,
    session: Session = Depends(get_session)
):
    """
    Tạo camera mới.
    
    Args:
        camera_data: Dữ liệu camera
        session: Database session
    
    Returns:
        Camera: Camera vừa tạo
    """
    # Validate status
    valid_statuses = ['active', 'inactive', 'maintenance']
    if camera_data.status not in valid_statuses:
        raise HTTPException(
            status_code=400,
            detail=f"Trạng thái phải là một trong: {', '.join(valid_statuses)}"
        )
    
    # Kiểm tra location_id tồn tại
    if camera_data.location_id:
        from app.models.location import Location
        location = session.exec(
            select(Location).where(Location.location_id == camera_data.location_id)
        ).first()
        if not location:
            raise HTTPException(status_code=404, detail="Không tìm thấy vị trí")
    
    # Tạo mới
    camera = Camera(**camera_data.model_dump())
    session.add(camera)
    session.commit()
    session.refresh(camera)
    
    return camera


@router.put("/{camera_id}", response_model=Camera)
async def update_camera(
    camera_id: int,
    camera_data: CameraUpdate,
    session: Session = Depends(get_session)
):
    """
    Cập nhật thông tin camera.
    
    Args:
        camera_id: ID của camera
        camera_data: Dữ liệu cập nhật
        session: Database session
    
    Returns:
        Camera: Camera sau khi cập nhật
    """
    camera = session.exec(
        select(Camera).where(Camera.camera_id == camera_id)
    ).first()
    
    if not camera:
        raise HTTPException(status_code=404, detail="Không tìm thấy camera")
    
    # Validate status
    valid_statuses = ['active', 'inactive', 'maintenance']
    if camera_data.status not in valid_statuses:
        raise HTTPException(
            status_code=400,
            detail=f"Trạng thái phải là một trong: {', '.join(valid_statuses)}"
        )
    
    # Kiểm tra location_id tồn tại
    if camera_data.location_id:
        from app.models.location import Location
        location = session.exec(
            select(Location).where(Location.location_id == camera_data.location_id)
        ).first()
        if not location:
            raise HTTPException(status_code=404, detail="Không tìm thấy vị trí")
    
    # Cập nhật
    camera.location_id = camera_data.location_id
    camera.name = camera_data.name
    camera.model = camera_data.model
    camera.ip_address = camera_data.ip_address
    camera.stream_url = camera_data.stream_url
    camera.status = camera_data.status
    camera.install_date = camera_data.install_date
    
    session.add(camera)
    session.commit()
    session.refresh(camera)
    
    return camera


@router.delete("/{camera_id}")
async def delete_camera(
    camera_id: int,
    session: Session = Depends(get_session)
):
    """
    Xóa camera.
    
    Args:
        camera_id: ID của camera
        session: Database session
    
    Returns:
        dict: Thông báo xác nhận
    """
    camera = session.exec(
        select(Camera).where(Camera.camera_id == camera_id)
    ).first()
    
    if not camera:
        raise HTTPException(status_code=404, detail="Không tìm thấy camera")
    
    # Kiểm tra xem có video job nào đang sử dụng camera này không
    from app.models.video_job import VideoJob
    videos_count = len(session.exec(
        select(VideoJob).where(VideoJob.camera_id == camera_id)
    ).all())
    
    if videos_count > 0:
        raise HTTPException(
            status_code=400,
            detail=f"Không thể xóa camera này vì có {videos_count} video đang sử dụng"
        )
    
    session.delete(camera)
    session.commit()
    
    return {
        "message": "Đã xóa camera thành công",
        "camera_id": camera_id
    }
