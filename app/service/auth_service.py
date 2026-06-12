from sqlalchemy.orm import Session

from app.models.user import User
from app.repository.user_repository import UserRepository
from app.security.passwords import verify_pswd
from app.security.tokens import create_token

class InvalidCredentials(Exception):
    pass

class AuthService:
    def __init__(self, db:Session):
        self.repo = UserRepository(db)

    def authenticate(self, email: str, password:str) -> str:
        user:User = self.repo.get_by_email(email=email.lower().strip())
        if user is None or not verify_pswd(password,user.password_hash):
            raise InvalidCredentials("Invalid email or password")
        return create_token(subject=user.id)