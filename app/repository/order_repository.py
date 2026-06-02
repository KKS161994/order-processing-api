from sqlalchemy.orm import Session
from app.models.order import Order
from sqlalchemy import select, func

class OrderRepository:
    def __init__(self,db:Session):
        self.db = db

    def create(self,user_id:int, amount: int, currency:str="USD")->Order:
        order = Order(user_id = user_id, amount = amount,currency=currency)
        self.db.add(order)
        # self.db.commit()
        # self.db.refresh(order)
        self.db.flush()
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
    
    def count_by_user(self,user_id:int)-> int:
        return self.db.scalar(
            select(func.count())
            .select_from(Order)
            .where(Order.user_id == user_id)
        ) or 0

    def list_by_user_after(
            self, user_id: int, cursor:int|None, limit:int = 20,
    )->list[Order]:
        stmt = select(Order).where(Order.user_id == user_id)
        if cursor is not None:
            stmt = stmt.where(Order.id<cursor)
        stmt = stmt.order_by(Order.id.desc()).limit(limit)
        return self.db.execute(statement=stmt).scalars().all()