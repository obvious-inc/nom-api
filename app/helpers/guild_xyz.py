import logging

import aiohttp

from app.models.user import User

logger = logging.getLogger(__name__)


async def get_guild_member_roles(guild_id: str, member_wallet_addr: str):
    roles = []
    async with aiohttp.ClientSession() as session:
        async with session.get(f"https://api.guild.xyz/v1/guild/access/{guild_id}/{member_wallet_addr}") as response:
            if not response.ok:
                response.raise_for_status()
            json_response = await response.json()
            for role in json_response:
                access = role.get("access")
                if access is True:
                    roles.append(role)
                    logger.debug(f"{member_wallet_addr} has access to guild {guild_id} with role: {role}")

    return roles


async def is_user_eligible_for_guild(user: User, guild_id: str):
    wallet_address = user.wallet_address
    roles = await get_guild_member_roles(guild_id=guild_id, member_wallet_addr=wallet_address)
    is_eligible = len(roles) > 0
    logger.info(f"is user ({str(user.id)}) with wallet {wallet_address} eligible for guild {guild_id}? {is_eligible}")
    return is_eligible
