from bson import ObjectId

from app.helpers.cache_utils import cache
from app.models.app import App, AppInstalled
from app.services.crud import get_item_by_id, get_items


async def fetch_and_cache_app(app_id: str):
    if not app_id:
        return {}

    app = await get_item_by_id(id_=app_id, result_obj=App)
    if not app:
        return {}

    installations = await get_items(filters={"app": ObjectId(app_id)}, result_obj=AppInstalled)

    dict_app = {
        "id": app_id,
        "creator": str(app.creator.pk),
    }

    channel_ids = []
    for installation in installations:
        channel_id = str(installation.channel.pk)
        channel_ids.append(channel_id)
        dict_app[f"channel:{channel_id}"] = ",".join(installation.scopes)

    dict_app["channels"] = ",".join(channel_ids)

    await cache.client.hset(f"app:{app_id}", mapping=dict_app)
    return dict_app
