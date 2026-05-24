from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.schemas import OrderCreate, OrderResponse
from app.db.session import get_db
from app.service.order_service import OrderNotFound, OrderService
from app.service.user_service import UserNotFound

router = APIRouter(prefix="/orders", tags=["orders"])


@router.post("", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
def create_order(payload: OrderCreate, db: Session = Depends(get_db)):
    service = OrderService(db)
    try:
        return service.create_order(
            user_id=payload.user_id,
            amount=payload.amount,
            currency=payload.currency,
        )
    except UserNotFound as e:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get("/{order_id}", response_model=OrderResponse)
def get_order(order_id: int, db: Session = Depends(get_db)):
    service = OrderService(db)
    try:
        return service.get_order(order_id)
    except OrderNotFound as e:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(e))