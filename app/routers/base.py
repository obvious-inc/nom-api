from fastapi import APIRouter, Depends

from app.dependencies import get_current_user
from app.models.user import User
from app.services.base import get_connection_ready_data

router = APIRouter()


@router.get("/", include_in_schema=False)
def get_index():
    return {"status": "ok"}


@router.get("/ready", include_in_schema=False)
async def get_connection_ready(current_user: User = Depends(get_current_user)):
    return await get_connection_ready_data(current_user=current_user)
