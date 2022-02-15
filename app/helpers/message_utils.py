import logging
import re

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
