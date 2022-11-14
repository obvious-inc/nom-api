import pytest

from app.helpers.urls import extract_unfurl_info_from_html


class TestURLHelper:
    @pytest.mark.parametrize(
        "html, url, partial_expected",
        [
            ("<html><title>Twitter</title>", None, {"title": "Twitter"}),
            ('<html><meta property="og:site_name" content="Twitter" /><meta ...', None, {"title": "Twitter"}),
            (
                '<html>...<link rel="icon" type="image/png" href="/static/images/favicon.ico" sizes="32x32"/>...',
                "https://docs.expo.dev/push-notifications/sending-notifications/",
                {"favicon": "https://docs.expo.dev/static/images/favicon.ico"},
            ),
        ],
    )
    @pytest.mark.asyncio
    async def test_extract_metatags(self, html, partial_expected, url):
        extracted_info = await extract_unfurl_info_from_html(html=html, url=url)
        assert partial_expected.items() <= extracted_info.items()
