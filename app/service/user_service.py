from sqlalchemy.orm import Session
from app.models.user import User
from app.repository.user_repository import UserRepository

class UserAlreadyExists(Exception):
    pass

class UserNotFound(Exception):
    pass

class UserService:
    def __init__(self,db : Session):
        self.repo = UserRepository(db)
        pass

    def create_user(self,email:str, name:str)->User:
        if self.repo.get_by_email(email):
            raise UserAlreadyExists(f"email {email} already exists")
        
        return self.repo.create(
            username = name,
            email=email,
        )

    def get_user(self, user_id: int) -> User | None:
        user = self.repo.get_by_id(id=user_id)
        if user is None:
            raise UserNotFound(f"user with id {user_id} does not exist")
        return user