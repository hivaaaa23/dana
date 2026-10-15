from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.dependencies import forbid_when_impersonating, get_current_user
from app.models.user import User
from app.schemas.user import ApiKeyInput, ApiKeyStatus
from app.utils.security import encrypt_api_key
router = APIRouter(prefix="/api-keys", tags=["API keys"])
@router.put("", response_model=ApiKeyStatus, dependencies=[Depends(forbid_when_impersonating)])
def save_api_key(payload: ApiKeyInput, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not payload.api_key.strip(): raise HTTPException(400, "API key cannot be empty")
    current_user.api_key_encrypted = encrypt_api_key(payload.api_key.strip()); db.commit()
    return ApiKeyStatus(configured=True)
@router.get("", response_model=ApiKeyStatus)
def api_key_status(current_user: User = Depends(get_current_user)): return ApiKeyStatus(configured=current_user.api_key_encrypted is not None)
@router.delete("", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(forbid_when_impersonating)])
def delete_api_key(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    current_user.api_key_encrypted = None; db.commit()
