"""
Script để seed dữ liệu mẫu cho bảng violation_types
Chạy: python -m app.scripts.seed_violation_types
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from sqlmodel import Session, select
from app.core.database import engine
from app.models.violation_type import ViolationType


def seed_violation_types():
    """Thêm các loại vi phạm mẫu vào database"""
    
    violation_types_data = [
        {
            "violation_type_code": "RED_LIGHT",
            "description": "Vượt đèn đỏ - Phương tiện di chuyển qua vạch dừng khi đèn tín hiệu màu đỏ",
            "fine_amount": 800000,
            "severity": "high"
        },
        {
            "violation_type_code": "WRONG_LANE",
            "description": "Đi sai làn đường - Phương tiện di chuyển không đúng làn quy định",
            "fine_amount": 400000,
            "severity": "medium"
        },
        {
            "violation_type_code": "SPEEDING",
            "description": "Vượt quá tốc độ cho phép - Phương tiện di chuyển với tốc độ vượt mức quy định",
            "fine_amount": 600000,
            "severity": "high"
        },
        {
            "violation_type_code": "NO_HELMET",
            "description": "Không đội mũ bảo hiểm - Người điều khiển xe máy không đội mũ bảo hiểm",
            "fine_amount": 200000,
            "severity": "medium"
        },
        {
            "violation_type_code": "STOP_LINE",
            "description": "Vượt vạch dừng - Phương tiện dừng vượt quá vạch dừng khi có tín hiệu dừng",
            "fine_amount": 300000,
            "severity": "low"
        },
        {
            "violation_type_code": "ILLEGAL_TURN",
            "description": "Rẽ trái/phải không đúng quy định - Phương tiện rẽ tại nơi cấm hoặc không có tín hiệu",
            "fine_amount": 500000,
            "severity": "medium"
        },
        {
            "violation_type_code": "NO_PARKING",
            "description": "Đỗ xe sai quy định - Phương tiện đỗ tại khu vực cấm đỗ",
            "fine_amount": 300000,
            "severity": "low"
        },
        {
            "violation_type_code": "PHONE_USE",
            "description": "Sử dụng điện thoại khi lái xe - Người điều khiển sử dụng điện thoại trong khi lái xe",
            "fine_amount": 400000,
            "severity": "medium"
        }
    ]
    
    with Session(engine) as session:
        print("🌱 Bắt đầu seed dữ liệu violation_types...")
        
        for vt_data in violation_types_data:
            # Kiểm tra xem đã tồn tại chưa
            existing = session.exec(
                select(ViolationType).where(
                    ViolationType.violation_type_code == vt_data["violation_type_code"]
                )
            ).first()
            
            if existing:
                print(f"⏭️  Bỏ qua '{vt_data['violation_type_code']}' - đã tồn tại")
                continue
            
            # Tạo mới
            violation_type = ViolationType(**vt_data)
            session.add(violation_type)
            print(f"✅ Đã thêm '{vt_data['violation_type_code']}' - {vt_data['description'][:50]}...")
        
        session.commit()
        print("\n🎉 Hoàn thành seed dữ liệu violation_types!")
        
        # Hiển thị tổng số
        total = len(session.exec(select(ViolationType)).all())
        print(f"📊 Tổng số loại vi phạm trong database: {total}")


if __name__ == "__main__":
    seed_violation_types()
