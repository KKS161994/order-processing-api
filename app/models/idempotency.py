from sqlalchemy.orm import Mapped,mapped_column
from sqlalchemy import String, Numeric, DateTime, func
from app.db.session import Base
from datetime import datetime
class IdempotencyKey(Base):
    __tablename__ = "idempotency_keys"

    key:Mapped[str] = mapped_column(String(255), primary_key=True)
    user_id:Mapped[int] = mapped_column(index=True)
    endpoint:Mapped[str] = mapped_column(String(255))
    response_status:Mapped[int] = mapped_column()
    response_body:Mapped[str] = mapped_column()
    created_at:Mapped[datetime] = mapped_column(
        DateTime(timezone=True),server_default=func.now()
    )
