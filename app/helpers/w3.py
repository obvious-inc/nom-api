import logging
import re

from eth_account.messages import SignableMessage, encode_defunct, encode_structured_data
from eth_typing import ChecksumAddress
from eth_utils import ValidationError
from hexbytes import HexBytes
from web3 import Web3
from web3.exceptions import ContractLogicError

from app.config import get_settings
from app.helpers.abis import erc721_abi, erc1155_abi
from app.helpers.alchemy import get_image_url as get_alchemy_image_url
from app.helpers.alchemy import get_nft as get_alchemy_nft
from app.helpers.simplehash import get_image_url as get_simplehash_image_url
from app.helpers.simplehash import get_nft as get_simplehash_nft

logger = logging.getLogger(__name__)


def checksum_address(address: str) -> ChecksumAddress:
    return Web3.toChecksumAddress(address)


def get_wallet_address_from_signed_message(message: str, signature: str) -> str:
    encoded_message = encode_defunct(text=message)
    try:
        address = Web3().eth.account.recover_message(encoded_message, signature=signature)
    except ValidationError as e:
        raise ValueError(e)
    return address


async def _replace_with_cloudflare_gateway(token_image_url: str) -> str:
    ipfs_re = r"(?:ipfs:\/\/|ipfs.io\/)(?:ipfs\/)?(.+)"
    pinata_ipfs_re = r"pinata\.cloud\/(?:ipfs\/)?(.+)"
    ipfs_match = re.findall(ipfs_re, token_image_url, flags=re.IGNORECASE)
    if ipfs_match:
        image_path = ipfs_match[0]
        return f"https://cloudflare-ipfs.com/ipfs/{image_path}"

    pinata_match = re.findall(pinata_ipfs_re, token_image_url, flags=re.IGNORECASE)
    if pinata_match:
        image_path = pinata_match[0]
        return f"https://cloudflare-ipfs.com/ipfs/{image_path}"

    return token_image_url


async def get_nft(contract_address: str, token_id: str, provider: str = "alchemy") -> dict:
    if provider == "alchemy":
        return await get_alchemy_nft(contract_address, token_id)
    elif provider == "simplehash":
        return await get_simplehash_nft(contract_address, token_id)
    else:
        raise NotImplementedError("no other providers implemented")


async def get_nft_image_url(nft, provider: str = "alchemy"):
    if provider == "alchemy":
        image_url = await get_alchemy_image_url(nft)
    elif provider == "simplehash":
        image_url = await get_simplehash_image_url(nft)
    else:
        raise NotImplementedError("no other providers implemented")

    return await _replace_with_cloudflare_gateway(token_image_url=image_url)


async def verify_token_ownership(contract_address: str, token_id: str, wallet_address: str) -> bool:
    settings = get_settings()
    web3_client = Web3(Web3.WebsocketProvider(settings.web3_provider_url_ws))
    contract_address = checksum_address(contract_address)
    wallet_address = checksum_address(wallet_address)
    token_id_int = int(token_id)

    try:
        contract = web3_client.eth.contract(address=contract_address, abi=erc721_abi)
        current_owner = contract.functions.ownerOf(token_id_int).call()
        return current_owner == wallet_address
    except ContractLogicError:
        contract = web3_client.eth.contract(address=contract_address, abi=erc1155_abi)
        balance = contract.functions.balanceOf(wallet_address, token_id_int).call()
        return balance > 0
    except Exception as e:
        logger.warning(f"exception verifying ownership of {contract_address}/{token_id_int} for {wallet_address} | {e}")
        return False


async def get_signable_message_for_broadcast_identity_payload(broadcast_identity_payload: dict) -> SignableMessage:
    signable_message: SignableMessage = encode_structured_data(
        {
            "types": {
                "EIP712Domain": [
                    {"name": "name", "type": "string"},
                    {"name": "version", "type": "string"},
                ],
                "SignerAddress": [{"name": "public_key", "type": "string"}],
                "BroadcastIdentityBody": [{"name": "signers", "type": "SignerAddress[]"}],
                "Signer": [
                    {"name": "account", "type": "address"},
                    {"name": "timestamp", "type": "uint256"},
                    {"name": "type", "type": "string"},
                    {"name": "body", "type": "BroadcastIdentityBody"},
                ],
            },
            "domain": {"name": "NewShades", "version": "0.0.1"},
            "primaryType": "Signer",
            "message": broadcast_identity_payload,
        }
    )

    return signable_message


async def get_wallet_address_from_broadcast_identity_payload(broadcast_identity_payload: dict, signature: str) -> str:
    signable_message = await get_signable_message_for_broadcast_identity_payload(broadcast_identity_payload)
    bytes_sig = HexBytes(signature)
    return Web3().eth.account.recover_message(signable_message, signature=bytes_sig)
