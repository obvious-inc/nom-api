from app.helpers.whitelist import is_wallet_whitelisted
from app.models.app import App
from app.models.user import User
from app.services.channels import get_all_member_channels
from app.services.crud import get_items
from app.services.users import get_user_read_states


async def get_connection_ready_data(current_user: User) -> dict:
    user_data = current_user.dump()

    try:
        user_whitelisted = await is_wallet_whitelisted(wallet_address=current_user.wallet_address)
        user_data["whitelisted"] = user_whitelisted
    except Exception:
        pass

    data = {"user": user_data}
    apps = await get_items(filters={}, result_obj=App)

    # TODO: pass only installed apps
    data["apps"] = [{"id": str(app.id), "name": app.name, "created_at": app.created_at.isoformat()} for app in apps]

    unique_user_ids = set()

    channels = []
    for channel in await get_all_member_channels(current_user=current_user, limit=None):
        unique_user_ids.update([member.pk for member in channel.members])
        dumped_channel = channel.dump()
        dumped_channel["members"] = [{"user": str(member.pk)} for member in channel.members]
        channels.append(dumped_channel)

    data["channels"] = channels

    users = await get_items(filters={"_id": {"$in": list(unique_user_ids)}}, result_obj=User, limit=None)
    data["users"] = [
        {
            "id": str(user.pk),
            "wallet_address": user.wallet_address,
        }
        for user in users
    ]

    read_states = await get_user_read_states(current_user=current_user)
    data["read_states"] = [
        {
            "channel": str(read_state.channel.pk),
            "last_read_at": read_state.last_read_at.isoformat(),
            "mention_count": read_state.mention_count,
        }
        for read_state in read_states
    ]

    return data
