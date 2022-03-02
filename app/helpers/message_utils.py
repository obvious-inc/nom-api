import logging
import re
from typing import List

logger = logging.getLogger(__name__)

MENTION_REFS_PATTERN = re.compile(r"(?!\b|\s)@<(?P<type>\w):(?P<id>[0-9a-f]{24})>", flags=re.IGNORECASE)
MENTION_TYPE_MAPPING = {"u": "user"}


async def get_message_content_mentions(content):
    mentions = []
    for match in re.finditer(MENTION_REFS_PATTERN, content):
        mention_type_matched = match.group("type")
        mention_type = MENTION_TYPE_MAPPING.get(mention_type_matched)
        if not mention_type:
            logger.warning(f"unexpected matched mention type '{mention_type_matched}' in {match.group()}")
            continue

        mention_id = match.group("id")
        mentions.append((mention_type, mention_id))

    return mentions


async def blockify_content(content: str) -> List[dict]:
    paragraphs = content.split("\n")
    blocks = [{"type": "paragraph", "children": [{"text": paragraph}]} for paragraph in paragraphs]
    return blocks


async def stringify_paragraph(paragraph_block):
    paragraph_text = ""
    for element in paragraph_block.get("children"):
        text = element.get("text")
        if element.get("bold"):
            paragraph_text += f"**{text}**"
        elif element.get("italic"):
            paragraph_text += f"*{text}*"
        elif element.get("strikethrough"):
            paragraph_text += f"~~{text}~~"
        elif element.get("type") == "user":
            ref = element.get("ref")
            paragraph_text += f"<@u:{ref}>"
        else:
            paragraph_text += text
    return paragraph_text


async def stringify_blocks(blocks: List[dict]) -> str:
    text_lines = []
    for block in blocks:
        logger.debug(f"block: {block}")
        parsed_text = ""
        block_type = block.get("type")
        if block_type in ["paragraph", "link"]:
            parsed_text = await stringify_paragraph(block)
        else:
            logger.warning(f"unknown block type: {block_type}")

        logger.debug(f"parsed text: {parsed_text}")
        text_lines.append(parsed_text)

    text = "\n".join(text_lines)
    logger.debug(f"text: {text}")
    return text
