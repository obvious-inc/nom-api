import http
from typing import List

from fastapi import HTTPException, UploadFile

from app.config import get_settings
from app.helpers.aws import upload_file
from app.helpers.cloudflare import upload_image_url, upload_images
from app.models.user import User


async def upload_files(files: List[UploadFile], current_user: User, prefix: str = None):
    settings = get_settings()

    if not prefix:
        raise HTTPException(status_code=http.HTTPStatus.UNPROCESSABLE_ENTITY, detail="Missing 'prefix' for media")

    files_list = []
    for file in files:
        file_id = "/".join([prefix, str(current_user.id), file.filename])
        path = f"{settings.cdn_media_folder}/{file_id}"
        await upload_file(file=file.file, filename=path, content_type=file.content_type)
        file_url = f"{settings.cdn_url}/{path}"
        file_data = {"id": file_id, "filename": file.filename, "url": file_url}
        files_list.append(file_data)

    return files_list


async def upload_image_files(images: List[UploadFile], current_user: User):
    return await upload_images(
        images,
        prefix=str(current_user.id),
    )


async def upload_image_from_url(image_url: str, current_user: User) -> dict:
    return await upload_image_url(image_url=image_url, prefix=str(current_user.pk))
