from typing import List

from fastapi import APIRouter, Depends

from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.servers import ServerSchema
from app.schemas.users import UserSchema
from app.services.servers import get_user_servers

router = APIRouter()


@router.get("/me", response_description="Get user info", response_model=UserSchema, summary="Get current user info")
async def get_user_me(current_user: User = Depends(get_current_user)):
    return current_user


@router.get(
    "/me/servers", response_description="List servers current user belongs to", response_model=List[ServerSchema]
)
async def list_user_servers(current_user: User = Depends(get_current_user)):
    servers = await get_user_servers(current_user=current_user)
    return servers
