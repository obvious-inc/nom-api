import logging

import aiohttp

from app.models.user import User

logger = logging.getLogger(__name__)

#
# async def get_guild(guild_id: int):
#     async with aiohttp.ClientSession() as session:
#         async with session.get(f"https://api.guild.xyz/v1/guild/{guild_id}") as response:
#             response.raise_for_status()
#             guild = await response.json()
#             return guild


async def get_guild_member_roles(guild_id: str, member_wallet_addr: str):
    roles = []
    async with aiohttp.ClientSession() as session:
        async with session.get(f"https://api.guild.xyz/v1/guild/access/{guild_id}/{member_wallet_addr}") as response:
            json_response = await response.json()
            for role in json_response:
                access = role.get("access")
                if access:
                    roles.append(role)

    return roles


#
# async def get_user_guild_roles(guild_id: str, user: User):
#     # Guild: check access from wallet address to specific guild id
#     # https://api.guild.xyz/v1/guild/access/1985/0x4977A4b74D3a81dB4c462d9073E10796d0cEE333
#     wallet_address = user.wallet_address
#
#     guild = await get_guild(guild_id)
#     logger.debug(f"fetched guild {guild.get('name')} ({guild.get('id')})")
#
#     roles = await get_guild_member_roles(guild_id=guild_id, member_wallet_addr=wallet_address)
#     logger.debug(f"{user.id} has the following roles in guild '{guild.get('name')}': {roles}")
#
#     return roles


async def is_user_eligble_for_guild(user: User, guild_id: str):
    wallet_address = user.wallet_address
    roles = await get_guild_member_roles(guild_id=guild_id, member_wallet_addr=wallet_address)
    return len(roles) > 0
