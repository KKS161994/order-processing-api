from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.schemas import (    
    CursorPaginatedResponse,
    CursorPaginationMeta,
    OrderCreate, 
    OrderResponse,
    PaginationMeta,
    PaginatedResponse,
    UserCreate,
    UserResponse
    )
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

@router.get("/{user_id}/orders",
            response_model=PaginatedResponse[OrderResponse],
            )
def list_user_orders(
    user_id: int,
    limit:int = Query(default= 20, ge = 1, le = 20),
    offset:int = Query(default= 0, ge = 0),
    db:Session = Depends(get_db),
)->PaginatedResponse[OrderResponse]:
    service = OrderService(db)
    try :
        orders,total = service.list_order_by_user(
            user_id=user_id,
            limit=limit,
            offset=offset
        )
    except UserNotFound as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail = str(e))
    return PaginatedResponse[OrderResponse](
        items = [OrderResponse.model_validate(o) for o in orders],
        pagination=PaginationMeta(
            limit=limit,
            offset=offset,
            total=total,
            has_more=(offset+len(orders))<total
        )
    )

@router.get(
    "/{user_id}/orders/cursor",
    response_model=CursorPaginatedResponse[OrderResponse],
)
def list_user_order_cursor(
    user_id:int,
    cursor:int|None = Query(
        default=None,
        description="Order id to paginate after"),
    limit:int = Query(
        default=20,
        ge = 1,
        le = 100,
    ),
    db:Session = Depends(get_db)    
)->CursorPaginatedResponse[OrderResponse]:
    service = OrderService(db)
    try:
        orders = service.list_user_order_after(user_id, cursor=cursor, limit=limit)
    except UserNotFound as e:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(e))
    
    next_cursor = orders[-1].id if orders and len(orders) == limit else None
    return CursorPaginatedResponse[OrderResponse](
        items=[OrderResponse.model_validate(o) for o in orders],
        pagination=CursorPaginationMeta(
            limit = limit,
            next_cursor = next_cursor,
            has_more = next_cursor is not None,
        )
    )