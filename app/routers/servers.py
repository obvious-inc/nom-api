import http
from typing import List

from fastapi import APIRouter, Body, Depends, HTTPException
from starlette import status

from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.channels import ServerChannelSchema
from app.schemas.servers import ServerCreateSchema, ServerMemberSchema, ServerSchema, ServerUpdateSchema
from app.services.channels import get_server_channels
from app.services.servers import (
    create_server,
    get_server_members,
    get_servers,
    is_eligible_to_join_server,
    join_server,
    update_server,
)

router = APIRouter()


@router.get("", summary="List servers", response_model=List[ServerSchema])
async def get_list_servers(current_user: User = Depends(get_current_user)):
    return await get_servers(current_user=current_user)


@router.post(
    "", response_description="Create new server", response_model=ServerSchema, status_code=http.HTTPStatus.CREATED
)
async def post_create_server(server: ServerCreateSchema = Body(...), current_user: User = Depends(get_current_user)):
    return await create_server(server, current_user=current_user)


@router.get(
    "/{server_id}/members",
    response_description="List server members",
    response_model=List[ServerMemberSchema],
    status_code=http.HTTPStatus.OK,
)
async def get_list_server_members(server_id, current_user: User = Depends(get_current_user)):
    return await get_server_members(server_id, current_user=current_user)


@router.post(
    "/{server_id}/join", summary="Join server", response_model=ServerMemberSchema, status_code=http.HTTPStatus.CREATED
)
async def post_join_server(server_id, current_user: User = Depends(get_current_user)):
    return await join_server(server_id=server_id, current_user=current_user)


@router.get(
    "/{server_id}/eligible",
    summary="Eligible to join server",
    status_code=http.HTTPStatus.NO_CONTENT,
)
async def get_check_server_joining_eligibility(server_id, current_user: User = Depends(get_current_user)):
    is_eligible = await is_eligible_to_join_server(server_id=server_id, current_user=current_user)
    if not is_eligible:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User not eligible to join this server")


@router.patch("/{server_id}", summary="Update server", response_model=ServerSchema, status_code=http.HTTPStatus.OK)
async def patch_update_server(
    server_id, update_data: ServerUpdateSchema, current_user: User = Depends(get_current_user)
):
    return await update_server(server_id, update_data=update_data, current_user=current_user)


@router.get(
    "/{server_id}/channels",
    response_description="List server channels",
    response_model=List[ServerChannelSchema],
    status_code=http.HTTPStatus.OK,
)
async def get_list_server_channels(server_id, current_user: User = Depends(get_current_user)):
    return await get_server_channels(server_id, current_user=current_user)
