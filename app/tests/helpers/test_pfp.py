import pytest

from app.helpers.pfp import extract_contract_and_token_from_string


class TestPFP:
    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "string_input, contract_address, token_id",
        [
            (
                "https://opensea.io/assets/0x5180db8f5c931aae63c74266b211f580155ecac8/8900",
                "0x5180db8f5c931aae63c74266b211f580155ecac8",
                "8900",
            ),
            (
                "https://opensea.io/assets/0x5180db8f5c931aae63c74266b211f580155ecac8/8900?test=1",
                "0x5180db8f5c931aae63c74266b211f580155ecac8",
                "8900",
            ),
            (
                "https://rinkeby.rarible.com/token/0xbed7c050b61e9e35f4a8e412dfcd2d34a05df267:1?tab=detail",
                "0xbed7c050b61e9e35f4a8e412dfcd2d34a05df267",
                "1",
            ),
            (
                "https://rarible.com/token/0xbed7c050b61e9e35f4a8e412dfcd2d34a05df267:1?tab=detail",
                "0xbed7c050b61e9e35f4a8e412dfcd2d34a05df267",
                "1",
            ),
            (
                "https://looksrare.org/collections/0x3903d4fFaAa700b62578a66e7a67Ba4cb67787f9/2880",
                "0x3903d4fFaAa700b62578a66e7a67Ba4cb67787f9",
                "2880",
            ),
            (
                "https://etherscan.io/nft/0xf07468ead8cf26c752c676e43c814fee9c8cf402/7399",
                "0xf07468ead8cf26c752c676e43c814fee9c8cf402",
                "7399",
            ),
            ("0x5180db8f5c931aae63c74266b211f580155ecac8/8900", "0x5180db8f5c931aae63c74266b211f580155ecac8", "8900"),
            ("0x5180db8f5c931aae63c74266b211f580155ecac8 8900", "0x5180db8f5c931aae63c74266b211f580155ecac8", "8900"),
            ("0x5180db8f5c931aae63c74266b211f580155ecac8:8900", "0x5180db8f5c931aae63c74266b211f580155ecac8", "8900"),
        ],
    )
    async def test_extract_contract_address_and_token_marketplaces(self, string_input, contract_address, token_id):
        assert await extract_contract_and_token_from_string(string_input) == (contract_address, token_id)
