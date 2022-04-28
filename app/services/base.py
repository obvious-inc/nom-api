from app.models.section import Section
from app.models.user import User
from app.services.channels import get_dm_channels, get_server_channels
from app.services.crud import get_items
from app.services.servers import get_server_members, get_user_servers
from app.services.users import get_user_read_states


async def get_connection_ready_data(current_user: User) -> dict:
    data = {"user": current_user.dump(), "servers": []}
    servers = await get_user_servers(current_user=current_user)
    common_user_ids = set()

    for server in servers:
        server_data = {"id": str(server.id), "name": server.name, "owner": str(server.owner.pk)}
        channels = await get_server_channels(server_id=str(server.id), current_user=current_user)
        members = await get_server_members(server_id=str(server.id), current_user=current_user)
        sections = await get_items(
            filters={"server": server.pk},
            result_obj=Section,
            current_user=current_user,
            sort_by_field="position",
            sort_by_direction=1,
        )

        member_list = []
        for member in members:
            common_user_ids.add(member.user.pk)
            member_dict = {
                "id": str(member.id),
                "user": str(member.user.pk),
                "server": str(member.server.pk),
                "display_name": member.display_name,
                "joined_at": member.joined_at,
                "pfp": member.pfp,
            }
            member_list.append(member_dict)

        server_data.update(
            {
                "channels": [
                    {
                        "id": str(channel.id),
                        "last_message_at": channel.last_message_at.isoformat() if channel.last_message_at else None,
                        "name": channel.name,
                    }
                    for channel in channels
                ],
                "members": member_list,
                "sections": [section.dump() for section in sections],
            }
        )

        data["servers"].append(server_data)

    dm_channels = []
    for channel in await get_dm_channels(current_user=current_user, limit=None):
        common_user_ids.update(map(lambda m: m.pk, channel.members))
        dm_channels.append(channel.dump())

    data["dms"] = dm_channels

    user_list = await get_items(
        filters={"_id": {"$in": list(common_user_ids)}}, result_obj=User, current_user=current_user, limit=None
    )

    data["users"] = [
        {
            "id": str(user.pk),
            "display_name": user.display_name,
            "pfp": user.pfp,
            "wallet_address": user.wallet_address,
            "status": user.status,
        }
        for user in user_list
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
