from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.dependencies import get_current_user
from app.schemas.user import TokenResponse, UserLogin, UserPublic, UserRegister
from app.services.auth_service import authenticate_user, get_user_by_email, register_user
from app.utils.security import create_access_token
router = APIRouter(prefix="/auth", tags=["authentication"])
@router.post("/register", response_model=UserPublic, status_code=201)
def register(payload: UserRegister, db: Session = Depends(get_db)):
    if len(payload.password) < 8: raise HTTPException(400, "Password must be at least 8 characters")
    if get_user_by_email(db, payload.email): raise HTTPException(409, "Email is already registered")
    return register_user(db, payload.email, payload.password)
@router.post("/login", response_model=TokenResponse)
def login(payload: UserLogin, db: Session = Depends(get_db)):
    user = authenticate_user(db, payload.email, payload.password)
    if not user: raise HTTPException(status_code=401, detail="Invalid email or password")
    return TokenResponse(access_token=create_access_token(user.id))
@router.get("/me", response_model=UserPublic)
def me(request: Request, current_user=Depends(get_current_user)):
    out = UserPublic.model_validate(current_user)
    by = getattr(request.state, "impersonated_by", None)
    out.impersonated, out.impersonated_by = by is not None, by
    return out
