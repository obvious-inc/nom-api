import logging
import re
from typing import List, Tuple

from app.models.message import Message

logger = logging.getLogger(__name__)

MENTION_REFS_PATTERN = re.compile(r"(?!\b|\s)@<(?P<type>\w):(?P<id>[0-9a-f]{24})>", flags=re.IGNORECASE)
BROADCAST_MENTION_REFS_PATTERN = re.compile(r"(?!\b|\s)@<(?P<type>b):(?P<range>.+?)>", flags=re.IGNORECASE)

MENTION_TYPE_MAPPING = {"u": "user", "b": "broadcast"}
MENTION_BROADCAST_RANGES = ["here", "channel", "everyone"]


async def get_message_content_mentions(content: str) -> List[Tuple[str, str]]:
    mentions = []
    for match in re.finditer(MENTION_REFS_PATTERN, content):
        mention_type_matched = match.group("type")
        mention_type = MENTION_TYPE_MAPPING.get(mention_type_matched)
        if not mention_type:
            logger.warning(f"unexpected matched mention type '{mention_type_matched}' in {match.group()}")
            continue

        mention_id = match.group("id")
        mentions.append((mention_type, mention_id))

    for match in re.finditer(BROADCAST_MENTION_REFS_PATTERN, content):
        mention_type_matched = match.group("type")
        mention_type = MENTION_TYPE_MAPPING.get(mention_type_matched)
        if not mention_type:
            logger.warning(f"unexpected matched mention type '{mention_type_matched}' in {match.group()}")
            continue

        mention_range = match.group("range")
        if mention_range not in MENTION_BROADCAST_RANGES:
            logger.warning(f"ignoring unknown broadcast range: {mention_range}")
            continue

        mentions.append((mention_type, mention_range))

    return mentions


async def get_message_mentions(message: Message) -> List[Tuple[str, str]]:
    if not message.content and message.blocks:
        message.content = await stringify_blocks(message.blocks)

    if not message.content:
        raise Exception("can't fetch mentions from message without content. [message=%s]", str(message.id))

    return await get_message_content_mentions(message.content)


async def blockify_content(content: str) -> List[dict]:
    paragraphs = content.split("\n")
    blocks = [{"type": "paragraph", "children": [{"text": paragraph}]} for paragraph in paragraphs]
    return blocks


async def stringify_text_node(text_node):
    text = text_node.get("text", "")
    if text_node.get("bold"):
        text = f"*{text}*"
    if text_node.get("italic"):
        text = f"_{text}_"
    if text_node.get("strikethrough"):
        text = f"~{text}~"

    return text


async def stringify_node(node: dict) -> str:
    text = node.get("text")
    if text:
        return await stringify_text_node(node)
    else:
        return await stringify_element(node)


async def stringify_element(element: dict) -> str:
    children = "".join([await stringify_node(child) for child in element.get("children", [])])
    el_type = element.get("type")

    if el_type == "paragraph":
        return children
    elif el_type == "link":
        return f"[{children}]({element.get('url')})"
    elif el_type == "user":
        return f"@<u:{element.get('ref')}>"
    elif el_type == "broadcast":
        return f"@<b:{element.get('ref')}>"
    else:
        logger.warning(f"unknown element type: {el_type}")
        return ""


async def stringify_blocks(blocks: List[dict]) -> str:
    elements = []
    for block in blocks:
        elements.append(await stringify_element(block))

    text = "\n".join(elements)
    return text
