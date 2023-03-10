import http
from typing import List, Optional, Union

from fastapi import APIRouter, Body, Depends, Response
from starlette.status import HTTP_204_NO_CONTENT

from app.dependencies import PermissionsChecker, get_current_user
from app.models.user import User
from app.schemas.channels import ChannelReadStateSchema, EitherChannel
from app.schemas.preferences import UserPreferencesSchema, UserPreferencesUpdateSchema
from app.schemas.reports import UserReportCreateSchema, UserReportSchema
from app.schemas.servers import ServerMemberUpdateSchema, ServerSchema
from app.schemas.users import PublicUserSchema, UserBlockCreateSchema, UserBlockSchema, UserSchema, UserUpdateSchema
from app.services.channels import get_user_channels
from app.services.servers import get_user_servers
from app.services.users import (
    block_user,
    delete_user,
    get_blocked_users,
    get_user_preferences,
    get_user_profile_by_server_id,
    get_user_read_states,
    get_users_info,
    report_user,
    unblock_user,
    update_user_preferences,
    update_user_profile,
)

router = APIRouter()


@router.get(
    "/me", response_description="Get user profile", response_model=UserSchema, summary="Get current user profile"
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


@router.patch("/me", response_model=UserSchema, summary="Update user profile")
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


@router.get("/me/preferences", summary="Get user preferences", response_model=UserPreferencesSchema)
async def fetch_get_user_preferences(current_user: User = Depends(get_current_user)):
    user_preferences = await get_user_preferences(current_user)
    if not user_preferences:
        return Response(status_code=HTTP_204_NO_CONTENT)

    return user_preferences


@router.put("/me/preferences", summary="Update user preferences", response_model=UserPreferencesSchema)
async def put_update_user_preferences(
    update_data: UserPreferencesUpdateSchema = Body(...), current_user: User = Depends(get_current_user)
):
    return await update_user_preferences(update_data, current_user)


@router.post("/me/reports", summary="Report user", response_model=UserReportSchema, status_code=http.HTTPStatus.CREATED)
async def post_report_user(report: UserReportCreateSchema = Body(...), current_user: User = Depends(get_current_user)):
    return await report_user(report_model=report, current_user=current_user)


@router.get("/me/blocks", summary="Get list of blocked users", response_model=List[UserBlockSchema])
async def get_fetch_blocked_users(current_user: User = Depends(get_current_user)):
    return await get_blocked_users(current_user=current_user)


@router.post("/me/blocks", summary="Block user", status_code=http.HTTPStatus.NO_CONTENT)
async def post_block_user(block: UserBlockCreateSchema = Body(...), current_user: User = Depends(get_current_user)):
    return await block_user(block, current_user=current_user)


@router.delete("/me/blocks/{user_id}", summary="Unblock user", status_code=http.HTTPStatus.NO_CONTENT)
async def post_unblock_user(user_id: str, current_user: User = Depends(get_current_user)):
    return await unblock_user(user_id, current_user=current_user)


@router.delete("/me", summary="Delete account", status_code=http.HTTPStatus.NO_CONTENT)
async def post_delete_user(current_user: User = Depends(get_current_user)):
    return await delete_user(current_user=current_user)
