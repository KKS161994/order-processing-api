from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import ForeignKey, DateTime, String, Numeric, func
from enum import Enum
from app.db.session import Base
from datetime import datetime

class PaymentStatus(str,Enum):
    PENDING = "pending"
    SUCCEEDED = "succeeded"
    FAILED = "failed"

class Payment(Base):
    __tablename__ = "payment"

    id:Mapped[int] = mapped_column(primary_key=True)
    order_id:Mapped[int] = mapped_column(ForeignKey("order.id"),index=True)
    amount:Mapped[int] = mapped_column(Numeric(10,2))
    currency:Mapped[str] = mapped_column(String(3), default="USD")
    status:Mapped[str] = mapped_column(String(20),default=PaymentStatus.PENDING)
    external_payment_id:Mapped[str | None] = mapped_column(String(255), index=True, nullable=True)

    created_at:Mapped[datetime] = mapped_column(DateTime(timezone=True),server_default=func.now())