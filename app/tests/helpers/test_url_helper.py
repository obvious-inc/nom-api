import pytest

from app.helpers.urls import extract_unfurl_info_from_html, unfurl_url


class TestURLHelper:
    @pytest.mark.parametrize(
        "html, url, partial_expected",
        [
            ("<html><title>Twitter</title>", "", {"title": "Twitter"}),
            ('<html><meta property="og:site_name" content="Twitter" /><meta ...', "", {"title": "Twitter"}),
            (
                '<html>...<link rel="icon" type="image/png" href="/static/images/favicon.ico" sizes="32x32"/>...',
                "https://docs.expo.dev/push-notifications/sending-notifications/",
                {"favicon": "https://docs.expo.dev/static/images/favicon.ico"},
            ),
            (
                '<!DOCTYPE html><html lang="en"><head>...</style><link rel="shortcut icon" href="/favicon.ico" type="image/x-icon" /><title>',
                "https://deno.com/blog/v1.28",
                {"favicon": "https://deno.com/favicon.ico"},
            ),
        ],
    )
    @pytest.mark.asyncio
    async def test_extract_metatags(self, html, partial_expected, url):
        extracted_info = await extract_unfurl_info_from_html(html=html, url=url)
        assert partial_expected.items() <= extracted_info.items()

    @pytest.mark.parametrize(
        "url, partial_expected",
        [
            (
                "https://www.nytimes.com/2022/11/14/science/time-leap-second.html",
                {"title": "Time Has Run Out for the Leap Second - The New York Times"},
            ),
            (
                "https://www.tiktok.com/@abba/video/7166121198521175302",
                {"title": "Happy Birthday Frida! | TikTok"},
            ),
        ],
    )
    @pytest.mark.asyncio
    async def test_unfurl(self, url, partial_expected):
        extracted_info = await unfurl_url(url=url)
        assert partial_expected.items() <= extracted_info.items()

    @pytest.mark.asyncio
    async def test_unfurl_twitter_link(self):
        url = "https://twitter.com/SoVeryBritish/status/1591470202981875712"
        extracted_info = await unfurl_url(url=url)
        metatags = extracted_info.get("metatags")
        assert len(metatags) > 2
        assert str(metatags.get("og:description", "")).startswith("Having to go")
