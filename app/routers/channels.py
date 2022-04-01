import http
from typing import List, Union

from fastapi import APIRouter, Body, Depends

from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.channels import DMChannelCreateSchema, EitherChannel, ServerChannelCreateSchema
from app.schemas.messages import MessageSchema
from app.services.channels import create_channel, create_typing_indicator, delete_channel
from app.services.messages import get_message, get_messages

router = APIRouter()


@router.post(
    "",
    response_description="Create new channel",
    response_model=EitherChannel,
    status_code=http.HTTPStatus.CREATED,
)
async def post_create_channel(
    channel: Union[ServerChannelCreateSchema, DMChannelCreateSchema] = Body(...),
    current_user: User = Depends(get_current_user),
):
    return await create_channel(channel, current_user=current_user)


@router.get("/{channel_id}/messages", response_description="Get latest messages", response_model=List[MessageSchema])
async def get_list_messages(channel_id, size: int = 50, current_user: User = Depends(get_current_user)):
    messages = await get_messages(channel_id, size, current_user=current_user)
    return messages


@router.get("/{channel_id}/messages/{message_id}", response_description="Get message", response_model=MessageSchema)
async def get_specific_message(channel_id, message_id, current_user: User = Depends(get_current_user)):
    return await get_message(channel_id, message_id, current_user=current_user)


@router.delete("/{channel_id}", response_description="Delete channel", response_model=EitherChannel)
async def delete_remove_channel(channel_id, current_user: User = Depends(get_current_user)):
    channel = await delete_channel(channel_id=channel_id, current_user=current_user)
    return channel


@router.post("/{channel_id}/typing", summary="Notify typing", status_code=http.HTTPStatus.NO_CONTENT)
async def post_user_typing_in_channel(channel_id, current_user: User = Depends(get_current_user)):
    await create_typing_indicator(channel_id, current_user)
