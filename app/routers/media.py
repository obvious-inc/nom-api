import http
from typing import List

from fastapi import APIRouter, Depends, File, UploadFile

from app.dependencies import get_current_user
from app.helpers.cloudflare import upload_images
from app.models.user import User

router = APIRouter()


@router.post("/images", summary="Upload new image", status_code=http.HTTPStatus.CREATED)
async def create_upload_image_files(
    files: List[UploadFile] = File(...), current_user: User = Depends(get_current_user)
):
    images = await upload_images(files, prefix=str(current_user.id))
    return images
