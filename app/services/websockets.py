import logging
from typing import List, Optional

from sentry_sdk import capture_exception
from umongo import Reference

from app.helpers.events import EventType
from app.helpers.websockets import pusher_client
from app.models.app import App, AppInstalled
from app.models.channel import Channel
from app.models.message import Message
from app.models.server import Server, ServerMember
from app.models.user import User
from app.services.crud import get_item_by_id, get_items

logger = logging.getLogger(__name__)


async def _get_users_online_channels(users: List[User]):
    channels = []
    user: User
    for user in users:
        channels.extend(user.online_channels)
    return list(set(channels))


async def _get_apps_online_channels(apps: List[App]):
    channels = []
    app: App
    for app in apps:
        channels.extend(app.online_channels)
    return list(set(channels))


async def get_server_online_channels(server: Server, current_user: Optional[User]):
    user_ids = set()
    members = await get_items(filters={"server": server.pk}, result_obj=ServerMember, limit=None)
    for member in members:
        user_ids.add(member.user.pk)

    users = await get_items(filters={"_id": {"$in": list(user_ids)}}, result_obj=User, limit=None)

    return await _get_users_online_channels(users)


async def get_channel_online_channels(channel: Channel, current_user: Optional[User]) -> List[str]:
    user_ids = set()
    if channel.kind == "dm" or channel.kind == "topic":
        for member in channel.members:
            user_ids.add(member.pk)
    elif channel.kind == "server":
        # members = await get_items(filters={"server": channel.server.pk}, result_obj=ServerMember, limit=None)
        # # DEPRECATED: further permission check to see if user can actually read message in server channel.
        # # As long as we're not using Servers, this is not needed.
        # for member in members:
        #     user_ids.add(member.user.pk)
        raise NotImplementedError("no longer using servers")

    users = await get_items(filters={"_id": {"$in": list(user_ids)}}, result_obj=User, limit=None)

    online_channels = await _get_users_online_channels(users)

    # TODO: This might slow down the websocket publishing... in the long run, it's best to dispatch user and app events
    # in parallel
    installed_apps = await get_items(filters={"channel": channel.pk}, result_obj=AppInstalled, limit=None)
    if len(installed_apps) > 0:
        app_ids = {install.app.pk for install in installed_apps}
        apps = await get_items(filters={"_id": {"$in": list(app_ids)}}, result_obj=App, limit=None)
        app_channels = await _get_apps_online_channels(apps)
        online_channels.extend(app_channels)

    return online_channels


async def get_servers_online_channels(servers: List[Server], current_user: Optional[User]):
    user_ids = set()
    members = []
    for server in servers:
        server_members = await get_items(filters={"server": server.pk}, result_obj=ServerMember, limit=None)
        members.extend(server_members)
        for member in server_members:
            user_ids.add(member.user.pk)

    users = await get_items(filters={"_id": {"$in": list(user_ids)}}, result_obj=User, limit=None)

    return await _get_users_online_channels(users)


async def pusher_broadcast_messages(
    event: EventType,
    current_user: Optional[User],
    data: dict,
    user: Optional[User] = None,
    users: Optional[List[User]] = None,
    message: Optional[Message] = None,
    channel: Optional[Channel] = None,
    server: Server = None,
    servers: Optional[List[Server]] = None,
    pusher_channel: Optional[str] = None,
    scope: str = None,
):
    pusher_channels = []
    if scope == "server" and server:
        pusher_channels = await get_server_online_channels(server=server, current_user=current_user)
    elif scope == "channel" and channel:
        pusher_channels = await get_channel_online_channels(channel=channel, current_user=current_user)
    elif scope == "message" and message:
        channel = await message.channel.fetch()
        if channel:
            pusher_channels = await get_channel_online_channels(channel=channel, current_user=current_user)
    elif scope == "user" and user:
        pusher_channels = await _get_users_online_channels([user])
    elif scope == "current_user" and current_user:
        pusher_channels = await _get_users_online_channels([current_user])
    elif scope == "users" and users:
        pusher_channels = await _get_users_online_channels(users)
    elif scope == "servers" and servers:
        pusher_channels = await get_servers_online_channels(servers, current_user=current_user)
    elif scope == "user_servers" and servers:
        pusher_channels = await get_servers_online_channels(servers, current_user=current_user)
    elif scope == "pusher_channel" and pusher_channel:
        pusher_channels = [pusher_channel]

    await broadcast_ws_event(event=event, data=data, ws_channels=pusher_channels)


