import http
from typing import List, Union

from fastapi import APIRouter, Body, Depends

from app.dependencies import get_current_user
from app.models.channel import Channel
from app.models.user import User
from app.schemas.channels import DMChannelCreateSchema, DMChannelSchema, ServerChannelCreateSchema, ServerChannelSchema
from app.services.channels import create_channel
from app.services.crud import get_items

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
