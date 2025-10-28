import time
import logging
from sqlalchemy import text
from app.core.database import engine

logger = logging.getLogger("db_check")


def check_database_connection(retries: int = 10, delay: int = 3) -> bool:
    """
    Kiểm tra kết nối đến PostgreSQL khi khởi động server.
    
    Nếu thất bại, thử lại N lần (mặc định 10) mỗi 3s.
    Điều này đảm bảo database đã sẵn sàng trước khi FastAPI xử lý request.
    
    Args:
        retries: Số lần thử lại tối đa
        delay: Thời gian chờ giữa các lần thử (giây)
    
    Returns:
        True nếu kết nối thành công
    
    Raises:
        ConnectionError: Nếu không thể kết nối sau tất cả các lần thử
    """
    attempt = 1
    while attempt <= retries:
        try:
            with engine.connect() as connection:
                # Thử query đơn giản để test connection
                connection.execute(text("SELECT 1"))
                logger.info("✅ Database connection successful!")
                logger.info(f"📊 Connected to: {engine.url.database} on {engine.url.host}:{engine.url.port}")
                return True
        except Exception as e:
            logger.warning(
                f"❌ Database connection failed (attempt {attempt}/{retries}): {str(e)}"
            )
            if attempt < retries:
                logger.info(f"⏳ Retrying in {delay} seconds...")
                time.sleep(delay)
            attempt += 1

    # Nếu tất cả các lần thử đều thất bại
    logger.error("🚨 Unable to connect to the database after multiple retries. Exiting.")
    raise ConnectionError("Database connection failed after retries.")


def test_database_query() -> dict:
    """
    Test query để kiểm tra database có hoạt động không.
    
    Sử dụng cho API endpoint /api/db/status.
    
    Returns:
        Dictionary chứa thông tin kết nối và trạng thái
    """
    try:
        with engine.connect() as connection:
            result = connection.execute(text("SELECT version()"))
            version = result.fetchone()[0]
            
            # Kiểm tra số bảng hiện có
            tables_result = connection.execute(text("""
                SELECT COUNT(*) 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
            """))
            table_count = tables_result.fetchone()[0]
            
            return {
                "status": "ok",
                "connected": True,
                "database": str(engine.url.database),
                "host": str(engine.url.host),
                "port": engine.url.port,
                "postgres_version": version,
                "tables_count": table_count
            }
    except Exception as e:
        logger.error(f"Database test query failed: {str(e)}")
        return {
            "status": "error",
            "connected": False,
            "error": str(e)
        }

