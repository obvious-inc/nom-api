import pytest

from app.helpers.lens import LensClient


class TestLensProtocolHelper:
    @pytest.mark.skip("3rd party API dependency")
    @pytest.mark.asyncio
    async def test_fetch_lens_protocol_profile(self):
        wallet_address = "0x3A5bd1E37b099aE3386D13947b6a90d97675e5e3"
        lens_profile = await LensClient().get_default_profile(wallet_address=wallet_address)
        expected_data = {"id": "0x0d", "handle": "yoginth.lens"}
        assert expected_data.items() <= lens_profile.items()
