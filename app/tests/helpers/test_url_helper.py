import pytest

from app.helpers.urls import extract_unfurl_info_from_html


class TestURLHelper:
    @pytest.mark.parametrize(
        "html, partial_expected",
        [
            ("<html><title>Twitter</title>", {"title": "Twitter"}),
            ('<html><meta property="og:site_name" content="Twitter" /><meta ...', {"title": "Twitter"}),
        ],
    )
    @pytest.mark.asyncio
    async def test_extract_metatags(self, html, partial_expected):
        extracted_info = await extract_unfurl_info_from_html(html=html)
        assert partial_expected.items() <= extracted_info.items()
