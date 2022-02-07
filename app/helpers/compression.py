import json
import logging
import sys
import zlib
from base64 import b64encode

logger = logging.getLogger(__name__)


def _zlib_compress(data: str):
    bytes_data = data.encode("utf-8")
    b64 = b64encode(zlib.compress(bytes_data))
    compressed_data = b64.decode("ascii")
    return compressed_data


async def compress_data(data: dict, compression_type="zlib"):
    json_data = json.dumps(data)
    original_size = sys.getsizeof(json_data)
    if compression_type == "zlib":
        compressed_data = _zlib_compress(json_data)
    else:
        raise NotImplementedError(f"unknown compression type: {compression_type}")

    compressed_size = sys.getsizeof(compressed_data)
    logger.debug(
        "compressed original data from %s to %s bytes using %s", original_size, compressed_size, compression_type
    )
    return compressed_data
