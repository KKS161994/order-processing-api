from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.schemas import OrderResponse, UserCreate, UserResponse
from app.db.session import get_db
from app.service.order_service import OrderService
from app.service.user_service import UserAlreadyExists, UserNotFound, UserService

router = APIRouter(prefix="/users", tags=["users"])


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(payload: UserCreate, db: Session = Depends(get_db)):
    service = UserService(db)
    try:
        return service.create_user(email=payload.email, name=payload.name)
    except UserAlreadyExists as e:
        raise HTTPException(status.HTTP_409_CONFLICT, detail=str(e))


@router.get("/{user_id}", response_model=UserResponse)
def get_user(user_id: int, db: Session = Depends(get_db)):
    service = UserService(db)
    try:
        return service.get_user(user_id)
    except UserNotFound as e:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get("/{user_id}/orders", response_model=list[OrderResponse])
def list_user_orders(
    user_id: int,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    service = OrderService(db)
    try:
        return service.list_all_orders(user_id, limit=limit, offset=offset)
    except UserNotFound as e:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(e))