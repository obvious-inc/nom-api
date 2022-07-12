from app.models.app import App
from app.models.user import User
from app.services.channels import get_all_member_channels
from app.services.crud import get_items
from app.services.users import get_user_read_states


async def get_connection_ready_data(current_user: User) -> dict:
    data = {"user": current_user.dump()}
    apps = await get_items(filters={}, result_obj=App)

    # TODO: pass only installed apps
    data["apps"] = [{"id": str(app.id), "name": app.name, "created_at": app.created_at.isoformat()} for app in apps]

    channels = []
    for channel in await get_all_member_channels(current_user=current_user, limit=None):
        channels.append(channel.dump())

    data["channels"] = channels

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
