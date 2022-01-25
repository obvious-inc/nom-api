import http
from typing import Union

from bson import ObjectId
from fastapi import HTTPException

from app.models.base import APIDocument
from app.models.channel import Channel
from app.models.user import User
from app.schemas.channels import DMChannelCreateSchema, ServerChannelCreateSchema
from app.services.crud import create_item, delete_item, get_item_by_id, get_items


async def create_dm_channel(channel_model: DMChannelCreateSchema, current_user: User) -> Union[Channel, APIDocument]:
    current_user_id = str(current_user.id)
    if current_user_id not in channel_model.members:
        channel_model.members.insert(0, current_user_id)

    # if same exact dm channel already exists, ignore
    filters = {
        "owner": current_user.id,
        "members": {"$all": [ObjectId(member) for member in channel_model.members]},
    }
    existing_dm_channels = await get_items(filters=filters, result_obj=Channel, current_user=current_user)
    if existing_dm_channels:
        # TODO: return 200 status code
        return existing_dm_channels[0]

    return await create_item(channel_model, result_obj=Channel, current_user=current_user, user_field="owner")


async def create_server_channel(
    channel_model: ServerChannelCreateSchema, current_user: User
) -> Union[Channel, APIDocument]:
    return await create_item(channel_model, result_obj=Channel, current_user=current_user, user_field="owner")


async def create_channel(
    channel_model: Union[DMChannelCreateSchema, ServerChannelCreateSchema], current_user: User
) -> Union[Channel, APIDocument]:
    kind = channel_model.kind
    if kind == "dm":
        return await create_dm_channel(channel_model, current_user)
    elif kind == "server":
        return await create_server_channel(channel_model, current_user)
    else:
        raise Exception(f"unexpected channel kind: {kind}")


async def get_server_channels(server_id, current_user: User) -> [Channel]:
    return await get_items(filters={"server": ObjectId(server_id)}, result_obj=Channel, current_user=current_user)


async def delete_channel(channel_id, current_user: User):
    channel = await get_item_by_id(id_=channel_id, result_obj=Channel, current_user=current_user)
    channel_owner = channel.owner
    server = await channel.server.fetch()
    server_owner = server.owner

    if not current_user == channel_owner or not current_user == server_owner:
        raise HTTPException(status_code=http.HTTPStatus.FORBIDDEN)

    return await delete_item(item=channel)
