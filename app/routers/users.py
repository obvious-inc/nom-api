from typing import List, Optional, Union

from fastapi import APIRouter, Body, Depends

from app.dependencies import PermissionsChecker, get_current_user
from app.models.user import User
from app.schemas.channels import ChannelReadStateSchema, EitherChannel
from app.schemas.servers import ServerMemberUpdateSchema, ServerSchema
from app.schemas.users import EitherUserProfile, PublicUserSchema, UserUpdateSchema
from app.services.channels import get_user_channels
from app.services.servers import get_user_servers
from app.services.users import get_user_profile_by_server_id, get_user_read_states, get_users_info, update_user_profile

router = APIRouter()


@router.get(
    "/me", response_description="Get user profile", response_model=EitherUserProfile, summary="Get current user profile"
)
async def get_user_me(server_id: Optional[str] = None, current_user: User = Depends(get_current_user)):
    if server_id:
        return await get_user_profile_by_server_id(server_id, current_user=current_user)
    return current_user


@router.get(
    "/me/servers", response_description="List servers current user belongs to", response_model=List[ServerSchema]
)
async def list_user_servers(current_user: User = Depends(get_current_user)):
    servers = await get_user_servers(current_user=current_user)
    return servers


@router.patch("/me", response_model=EitherUserProfile, summary="Update user profile")
async def patch_update_user_profile(
    server_id: Optional[str] = None,
    update_data: Union[UserUpdateSchema, ServerMemberUpdateSchema] = Body(...),
    current_user: User = Depends(get_current_user),
):
    return await update_user_profile(server_id, update_data=update_data, current_user=current_user)


@router.get("/me/read_states", summary="List user's read states", response_model=List[ChannelReadStateSchema])
async def list_read_states(current_user: User = Depends(get_current_user)):
    return await get_user_read_states(current_user)


@router.get("/me/channels", summary="List channels user belongs to", response_model=List[EitherChannel])
async def fetch_get_user_channels(current_user: User = Depends(get_current_user)):
    return await get_user_channels(current_user)


@router.post(
    "/info",
    response_description="Get users info",
    response_model=List[PublicUserSchema],
    dependencies=[Depends(PermissionsChecker(needs_bearer=True))],
)
async def post_get_users_info(data=Body(...)):
    return await get_users_info(data)
