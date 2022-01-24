import http
from typing import List, Union

from fastapi import APIRouter, Body, Depends

from app.dependencies import get_current_user
from app.models.channel import Channel
from app.models.user import User
from app.schemas.channels import DMChannelCreateSchema, DMChannelSchema, ServerChannelCreateSchema, ServerChannelSchema
from app.schemas.messages import MessageSchema
from app.services.channels import create_channel, delete_channel
from app.services.crud import get_items
from app.services.messages import get_messages

router = APIRouter()


@router.post(
    "",
    response_description="Create new channel",
    response_model=Union[ServerChannelSchema, DMChannelSchema],
    status_code=http.HTTPStatus.CREATED,
)
async def post_create_channel(
    channel: Union[ServerChannelCreateSchema, DMChannelCreateSchema] = Body(...),
    current_user: User = Depends(get_current_user),
):
    return await create_channel(channel, current_user=current_user)


@router.get(
    "", response_description="List all channels", response_model=List[Union[ServerChannelSchema, DMChannelSchema]]
)
async def list_channels(current_user: User = Depends(get_current_user)):
    channels = await get_items(filters={}, result_obj=Channel, current_user=current_user)
    return channels


@router.get("/{channel_id}/messages", response_description="Get latest messages", response_model=List[MessageSchema])
async def get_list_messages(channel_id, size: int = 50, current_user: User = Depends(get_current_user)):
    messages = await get_messages(channel_id, size, current_user=current_user)
    return messages


@router.delete(
    "/{channel_id}", response_description="Delete channel", response_model=Union[ServerChannelSchema, DMChannelSchema]
)
async def delete_remove_channel(channel_id, current_user: User = Depends(get_current_user)):
    channel = await delete_channel(channel_id=channel_id, current_user=current_user)
    return channel
