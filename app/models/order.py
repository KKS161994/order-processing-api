from datetime import datetime
from decimal import Decimal
from enum import Enum
from sqlalchemy import ForeignKey, String, Numeric, func,DateTime
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base
class OrderStatus(str,Enum):
    PENDING = "pending"
    PAID = "paid"
    CANCELLED = "cancelled"
    FAILED = "failed"


class Order(Base):
    __tablename__ = "order"

    id:Mapped[int] = mapped_column(primary_key=True)
    user_id:Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    amount:Mapped[int] = mapped_column(Numeric(10,2))
    currency:Mapped[str] = mapped_column(String(3), default= "USD")
    status:Mapped[str] = mapped_column(String(20), default=OrderStatus.PENDING)
    version:Mapped[int] = mapped_column(default = 1)
    created_at:Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default = func.now(),
    )
    updated_at = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate = func.now(),
    )