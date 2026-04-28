import uuid

from loguru import logger
from sqlalchemy import select

from app.core.security import hash_password
from app.db.session import AsyncSessionLocal
from app.models.user import User, UserRole

_ADMIN_EMAIL = "admin@hcmut.edu.vn"
_ADMIN_PASSWORD = "admin123"


async def bootstrap_admin() -> None:
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User).where(User.email == _ADMIN_EMAIL))
        if result.scalar_one_or_none():
            return

        admin = User(
            id=uuid.uuid4(),
            email=_ADMIN_EMAIL,
            hashed_password=hash_password(_ADMIN_PASSWORD),
            role=UserRole.admin,
        )
        db.add(admin)
        await db.commit()
        logger.info(f"✅ Admin bootstrapped — email: {_ADMIN_EMAIL} / password: {_ADMIN_PASSWORD}")
