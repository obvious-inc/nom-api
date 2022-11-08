import http
from typing import List

from fastapi import APIRouter, Body, Depends, File, UploadFile

from app.dependencies import get_current_user
from app.models.user import User
from app.services.media import upload_files, upload_image_files, upload_image_from_url

router = APIRouter()


@router.post("", summary="Upload new media", status_code=http.HTTPStatus.CREATED)
async def create_upload_files(
    prefix: str, files: List[UploadFile] = File(...), current_user: User = Depends(get_current_user)
):
    return await upload_files(files, prefix=prefix, current_user=current_user)


@router.post("/images", summary="Upload new image", status_code=http.HTTPStatus.CREATED)
async def create_upload_image_files(
    files: List[UploadFile] = File(...), current_user: User = Depends(get_current_user)
):
    return await upload_image_files(files, current_user=current_user)


@router.post("/url", summary="Upload new image from URL", status_code=http.HTTPStatus.CREATED)
async def create_upload_image_url(url: str = Body(..., embed=True), current_user: User = Depends(get_current_user)):
    return await upload_image_from_url(url, current_user=current_user)
