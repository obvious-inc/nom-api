from typing import List

DEFAULT_CHUNK_SIZE = 90


async def batch_list(list_: List, chunk_size: int = DEFAULT_CHUNK_SIZE):
    total_length = len(list_)
    for ndx in range(0, total_length, chunk_size):
        yield list_[ndx : min(ndx + chunk_size, total_length)]
