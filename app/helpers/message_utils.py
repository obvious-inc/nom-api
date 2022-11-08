import logging
import re
from typing import List, Optional, Tuple, Union

from bson import ObjectId

from app.helpers.list_utils import batch_list
from app.models.message import Message
from app.models.user import User
from app.schemas.messages import MessageCreateSchema, SystemMessageCreateSchema
from app.services.crud import get_item_by_id, get_items

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


async def get_node_mentions(node: dict) -> Optional[Tuple[str, str]]:
    node_type = node.get("type")
    if node_type == "user":
        return "user", str(node.get("ref"))
    elif node_type == "broadcast":
        mention_range = str(node.get("ref"))
        if mention_range not in MENTION_BROADCAST_RANGES:
            logger.warning(f"ignoring unknown broadcast range: {mention_range}")
            return None
        return "broadcast", mention_range
    else:
        return None


async def get_message_nodes_mentions(nodes: List[dict]) -> List[Tuple[str, str]]:
    mentions = []
    for node in nodes:
        node_mention = await get_node_mentions(node)
        if node_mention:
            mentions.append(node_mention)

        children = node.get("children")
        if not children:
            continue

        child_mentions = await get_message_nodes_mentions(children)
        if child_mentions:
            mentions.extend(child_mentions)

    return mentions


async def get_message_mentions(message: Message) -> List[Tuple[str, str]]:
    if not message.blocks:
        logger.warning(f"no blocks to fetch mentions from. [message={str(message.id)}")
        return []

    return await get_message_nodes_mentions(message.blocks)


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

    if el_type == "paragraph" or el_type == "attachments":
        return children
    elif el_type == "link":
        return f"[{children}]({element.get('url')})"
    elif el_type == "user":
        return f"@<u:{element.get('ref')}>"
    elif el_type == "broadcast":
        return f"@<b:{element.get('ref')}>"
    elif el_type == "image-attachment":
        return element.get("url", "")
    else:
        logger.warning(f"unknown element type: {el_type}")
        return ""


async def stringify_blocks(blocks: List[dict]) -> str:
    elements = []
    for block in blocks:
        elements.append(await stringify_element(block))

    text = "\n".join(elements)
    return text


async def get_raw_node(node: dict) -> str:
    text = node.get("text", "")
    if text:
        return text
    else:
        return await get_raw_element(node)


async def get_raw_element(element: dict) -> str:
    children = "".join([await get_raw_node(child) for child in element.get("children", [])])
    el_type = element.get("type")

    if el_type == "paragraph" or el_type == "attachments":
        return children
    elif el_type == "link":
        return element.get("url", "")
    elif el_type == "user":
        user = await get_item_by_id(id_=element.get("ref"), result_obj=User)
        return f"@{user.display_name or user.wallet_address}"
    elif el_type == "broadcast":
        return f"@{element.get('ref')}"
    elif el_type == "image-attachment":
        return element.get("url", "")
    else:
        logger.warning(f"unknown element type: {el_type}")
        return ""


async def get_raw_blocks(blocks: List[dict]):
    elements = []
    for block in blocks:
        elements.append(await get_raw_element(block))

    text = "\n".join(elements)
    return text


async def get_message_mentioned_users(message: Message) -> List[User]:
    user_ids = set()
    mentions = await get_message_mentions(message)
    for mention_type, mention_ref in mentions:
        logger.debug(f"found '{mention_type}' mention of @{mention_ref}")

        if mention_type == "user":
            user_ids.add(ObjectId(mention_ref))
        elif mention_type == "broadcast":
            logger.warning("broadcast mentions not supported yet")
            continue
        else:
            logger.error(f"unsupported mention type: {mention_type}")
            continue

    users = []
    async for batch_user_ids in batch_list(list(user_ids)):
        users.extend(await get_items(filters={"_id": {"$in": batch_user_ids}}, result_obj=User, limit=None))

    return users


async def is_message_empty(message_model: Union[MessageCreateSchema, SystemMessageCreateSchema]) -> bool:
    if not message_model.blocks or len(message_model.blocks) == 0:
        return True

    if len(message_model.blocks) > 1:
        return False

    single_block = message_model.blocks[0]

    if single_block.get("type") != "paragraph":
        return False

    paragraph_children = single_block.get("children", [])
    if len(paragraph_children) > 1:
        return False

    paragraph_child = paragraph_children[0]

    text = paragraph_child.get("text")
    if text == "":
        return True

    return False
