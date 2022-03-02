from typing import List

import pytest

from app.helpers.message_utils import get_message_content_mentions, stringify_blocks


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

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "blocks, text",
        [
            ([], ""),
            (
                [{"type": "paragraph", "children": [{"text": "hey"}]}],
                "hey",
            ),
            (
                [
                    {"type": "paragraph", "children": [{"text": "hey"}]},
                    {"type": "paragraph", "children": [{"text": "there"}]},
                    {"type": "paragraph", "children": []},
                    {"type": "paragraph", "children": [{"text": "multiline text"}]},
                ],
                "hey\nthere\n\nmultiline text",
            ),
            (
                [
                    {
                        "type": "paragraph",
                        "children": [{"text": "hey "}, {"text": "bold", "bold": True}, {"text": " text"}],
                    },
                ],
                "hey **bold** text",
            ),
            (
                [
                    {
                        "type": "paragraph",
                        "children": [{"text": "hey "}, {"text": "italic", "italic": True}, {"text": " text"}],
                    },
                ],
                "hey _italic_ text",
            ),
            (
                [
                    {
                        "type": "paragraph",
                        "children": [{"text": "Hi "}, {"text": "there", "bold": True}, {"text": "!"}],
                    },
                    {
                        "type": "paragraph",
                        "children": [
                            {"text": "Here's a link: "},
                            {
                                "type": "link",
                                "url": "http://google.com/",
                                "children": [{"text": "google", "bold": True}],
                            },
                        ],
                    },
                ],
                "Hi **there**!\nHere's a link: [**google**](http://google.com/)",
            ),
            (
                [
                    {
                        "type": "paragraph",
                        "children": [
                            {"text": "hey "},
                            {"type": "user", "ref": "123123123"},
                            {"text": ", you around?"},
                        ],
                    },
                ],
                "hey <@u:123123123>, you around?",
            ),
        ],
    )
    async def test_stringify_blocks(self, blocks: List[dict], text: str):
        assert await stringify_blocks(blocks) == text
