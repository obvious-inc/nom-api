from fastapi import APIRouter, Depends, HTTPException

from app.dependencies import get_current_user
from app.helpers.database import get_db
from app.models.user import User
from app.schemas.users import UserSchema
from app.services.users import get_user_by_id

router = APIRouter()


@router.get("/me", response_description="Get user info", response_model=UserSchema)
async def get_user_me(db=Depends(get_db), current_user: User = Depends(get_current_user)):
    user = await get_user_by_id(user_id=current_user.id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user
