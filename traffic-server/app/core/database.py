from sqlmodel import create_engine, Session, SQLModel
from app.core.config import settings

# Tạo engine kết nối đến PostgreSQL
engine = create_engine(settings.DATABASE_URL, echo=True)


def get_session():
    """
    Dependency để lấy database session.
    
    Sử dụng trong FastAPI route với Depends(get_session).
    """
    with Session(engine) as session:
        yield session


def create_db_and_tables():
    """
    Tạo tất cả các bảng trong database dựa trên SQLModel models.
    
    Gọi hàm này khi khởi động ứng dụng.
    """
    SQLModel.metadata.create_all(engine)

