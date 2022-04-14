import http

from fastapi import APIRouter, Depends

from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.sections import SectionSchema, SectionUpdateSchema
from app.services.sections import delete_section, update_section

router = APIRouter()


@router.patch("/{section_id}", summary="Update section", response_model=SectionSchema, status_code=http.HTTPStatus.OK)
async def patch_update_section(
    section_id: str, update_data: SectionUpdateSchema, current_user: User = Depends(get_current_user)
):
    return await update_section(section_id=section_id, update_data=update_data, current_user=current_user)


@router.delete("/{section_id}", summary="Delete section", status_code=http.HTTPStatus.NO_CONTENT)
async def delete_remove_section(section_id: str, current_user: User = Depends(get_current_user)):
    await delete_section(section_id=section_id, current_user=current_user)
