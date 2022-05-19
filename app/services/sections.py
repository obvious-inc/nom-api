from typing import List

from bson import ObjectId
from fastapi import HTTPException
from starlette import status

from app.helpers.queue_utils import queue_bg_task
from app.helpers.ws_events import WebSocketServerEvent
from app.models.section import Section
from app.models.server import Server
from app.models.user import User
from app.schemas.sections import SectionCreateSchema, SectionServerUpdateSchema, SectionUpdateSchema
from app.services.crud import create_item, delete_item, find_and_update_item, get_item_by_id, get_items, update_item
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

    # TODO: verify channels belong to server?

    section = await create_item(section_model, result_obj=Section, current_user=current_user, user_field=None)

    await queue_bg_task(
        broadcast_server_event,
        server_id,
        str(current_user.id),
        WebSocketServerEvent.SERVER_SECTION_CREATE,
        {"server": server_id, "section": await section.to_dict()},
    )

    return section


async def update_section(section_id: str, update_data: SectionUpdateSchema, current_user: User):
    section = await get_item_by_id(id_=section_id, result_obj=Section, current_user=current_user)
    server = await section.server.fetch()
    if server.owner != current_user:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User has no permissions to update section")

    data = update_data.dict(exclude_unset=True)
    section = await get_item_by_id(id_=section_id, result_obj=Section, current_user=current_user)

    # TODO: verify channels belong to server?

    updated_section = await update_item(section, data=data, current_user=current_user)

    await queue_bg_task(
        broadcast_server_event,
        str(server.pk),
        str(current_user.id),
        WebSocketServerEvent.SERVER_SECTION_UPDATE,
        {"server": str(server.pk), "section": await updated_section.to_dict()},
    )

    return updated_section


async def update_server_sections(server_id: str, sections: List[SectionServerUpdateSchema], current_user: User):
    server = await get_item_by_id(id_=server_id, result_obj=Server, current_user=current_user)
    if server.owner != current_user:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User has no permissions to update sections")

    final_sections = []
    for section_model in sections:
        section_id = section_model.id
        update_data = {
            "name": section_model.name,
            "channels": section_model.channels,
        }

        if section_model.position is not None:
            update_data["position"] = section_model.position

        updated_section = await find_and_update_item(
            filters={"_id": ObjectId(section_id)}, data={"$set": update_data}, result_obj=Section
        )

        final_sections.append(updated_section)

    await queue_bg_task(
        broadcast_server_event,
        server_id,
        str(current_user.id),
        WebSocketServerEvent.SERVER_SECTIONS_UPDATE,
        {"server": server_id, "sections": [await section.to_dict() for section in final_sections]},
    )

    return final_sections


async def delete_section(section_id: str, current_user: User):
    section = await get_item_by_id(id_=section_id, result_obj=Section, current_user=current_user)
    server = await section.server.fetch()
    if server.owner != current_user:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User has no permissions to delete section")

    await queue_bg_task(
        broadcast_server_event,
        str(server.pk),
        str(current_user.id),
        WebSocketServerEvent.SERVER_SECTION_DELETE,
        {"server": str(server.pk), "section": await section.to_dict()},
    )

    return await delete_item(item=section)
