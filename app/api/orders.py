from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.schemas import OrderCreate, OrderResponse
from app.db.session import get_db
from app.repository.order_repository import OrderRepository
from app.repository.user_repository import UserRepository

router = APIRouter(prefix = "/orders",tags = ["orders"])

@router.post("", response_model= OrderResponse, status_code=status.HTTP_201_CREATED)
def create_order(payload: OrderCreate,db:Session = Depends(get_db)):
    user_repo = UserRepository(db)
    user = user_repo.get_by_id(payload.user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No such user exists",
        )
    order_repo = OrderRepository(db)
    order = order_repo.create(
        user_id=payload.user_id,
        amount=payload.amount,
        currency=payload.currency,
        )
    return order


@router.get("/{order_id}",response_model=OrderResponse)
def get_order(order_id:int,db:Session = Depends(get_db)):
    order_repo = OrderRepository(db)
    order = order_repo.get_by_id(order_id= order_id)
    if order is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No order exists for this order id"
        )
    return order