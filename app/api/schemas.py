from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import TypeVar, Generic

T = TypeVar("T")

class PaginationMeta(BaseModel):
    limit: int
    offset: int
    total: int
    has_more: bool

class CursorPaginationMeta(BaseModel):
    limit: int
    next_cursor: int | None
    has_more: bool

class PaginatedResponse(BaseModel, Generic[T]): 
    items: list[T]
    pagination: PaginationMeta

class CursorPaginatedResponse(BaseModel, Generic[T]):
    items: list[T]
    pagination: CursorPaginationMeta

class UserCreate(BaseModel):
    email: EmailStr
    name:str = Field(min_length= 1, max_length=255)
    password: str = Field(min_length=8, max_length= 128)

    @field_validator("name")
    @classmethod
    def strip_name(cls,v:str) -> str:
        stripped = v.strip()
        if not stripped:
            raise ValueError("name cannot be empty or whitespace only")
        return stripped
    
    @field_validator("email")
    @classmethod
    def normalise_email(cls,v:str)->str:
        return v.lower().strip()


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