import http
from typing import Optional

from fastapi import APIRouter, Depends

from app.dependencies import get_current_user
from app.services.integrations import get_gifs_search

router = APIRouter(dependencies=[Depends(get_current_user)])


@router.get(
    "/giphy/search",
    summary="Fetch giphy gifs",
    status_code=http.HTTPStatus.OK,
)
async def search_giphy_gifs(q: str, media_filter: Optional[str] = None):
    return await get_gifs_search(search_term=q, media_filter=media_filter, provider="giphy")


@router.get(
    "/tenor/search",
    summary="Fetch tenor gifs",
    status_code=http.HTTPStatus.OK,
)
async def search_tenor_gifs(q: str, media_filter: Optional[str] = None):
    return await get_gifs_search(search_term=q, media_filter=media_filter, provider="tenor")
