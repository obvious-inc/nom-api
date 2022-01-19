import http

from fastapi import APIRouter, Body, Depends
from starlette.background import BackgroundTasks

from app.dependencies import get_current_user
from app.helpers.database import get_db
from app.models.user import User
from app.schemas.messages import MessageCreateSchema, MessageSchema
from app.services.messages import create_message

router = APIRouter()


@router.post(
    "",
    response_description="Create new message",
    response_model=MessageSchema,
    status_code=http.HTTPStatus.CREATED,
)
async def post_create_message(
    message: MessageCreateSchema = Body(...),
    db=Depends(get_db),
    current_user: User = Depends(get_current_user),
    background_tasks: BackgroundTasks = None,
):
    return await create_message(message, current_user=current_user, background_tasks=background_tasks)
