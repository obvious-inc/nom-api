from app.models.user import User
from app.services.channels import get_server_channels
from app.services.servers import get_server_members, get_user_servers
from app.services.users import get_user_read_states


async def get_connection_ready_data(current_user: User) -> dict:
    data = {"user": current_user.dump(), "servers": []}
    servers = await get_user_servers(current_user=current_user)
    for server in servers:
        server_data = {"id": str(server.id), "name": server.name, "owner": str(server.owner.pk)}
        channels = await get_server_channels(server_id=str(server.id), current_user=current_user)
        members = await get_server_members(server_id=str(server.id), current_user=current_user)

        member_list = []
        for member in members:
            user = await member.user.fetch()
            member_dict = {
                "id": str(member.id),
                "user": {"id": str(user.id), "display_name": user.display_name},
                "server": str(member.server.pk),
                "display_name": member.display_name,
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
            }
        )

        data["servers"].append(server_data)

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
