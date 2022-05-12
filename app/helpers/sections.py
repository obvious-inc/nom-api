import json
from typing import Dict, List, Optional

from bson import ObjectId

from app.helpers.cache_utils import cache
from app.models.section import Section
from app.services.crud import get_item


async def fetch_section_permission_ow(channel_id: Optional[str]) -> Dict[str, List[str]]:
    if not channel_id:
        return {}

    section_id = await cache.client.hget(f"channel:{channel_id}", "section")
    cached_section_permissions = await cache.client.hget(f"section:{section_id}", "permissions")
    if cached_section_permissions is not None:
        return json.loads(cached_section_permissions)

    section = await get_item(filters={"channels": ObjectId(channel_id)}, result_obj=Section)
    if not section:
        return {}

    section_overwrites = {str(overwrite.role.pk): overwrite.permissions for overwrite in section.permission_overwrites}
    await cache.client.hset(f"section:{str(section.pk)}", "permissions", json.dumps(section_overwrites))
    # TODO: this should be done on creating sections, not here...
    await cache.client.hset(f"channel:{channel_id}", "section", str(section.pk))

    return section_overwrites
