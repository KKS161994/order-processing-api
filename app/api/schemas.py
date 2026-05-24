from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, EmailStr, Field

class UserCreate(BaseModel):
    email: EmailStr
    name:str = Field(min_length= 1, max_length=255)

class UserResponse(BaseModel):
    id: int
    email: str
    name: str
    created_at: datetime

    class Config:
        from_attributes = True

class OrderCreate(BaseModel):
    user_id:int
    amount: Decimal = Field(gt=0, decimal_places=2)
    currency: str = Field(default="USD", min_length= 3, max_length=3)

class OrderResponse(BaseModel):
    id: int
    user_id: int
    amount: Decimal
    currency: str
    status: str
    created_at: datetime

    class Config:
        from_attributes = True