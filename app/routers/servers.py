import http
from typing import List

from fastapi import APIRouter, Body, Depends, HTTPException
from starlette import status

from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.channels import ServerChannelSchema
from app.schemas.sections import SectionCreateSchema, SectionSchema, SectionServerUpdateSchema
from app.schemas.servers import (
    PublicServerSchema,
    ServerCreateSchema,
    ServerMemberSchema,
    ServerSchema,
    ServerUpdateSchema,
)
from app.schemas.users import RoleCreateSchema, RoleSchema
from app.services.channels import get_server_channels
from app.services.roles import create_role, get_roles
from app.services.sections import create_section, get_sections, update_server_sections
from app.services.servers import (
    create_server,
    get_public_server_info,
    get_server_members,
    get_servers,
    is_eligible_to_join_server,
    join_server,
    update_server,
)

router = APIRouter()


@router.get("", summary="List servers", response_model=List[ServerSchema], dependencies=[Depends(get_current_user)])
async def get_list_servers():
    return await get_servers()


@router.get("/{server_id}", summary="Get server info", response_model=PublicServerSchema)
async def get_fetch_server(server_id: str):
    return await get_public_server_info(server_id=server_id)


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


@router.get("/{server_id}/sections", summary="List sections", response_model=List[SectionSchema])
async def get_list_sections(server_id, current_user: User = Depends(get_current_user)):
    return await get_sections(server_id, current_user=current_user)


@router.post(
    "/{server_id}/sections",
    summary="Create a section",
    response_model=SectionSchema,
    status_code=http.HTTPStatus.CREATED,
)
async def post_create_section(
    server_id, section_data: SectionCreateSchema, current_user: User = Depends(get_current_user)
):
    return await create_section(server_id=server_id, section_model=section_data, current_user=current_user)


@router.put(
    "/{server_id}/sections",
    summary="Update server's sections",
    response_model=List[SectionSchema],
    status_code=http.HTTPStatus.OK,
)
async def put_update_sections(
    server_id, section_data: List[SectionServerUpdateSchema], current_user: User = Depends(get_current_user)
):
    return await update_server_sections(server_id=server_id, sections=section_data, current_user=current_user)


@router.get("/{server_id}/roles", summary="List roles", response_model=List[RoleSchema])
async def get_list_roles(server_id, current_user: User = Depends(get_current_user)):
    return await get_roles(server_id=server_id, current_user=current_user)


@router.post(
    "/{server_id}/roles",
    summary="Create a role",
    response_model=RoleSchema,
    status_code=http.HTTPStatus.CREATED,
)
async def post_create_role(server_id, role_data: RoleCreateSchema, current_user: User = Depends(get_current_user)):
    return await create_role(server_id=server_id, role_model=role_data, current_user=current_user)
