import logging
from typing import List

from app.models.user import WhitelistedWallet
from app.services.crud import get_items

logger = logging.getLogger(__name__)


async def get_whitelisted_wallets() -> List[WhitelistedWallet]:
    return await get_items(filters={}, result_obj=WhitelistedWallet, limit=None)


async def is_wallet_whitelisted(wallet_address: str) -> bool:
    whitelisted_addresses = await get_whitelisted_wallets()
    return wallet_address.lower() in [obj.wallet_address.lower() for obj in whitelisted_addresses]


async def whitelist_wallet(wallet_address: str) -> WhitelistedWallet:
    db_object = WhitelistedWallet(wallet_address=wallet_address)
    await db_object.commit()
    logger.info("Object created. [object_type=%s, object_id=%s]", WhitelistedWallet.__name__, str(db_object.id))
    return db_object
