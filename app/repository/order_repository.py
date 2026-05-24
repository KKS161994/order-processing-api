from sqlalchemy.orm import Session
from app.models.order import Order
from sqlalchemy import select

class OrderRepository:
    def __init__(self,db:Session):
        self.db = db

    def create(self,user_id:int, amount: int, currency:str="USD")->Order:
        order = Order(user_id = user_id, amount = amount,currency=currency)
        self.db.add(order)
        self.db.commit()
        self.db.refresh(order)
        return order
    

    def get_by_id(self,order_id:int)->Order | None:
        return self.db.get(Order,order_id)
    
    def list_by_users(self, user_id:int, limit:int = 20, offset:int = 0)->list[Order]:
        return self.db.execute(
            select(Order)
            .where(Order.user_id == user_id)
            .order_by(Order.created_at.desc())
            .limit(limit)
            .offset(offset)
        ).scalars().all()