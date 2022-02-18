import pytest

from app.helpers.message_utils import get_message_content_mentions


class TestMessageUtils:
    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "content, mentions",
        [
            ("hey @<u:61ee8893e89d5fe35c198ef2>", [("user", "61ee8893e89d5fe35c198ef2")]),
            (
                "props to @<u:61ee8893e89d5fe35c198ef2> and @<u:61ee8893e89d5fe35c198ef1>",
                [("user", "61ee8893e89d5fe35c198ef2"), ("user", "61ee8893e89d5fe35c198ef1")],
            ),
            ("props to @prego and @<u:61ee8893e89d5fe35c198ef1>", [("user", "61ee8893e89d5fe35c198ef1")]),
            ("props @here and @everyone", []),
            ("props to role @<r:61ee8893e89d5fe35c198ef1>", []),
            (
                "@<u:61ee8893e89d5fe35c198ef2>@<u:61ee8893e89d5fe35c198ef1>@<u:61ee8893e89d5fe35c198ef2>",
                [
                    ("user", "61ee8893e89d5fe35c198ef2"),
                    ("user", "61ee8893e89d5fe35c198ef1"),
                    ("user", "61ee8893e89d5fe35c198ef2"),
                ],
            ),
        ],
    )
    async def test_get_mentions(self, content, mentions):
        assert await get_message_content_mentions(content) == mentions
