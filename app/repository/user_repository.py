from sqlalchemy.orm import Session
from sqlalchemy import select
from app.models.user import User

class UserRepository:
    def __init__(self, db : Session):
        self.db = db
    
    def create(self,username:str, email:str,password:str)-> User:
        user = User(email = email, name =username,password_hash = password)
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user
    
    def get_by_id(self, id:int)->User | None:
        return self.db.get(User,id)
    
    def get_by_email(self,email:str)->User | None:
        return self.db.execute(
            select(User).where(User.email == email)
        ).scalar_one_or_none()
    