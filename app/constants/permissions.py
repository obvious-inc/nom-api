from enum import Enum


class Permission(Enum):
    MESSAGES_CREATE = "messages.create"
    MESSAGES_LIST = "messages.list"

    CHANNELS_CREATE = "channels.create"
    CHANNELS_VIEW = "channels.view"
    CHANNELS_INVITE = "channels.invite"
    CHANNELS_JOIN = "channels.join"
    CHANNELS_PERMISSIONS_MANAGE = "channels.permissions.manage"
    CHANNELS_KICK = "channels.kick"
    CHANNELS_DELETE = "channels.delete"
    CHANNELS_MEMBERS_LIST = "channels.members.list"

    MEMBERS_KICK = "members.kick"

    ROLES_LIST = "roles.list"
    ROLES_CREATE = "roles.create"

    APPS_MANAGE = "apps.manage"


ALL_PERMISSIONS = [p.value for p in Permission]
SERVER_OWNER_PERMISSIONS = ALL_PERMISSIONS
CHANNEL_OWNER_PERMISSIONS = ALL_PERMISSIONS

DEFAULT_ROLE_PERMISSIONS = [
    p.value
    for p in [
        Permission.MESSAGES_LIST,
        Permission.MESSAGES_CREATE,
    ]
]

DEFAULT_DM_MEMBER_PERMISSIONS = [
    p.value
    for p in [
        Permission.CHANNELS_VIEW,
        Permission.MESSAGES_LIST,
        Permission.MESSAGES_CREATE,
        Permission.CHANNELS_MEMBERS_LIST,
        Permission.APPS_MANAGE,
    ]
]

DEFAULT_TOPIC_MEMBER_PERMISSIONS = [
    p.value
    for p in [
        Permission.CHANNELS_VIEW,
        Permission.MESSAGES_LIST,
        Permission.MESSAGES_CREATE,
        Permission.CHANNELS_MEMBERS_LIST,
    ]
]

DEFAULT_USER_PERMISSIONS = [p.value for p in [Permission.CHANNELS_CREATE]]
