from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.api.schemas import UserCreate, UserResponse,OrderResponse

from app.db.session import get_db
from app.repository.user_repository import UserRepository
from app.repository.order_repository import OrderRepository

router = APIRouter(prefix="/users", tags=["users"])

@router.post("",response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(payload: UserCreate, db:Session = Depends(get_db)):
    repo = UserRepository(db)
    existing = repo.get_by_email(payload.email) 
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail = "user with this email already exists"
        )
    user = repo.create(payload.name,payload.email)
    return user

@router.get("/{user_id}", response_model=UserResponse)
def get_user(user_id:int, db:Session = Depends(get_db)):
    repo = UserRepository(db)
    user = repo.get_by_id(user_id)

    if user is None:
        raise HTTPException(
            status_code = status.HTTP_404_NOT_FOUND,
            detail="User with this id does not exist",
        )
    return user

@router.get("/{user_id}/orders",response_model=list[OrderResponse])
def get_orders_for_user(
    user_id: int, 
    db:Session = Depends(get_db),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    user_repo = UserRepository(db)
    user = user_repo.get_by_id(user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            details = "This user id does not exist"
        )
    
    order_repo = OrderRepository(db)
    orders = order_repo.list_by_users(
        user_id=user_id,
        limit=limit,
        offset=offset,
    )
    return orders