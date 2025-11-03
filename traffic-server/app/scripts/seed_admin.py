"""
Script để tạo admin user mặc định

Usage:
    python -m app.scripts.seed_admin
    
hoặc từ thư mục traffic-server:
    cd traffic-server
    python -m app.scripts.seed_admin
"""

from sqlmodel import Session, select
from app.models.user import User
from app.core.database import engine
from app.routers.auth import hash_password
from datetime import datetime, timezone


def create_admin_user():
    """
    Tạo admin user mặc định nếu chưa tồn tại
    
    Credentials:
        - Username: admin
        - Password: Admin@123
        - Role: admin
    """
    with Session(engine) as session:
        # Kiểm tra xem admin đã tồn tại chưa
        stmt = select(User).where(User.username == "admin")
        existing_admin = session.exec(stmt).first()
        
        if existing_admin:
            print("⚙️  Admin user already exists!")
            print(f"   Username: {existing_admin.username}")
            print(f"   Email: {existing_admin.email or 'N/A'}")
            print(f"   Role: {existing_admin.role}")
            print(f"   Created at: {existing_admin.created_at}")
            return
        
        # Tạo admin user mới
        admin = User(
            username="admin",
            full_name="Administrator",
            email="admin@traffic-system.com",
            password_hash=hash_password("Admin@123"),
            role="admin",
            created_at=datetime.now(timezone.utc)
        )
        
        session.add(admin)
        session.commit()
        session.refresh(admin)
        
        print("✅ Admin user created successfully!")
        print(f"   Username: {admin.username}")
        print(f"   Password: Admin@123")
        print(f"   Email: {admin.email}")
        print(f"   Role: {admin.role}")
        print(f"   User ID: {admin.user_id}")
        print("\n🔐 Please change the password after first login!")


def create_demo_user():
    """
    Tạo demo user cho testing
    
    Credentials:
        - Username: demo
        - Password: Demo@123
        - Role: user
    """
    with Session(engine) as session:
        # Kiểm tra xem demo user đã tồn tại chưa
        stmt = select(User).where(User.username == "demo")
        existing_demo = session.exec(stmt).first()
        
        if existing_demo:
            print("\n⚙️  Demo user already exists!")
            return
        
        # Tạo demo user
        demo = User(
            username="demo",
            full_name="Demo User",
            email="demo@traffic-system.com",
            password_hash=hash_password("Demo@123"),
            role="user",
            created_at=datetime.now(timezone.utc)
        )
        
        session.add(demo)
        session.commit()
        session.refresh(demo)
        
        print("\n✅ Demo user created successfully!")
        print(f"   Username: {demo.username}")
        print(f"   Password: Demo@123")
        print(f"   Email: {demo.email}")
        print(f"   Role: {demo.role}")


if __name__ == "__main__":
    # Set UTF-8 encoding for Windows console
    import sys
    if sys.platform == 'win32':
        try:
            import io
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
        except:
            pass
    
    print("🚀 Seeding database with default users...\n")
    print("=" * 50)
    
    try:
        # Tạo admin user
        create_admin_user()
        
        # Tạo demo user (optional)
        create_demo_user()
        
        print("\n" + "=" * 50)
        print("🎉 Database seeding completed!")
        
    except Exception as e:
        print(f"\n❌ Error seeding database: {e}")
        import traceback
        traceback.print_exc()

