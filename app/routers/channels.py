import http
from datetime import datetime
from typing import List, Optional, Union

from fastapi import APIRouter, Body, Depends

from app.dependencies import PermissionsChecker, common_parameters, get_current_user
from app.models.user import User
from app.schemas.channels import (
    ChannelBulkReadStateCreateSchema,
    ChannelUpdateSchema,
    DMChannelCreateSchema,
    EitherChannel,
    ServerChannelCreateSchema,
)
from app.schemas.messages import EitherMessage
from app.services.channels import (
    bulk_mark_channels_as_read,
    create_channel,
    create_typing_indicator,
    delete_channel,
    get_channel,
    mark_channel_as_read,
    update_channel,
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
    channel: Union[ServerChannelCreateSchema, DMChannelCreateSchema] = Body(...),
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


@router.delete("/{channel_id}", response_description="Delete channel", response_model=EitherChannel)
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
