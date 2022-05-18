import json
from typing import Any, Dict

from bson import ObjectId

from app.helpers.cache_utils import cache
from app.models.section import Section
from app.services.crud import get_item, get_item_by_id


async def fetch_and_cache_section(section_id: str, channel_id: str) -> Dict[str, Any]:
    section = None
    if section_id:
        section = await get_item_by_id(id_=section_id, result_obj=Section)
    elif channel_id:
        section = await get_item(filters={"channels": ObjectId(channel_id)}, result_obj=Section)
        if section:
            section_id = str(section.pk)

    if not section:
        await cache.client.hset(f"channel:{channel_id}", "section", "")
        return {}

    section_overwrites = {str(overwrite.role.pk): overwrite.permissions for overwrite in section.permission_overwrites}

    dict_section = {"permissions": json.dumps(section_overwrites)}

    await cache.client.hset(f"section:{section_id}", mapping=dict_section)
    await cache.client.hset(f"channel:{channel_id}", "section", section_id)
    return dict_section
