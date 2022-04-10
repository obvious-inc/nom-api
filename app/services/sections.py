from typing import List

from bson import ObjectId
from fastapi import HTTPException
from starlette import status

from app.models.section import Section
from app.models.server import Server
from app.models.user import User
from app.schemas.sections import SectionCreateSchema, SectionUpdateSchema
from app.services.crud import create_item, delete_items, get_item_by_id, get_items, update_item


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

    return await create_item(section_model, result_obj=Section, current_user=current_user, user_field=None)


async def update_section(server_id: str, section_id: str, update_data: SectionUpdateSchema, current_user: User):
    server = await get_item_by_id(id_=server_id, result_obj=Server, current_user=current_user)
    if server.owner != current_user:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User has no permissions to update section")

    data = update_data.dict(exclude_unset=True)
    section = await get_item_by_id(id_=section_id, result_obj=Section, current_user=current_user)

    return await update_item(section, data=data, current_user=current_user)


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

    return final_sections
