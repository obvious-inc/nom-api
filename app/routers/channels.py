import http
from datetime import datetime
from typing import List, Optional, Union

from fastapi import APIRouter, Body, Depends

from app.dependencies import PermissionsChecker, common_parameters, get_current_user, get_current_user_non_error
from app.models.user import User
from app.schemas.channels import (
    ChannelBulkReadStateCreateSchema,
    ChannelUpdateSchema,
    DMChannelCreateSchema,
    EitherChannel,
    ServerChannelCreateSchema,
    TopicChannelCreateSchema,
)
from app.schemas.messages import EitherMessage
from app.schemas.permissions import PermissionUpdateSchema
from app.schemas.users import PublicUserSchema
from app.services.channels import (
    bulk_mark_channels_as_read,
    create_channel,
    create_typing_indicator,
    delete_channel,
    get_channel,
    get_channel_members,
    get_channel_permissions,
    invite_members_to_channel,
    join_channel,
    kick_member_from_channel,
    mark_channel_as_read,
    update_channel,
    update_channel_permissions,
)
from app.services.messages import get_message, get_messages

router = APIRouter()


@router.post(
    "",
    response_description="Create new channel",
    response_model=EitherChannel,
    status_code=http.HTTPStatus.CREATED,
    dependencies=[Depends(PermissionsChecker(permissions=["channels.create"]))],
)
async def post_create_channel(
    channel: Union[ServerChannelCreateSchema, TopicChannelCreateSchema, DMChannelCreateSchema] = Body(...),
    current_user: User = Depends(get_current_user),
):
    return await create_channel(channel, current_user=current_user)


@router.get(
    "/{channel_id}/messages",
    response_description="Get latest messages",
    response_model=List[EitherMessage],
    dependencies=[Depends(PermissionsChecker(needs_user=False, permissions=["messages.list"]))],
)
async def get_list_messages(channel_id, common_params: dict = Depends(common_parameters)):
    return await get_messages(channel_id=channel_id, **common_params)


@router.get(
    "/{channel_id}",
    response_description="Get channel info",
    response_model=EitherChannel,
    dependencies=[Depends(PermissionsChecker(needs_user=False, permissions=["channels.view"]))],
)
async def get_fetch_channel(channel_id):
    return await get_channel(channel_id=channel_id)


@router.get(
    "/{channel_id}/messages/{message_id}",
    response_description="Get message",
    response_model=EitherMessage,
    dependencies=[Depends(PermissionsChecker(needs_user=False, permissions=["messages.list"]))],
)
async def get_specific_message(channel_id, message_id):
    return await get_message(channel_id=channel_id, message_id=message_id)


@router.delete(
    "/{channel_id}",
    response_description="Delete channel",
    response_model=EitherChannel,
    dependencies=[Depends(PermissionsChecker(needs_user=False, permissions=["channels.delete"]))],
)
async def delete_remove_channel(channel_id, current_user: User = Depends(get_current_user)):
    return await delete_channel(channel_id=channel_id, current_user=current_user)


@router.post("/{channel_id}/typing", summary="Notify typing", status_code=http.HTTPStatus.NO_CONTENT)
async def post_user_typing_in_channel(channel_id, current_user: User = Depends(get_current_user)):
    await create_typing_indicator(channel_id, current_user)


@router.patch("/{channel_id}", summary="Update channel", response_model=EitherChannel, status_code=http.HTTPStatus.OK)
async def patch_update_channel(
    channel_id,
    update_data: ChannelUpdateSchema,
    current_user: User = Depends(get_current_user),
):
    return await update_channel(channel_id, update_data=update_data, current_user=current_user)


@router.post("/{channel_id}/ack", response_description="ACK channel", status_code=http.HTTPStatus.NO_CONTENT)
async def post_mark_channel_read(
    channel_id, last_read_at: Optional[datetime] = None, current_user: User = Depends(get_current_user)
):
    await mark_channel_as_read(channel_id, last_read_at, current_user=current_user)


@router.post("/ack", response_description="Bulk ACK channels", status_code=http.HTTPStatus.NO_CONTENT)
async def post_bulk_mark_channels_read(
    ack_data: ChannelBulkReadStateCreateSchema, current_user: User = Depends(get_current_user)
):
    await bulk_mark_channels_as_read(ack_data, current_user=current_user)


@router.post(
    "/{channel_id}/invite",
    summary="Invite user to channel",
    status_code=http.HTTPStatus.NO_CONTENT,
    dependencies=[Depends(PermissionsChecker(permissions=["channels.invite"]))],
)
async def post_invite_to_channel(
    channel_id: str, members: List[str] = Body(..., embed=True), current_user: User = Depends(get_current_user)
):
    return await invite_members_to_channel(channel_id=channel_id, members=members, current_user=current_user)


@router.delete(
    "/{channel_id}/members/me", response_description="Remove me from channel", status_code=http.HTTPStatus.NO_CONTENT
)
async def delete_remove_me_from_channel(channel_id: str, current_user: User = Depends(get_current_user)):
    return await kick_member_from_channel(channel_id=channel_id, member_id=str(current_user.pk))


@router.delete(
    "/{channel_id}/members/{member_id}",
    response_description="Remove member from channel",
    status_code=http.HTTPStatus.NO_CONTENT,
    dependencies=[Depends(PermissionsChecker(permissions=["channels.kick"]))],
)
async def delete_remove_member_from_channel(channel_id: str, member_id: str):
    return await kick_member_from_channel(channel_id=channel_id, member_id=member_id)


@router.put(
    "/{channel_id}/permissions",
    summary="Update channel permissions",
    status_code=http.HTTPStatus.NO_CONTENT,
    dependencies=[Depends(PermissionsChecker(permissions=["channels.permissions.manage"]))],
)
async def put_update_channel_permissions(channel_id: str, update_data: List[PermissionUpdateSchema] = Body(...)):
    return await update_channel_permissions(channel_id=channel_id, update_data=update_data)


@router.get(
    "/{channel_id}/permissions",
    summary="Get channel permissions",
    response_model=List[str],
)
async def get_fetch_channel_permissions(
    channel_id: str, current_user_or_exception: User = Depends(get_current_user_non_error)
):
    return await get_channel_permissions(channel_id=channel_id, current_user_or_exception=current_user_or_exception)


@router.post(
    "/{channel_id}/join",
    summary="Join channel",
    status_code=http.HTTPStatus.NO_CONTENT,
    dependencies=[Depends(PermissionsChecker(permissions=["channels.join"]))],
)
async def post_join_server(channel_id: str, current_user: User = Depends(get_current_user)):
    return await join_channel(channel_id=channel_id, current_user=current_user)


@router.get(
    "/{channel_id}/members",
    response_description="List channel members",
    response_model=List[PublicUserSchema],
    dependencies=[Depends(PermissionsChecker(permissions=["channels.view"]))],
)
async def get_fetch_channel_members(channel_id: str):
    return await get_channel_members(channel_id=channel_id)
