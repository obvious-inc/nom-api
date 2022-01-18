from fastapi import APIRouter, Depends

from app.dependencies import get_current_user
from app.helpers.database import get_db
from app.models.user import User
from app.schemas.users import UserSchema

router = APIRouter()


@router.get("/me", response_description="Get user info", response_model=UserSchema, summary="Get current user info")
async def get_user_me(db=Depends(get_db), current_user: User = Depends(get_current_user)):
    return current_user
