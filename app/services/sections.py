from typing import List

from bson import ObjectId
from fastapi import HTTPException
from starlette import status

from app.helpers.queue_utils import queue_bg_task
from app.helpers.ws_events import WebSocketServerEvent
from app.models.section import Section
from app.models.server import Server
from app.models.user import User
from app.schemas.sections import SectionCreateSchema, SectionUpdateSchema
from app.services.crud import create_item, delete_items, get_item_by_id, get_items, update_item
from app.services.websockets import broadcast_server_event


async def get_sections(server_id: str, current_user: User):
    return await get_items(
        filters={"server": ObjectId(server_id)},
        result_obj=Section,
        current_user=current_user,
        sort_by_field="position",
        sort_by_direction=1,
    )


async def create_section(server_id: str, section_model: SectionCreateSchema, current_user: User):
    server = await get_item_by_id(id_=server_id, result_obj=Server, current_user=current_user)
    if server.owner != current_user:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User has no permissions to create section")

    section_model.server = str(server.pk)

    section = await create_item(section_model, result_obj=Section, current_user=current_user, user_field=None)

    await queue_bg_task(
        broadcast_server_event,
        server_id,
        str(current_user.id),
        WebSocketServerEvent.SERVER_SECTION_CREATE,
        {"server": server_id, "section": section.to_dict()},
    )

    return section


async def update_section(server_id: str, section_id: str, update_data: SectionUpdateSchema, current_user: User):
    server = await get_item_by_id(id_=server_id, result_obj=Server, current_user=current_user)
    if server.owner != current_user:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User has no permissions to update section")

    data = update_data.dict(exclude_unset=True)
    section = await get_item_by_id(id_=section_id, result_obj=Section, current_user=current_user)

    updated_section = await update_item(section, data=data, current_user=current_user)

    await queue_bg_task(
        broadcast_server_event,
        server_id,
        str(current_user.id),
        WebSocketServerEvent.SERVER_SECTION_UPDATE,
        {"server": server_id, "section": updated_section.to_dict()},
    )

    return updated_section


async def update_server_sections(server_id: str, sections: List[SectionCreateSchema], current_user: User):
    server = await get_item_by_id(id_=server_id, result_obj=Server, current_user=current_user)
    if server.owner != current_user:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User has no permissions to update sections")

    # delete all old sections
    await delete_items(filters={"server": server.pk}, result_obj=Section, current_user=current_user)

    final_sections = []
    for section_model in sections:
        section_model.server = str(server.pk)
        new_section = await create_item(section_model, result_obj=Section, current_user=current_user, user_field=None)
        final_sections.append(new_section)

    await queue_bg_task(
        broadcast_server_event,
        server_id,
        str(current_user.id),
        WebSocketServerEvent.SERVER_SECTIONS_UPDATE,
        {"server": server_id, "sections": final_sections},
    )

    return final_sections