async def broadcast_ws_event(event: EventType, data: dict, ws_channels: Optional[List[str]] = None):
    if not ws_channels:
        logger.debug("no online websocket channels. [event=%s]", event)
        return

    has_errors = False
    event_name = event.value

    while len(ws_channels) > 0:
        push_channels = ws_channels[:90]
        try:
            await pusher_client.trigger(push_channels, event_name, data)
        except Exception as e:
            logger.exception("Problem broadcasting event to Pusher channel. [event_name=%s]", event_name)
            capture_exception(e)
            has_errors = True
        ws_channels = ws_channels[90:]

    if not has_errors:
        logger.info("Event broadcast successful. [event_name=%s]", event_name)


async def broadcast_connection_ready(current_user: User, channel: str):
    raise NotImplementedError("no longer in use!")


async def broadcast_channel_event(
    channel_id: str, current_user_id: str, event: EventType, custom_data: Optional[dict] = None
):
    current_user = await get_item_by_id(id_=current_user_id, result_obj=User)
    channel = await get_item_by_id(id_=channel_id, result_obj=Channel)

    event_data = {"channel": channel.dump()}
    if custom_data:
        event_data.update(custom_data)

    await pusher_broadcast_messages(
        event=event, data=event_data, current_user=current_user, scope="channel", channel=channel
    )


async def broadcast_server_event(
    server_id: str, current_user_id: str, event: EventType, custom_data: Optional[dict] = None
):
    current_user = await get_item_by_id(id_=current_user_id, result_obj=User)
    server = await get_item_by_id(id_=server_id, result_obj=Server)

    event_data = {}
    if custom_data:
        event_data.update(custom_data)

    await pusher_broadcast_messages(
        event=event, data=event_data, current_user=current_user, scope="server", server=server
    )


async def broadcast_current_user_event(
    current_user_id,
    event: EventType,
    custom_data: Optional[dict] = None,
):
    current_user = await get_item_by_id(id_=current_user_id, result_obj=User)

    event_data = {}
    if custom_data:
        event_data.update(custom_data)

    await pusher_broadcast_messages(event=event, data=event_data, current_user=current_user, scope="current_user")


async def broadcast_user_servers_event(current_user_id: str, event: EventType, custom_data: dict) -> None:
    current_user = await get_item_by_id(id_=current_user_id, result_obj=User)

    event_data = {"user": await current_user.to_dict(exclude_fields=["pfp"])}
    if custom_data:
        event_data.update(custom_data)

    server_members = await get_items({"user": current_user}, result_obj=ServerMember, limit=None)
    servers = [member.server for member in server_members]

    await pusher_broadcast_messages(
        event=event, data=event_data, current_user=current_user, scope="user_servers", servers=servers
    )


async def broadcast_users_event(users: List[User], event: EventType, custom_data: dict) -> None:
    event_data = {}
    if custom_data:
        event_data.update(custom_data)

    await pusher_broadcast_messages(event=event, data=event_data, users=users, scope="users", current_user=None)


async def broadcast_websocket_event(user_ids: List[Reference], event: EventType, ws_data: dict):
    listening_users = await get_items(filters={"_id": {"$in": user_ids}}, result_obj=User, limit=None)
    online_channels = set()
    for user in listening_users:
        online_channels.update(user.online_channels)

    await broadcast_ws_event(event, data=ws_data, ws_channels=list(online_channels))
