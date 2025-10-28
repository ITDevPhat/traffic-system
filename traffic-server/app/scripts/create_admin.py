import os
from sqlmodel import Session, select

from app.core.database import engine
from app.models import User
from app.routers.auth import hash_password


def run():
    username = os.getenv("ADMIN_USERNAME", "admin")
    password = os.getenv("ADMIN_PASSWORD", None)
    if not password:
        print("Please set ADMIN_PASSWORD env for initial admin creation")
        return

    with Session(engine) as session:
        existing = session.exec(select(User).where(User.username == username)).first()
        if existing:
            print("Admin already exists")
            return
        user = User(
            username=username,
            password_hash=hash_password(password),
            role="admin"
        )
        session.add(user)
        session.commit()
        print(f"Admin user '{username}' created")


if __name__ == "__main__":
    run()

