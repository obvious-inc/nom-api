import http
from typing import Union

from fastapi import APIRouter, Body, Depends

from app.dependencies import get_current_user
from app.helpers.database import get_db
from app.models.user import User
from app.schemas.channels import ServerChannelSchema, DMChannelSchema, \
    ServerChannelCreateSchema, DMChannelCreateSchema
from app.services.channels import create_channel

router = APIRouter()


@router.post("",
             response_description="Create new channel",
             response_model=Union[ServerChannelSchema, DMChannelSchema],
             status_code=http.HTTPStatus.CREATED)
async def post_create_channel(channel: Union[ServerChannelCreateSchema, DMChannelCreateSchema] = Body(...),
                              db=Depends(get_db),
                              current_user: User = Depends(get_current_user)):
    return await create_channel(channel, current_user=current_user)
