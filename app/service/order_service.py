from sqlalchemy.orm import Session
from app.models.order import Order
from app.models.user import User
from app.repository.order_repository import OrderRepository
from app.repository.user_repository import UserRepository
from app.service.user_service import UserNotFound

class OrderNotFound(Exception):
    pass

class OrderService:
    def __init__(self,db : Session):
        self.db = db
        self.order_repo = OrderRepository(db)
        self.user_repo = UserRepository(db)

    def create_order(self,user_id:int , amount: int, currency: int)-> Order:
        user = self.user_repo.get_by_id(user_id)
        if user is None:
            raise UserNotFound(f"User {user_id} not exist") 
        
        return self.order_repo.create(
            user_id=user_id,
            amount=amount,
            currency=currency,
        )
    
    def get_order(self,order_id:int)->Order:
        order = self.order_repo.get_by_id(
            order_id=order_id)
        if order is None:
            raise OrderNotFound(f"Order {order_id} not found")
        return order
    
    def list_all_orders(self,user_id:int,limit:int,offset:int)->list[Order]:
        user = self.user_repo.get_by_id(
            id = user_id
        )
        if user is None:
            raise UserNotFound(f"User {user_id} not exist") 
        orders = self.order_repo.list_by_users(
            user_id= user_id,
            limit=limit,
            offset=offset,
        )
        return orders
        