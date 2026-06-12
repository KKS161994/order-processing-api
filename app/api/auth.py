from fastapi import APIRouter,Depends,HTTPException,status
from pydantic import BaseModel,EmailStr
from app.db.session import get_db
from app.service.auth_service import AuthService,InvalidCredentials


router = APIRouter(prefix="/auth",tags=["auth"])


class LoginRequest(BaseModel):
    email:EmailStr
    password:str

class TokenResponse(BaseModel):
    access_token:str
    token_type: str = "bearer"

@router.post("/login",response_model= TokenResponse)
def login(payload: LoginRequest,db = Depends(get_db)):
    auth_service = AuthService(db)
    try:
        token =auth_service.authenticate(payload.email,payload.password)
    except InvalidCredentials as e:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail=str(e))
    return TokenResponse(access_token=token)



