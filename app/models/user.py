from sqlalchemy import DateTime,String,func
from sqlalchemy.orm import mapped_column, Mapped
from app.db.session import Base
from app.models.enums import UserRole

class User(Base):
    __tablename__ = "users"

    id:Mapped[int] = mapped_column(primary_key= True)
    email:Mapped[str] = mapped_column(String(255), unique=True, index = True)
    name:Mapped[str] = mapped_column(String(255))
    created_at:Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now()
    )
    updated_at:Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        server_default= func.now(),
        onupdate= func.now(),
    )
    password_hash:Mapped[str] = mapped_column(
        String(255),
        nullable= True,
    )

    user_role: Mapped[UserRole] = mapped_column(
        String,
        default=UserRole.CUSTOMER,
        server_default=UserRole.CUSTOMER.value,
        nullable=False,
    )
