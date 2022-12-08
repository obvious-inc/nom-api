import logging

from app.helpers.w3 import checksum_address
from app.models.user import WhitelistedWallet
from app.services.crud import get_item

logger = logging.getLogger(__name__)


async def is_wallet_whitelisted(wallet_address: str) -> bool:
    wallet_address_checksum = checksum_address(wallet_address)
    exists = await get_item(filters={"wallet_address": wallet_address_checksum}, result_obj=WhitelistedWallet)
    return exists is not None


async def whitelist_wallet(wallet_address: str) -> WhitelistedWallet:
    wallet_address_checksum = checksum_address(wallet_address)
    db_object = WhitelistedWallet(wallet_address=wallet_address_checksum)
    await db_object.commit()
    logger.info("Object created. [object_type=%s, object_id=%s]", WhitelistedWallet.__name__, str(db_object.id))
    return db_object
