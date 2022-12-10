import http
from typing import Optional

from fastapi import APIRouter, Depends

from app.dependencies import get_current_user
from app.services.integrations import generate_dalle_image, get_gifs_search, talk_to_chatgpt

router = APIRouter(dependencies=[Depends(get_current_user)])


@router.get(
    "/giphy/search",
    summary="Fetch giphy gifs",
    status_code=http.HTTPStatus.OK,
    include_in_schema=False,
)
async def search_giphy_gifs(q: str, media_filter: Optional[str] = None):
    return await get_gifs_search(search_term=q, media_filter=media_filter, provider="giphy")


@router.get(
    "/tenor/search",
    summary="Fetch tenor gifs",
    status_code=http.HTTPStatus.OK,
    include_in_schema=False,
)
async def search_tenor_gifs(q: str, media_filter: Optional[str] = None):
    return await get_gifs_search(search_term=q, media_filter=media_filter, provider="tenor")


@router.post(
    "/dalle/generate",
    summary="Generate DALL-E image",
    status_code=http.HTTPStatus.CREATED,
    include_in_schema=False,
)
async def post_generate_dalle_image(prompt: str):
    return await generate_dalle_image(prompt=prompt)


@router.post(
    "/chatgpt",
    summary="Talk to ChatGPT",
    status_code=http.HTTPStatus.CREATED,
    include_in_schema=False,
)
async def post_talk_chatgpt(message: str):
    return await talk_to_chatgpt(message=message)
