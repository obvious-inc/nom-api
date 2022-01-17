from functools import cache

from ens import ENS
from eth_account.messages import encode_defunct
from eth_typing import ChecksumAddress
from eth_utils import ValidationError
from web3 import Web3

from app.config import get_settings


def checksum_address(address: str) -> ChecksumAddress:
    return Web3().toChecksumAddress(address)


def get_wallet_address_from_signed_message(message: str, signature: str) -> str:
    encoded_message = encode_defunct(text=message)
    try:
        address = Web3().eth.account.recover_message(encoded_message, signature=signature)
    except ValidationError as e:
        raise ValueError(e)
    return address


@cache
async def get_ens_primary_name_for_address(wallet_address: str) -> str:
    settings = get_settings()
    web3_client = Web3(Web3.WebsocketProvider(settings.web3_provider_url_ws))
    wallet_address = checksum_address(wallet_address)
    ens_name = ENS.fromWeb3(web3_client).name(wallet_address)
    return ens_name
