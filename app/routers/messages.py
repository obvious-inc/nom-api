import http
import logging

from fastapi import APIRouter, Body, Depends

from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.messages import MessageCreateSchema, MessageSchema
from app.services.messages import create_message

router = APIRouter()

logger = logging.getLogger(__name__)


@router.post(
    "",
    response_description="Create new message",
    response_model=MessageSchema,
    status_code=http.HTTPStatus.CREATED,
)
async def post_create_message(
    message: MessageCreateSchema = Body(...),
    current_user: User = Depends(get_current_user),
):
    logger.debug(f"creating message: {message}")
    return await create_message(message, current_user=current_user)
