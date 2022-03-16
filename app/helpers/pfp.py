import logging
import re
from re import Pattern
from typing import Optional, Tuple

from app.helpers import cloudflare
from app.services.crud import update_item

logger = logging.getLogger(__name__)

OPENSEA_LINK_REGEX_PAT = re.compile(r".+?assets/(?P<contract>.+?)/(?P<token_id>.+?)\b")
RARIBLE_LINK_REGEX_PAT = re.compile(r".+?token/(?P<contract>.+?):(?P<token_id>.+?)\b")
LOOKS_RARE_LINK_REGEX_PAT = re.compile(r".+?collections/(?P<contract>.+?)/(?P<token_id>.+?)\b")
ETHERSCAN_NFT_LINK_REGEX_PAT = re.compile(r".+?nft/(?P<contract>.+?)/(?P<token_id>.+?)\b")
CONTRACT_TOKEN_REGEX_PAT = re.compile(r"(?P<contract>0x[a-f0-9]+)(\s|:|/)(?P<token_id>.+?)\b", flags=re.IGNORECASE)


async def _extract_contract_and_token_from_string(link: str, pattern: Pattern) -> Tuple[Optional[str], Optional[str]]:
    match = re.match(pattern, link)
    if not match:
        return None, None

    contract_address = match.group("contract")
    token_id = match.group("token_id")
    return contract_address, token_id


async def extract_contract_and_token_from_string(pfp_string: str) -> Tuple[Optional[str], Optional[str]]:
    if "opensea" in pfp_string:
        regex_patt = OPENSEA_LINK_REGEX_PAT
    elif "rarible" in pfp_string:
        regex_patt = RARIBLE_LINK_REGEX_PAT
    elif "looksrare" in pfp_string:
        regex_patt = LOOKS_RARE_LINK_REGEX_PAT
    elif "etherscan" in pfp_string and "nft" in pfp_string:
        regex_patt = ETHERSCAN_NFT_LINK_REGEX_PAT
    else:
        regex_patt = CONTRACT_TOKEN_REGEX_PAT

    return await _extract_contract_and_token_from_string(pfp_string, regex_patt)


async def upload_pfp_url_and_update_profile(input_str: str, image_url: str, profile, metadata: dict):
    cf_image = await cloudflare.upload_image_url(image_url, metadata=metadata)
    cf_id = cf_image.get("id")

    profile_pfp = profile.pfp
    if profile_pfp and profile_pfp.get("input", "") == input_str:
        profile_pfp["cf_id"] = cf_id
        await update_item(item=profile, data={"pfp": profile_pfp})
        logger.info(f"PFP for profile {profile.pk} uploaded to cloudflare successfully with id: {cf_id}")
