import http

from fastapi import APIRouter, Body, Depends

from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.messages import MessageCreateSchema, MessageReactionCreateSchema, MessageSchema
from app.services.messages import add_reaction_to_message, create_message, remove_reaction_from_message

router = APIRouter()


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
    return await create_message(message, current_user=current_user)


@router.post(
    "/{message_id}/reactions",
    summary="Add reaction to message",
    status_code=http.HTTPStatus.NO_CONTENT,
)
async def post_add_reaction(
    message_id: str,
    reaction: MessageReactionCreateSchema = Body(...),
    current_user: User = Depends(get_current_user),
):
    await add_reaction_to_message(message_id, reaction_model=reaction, current_user=current_user)


@router.delete(
    "/{message_id}/reactions/{reaction_emoji}",
    summary="Remove reaction to message",
    status_code=http.HTTPStatus.NO_CONTENT,
)
async def delete_remove_reaction(
    message_id: str,
    reaction_emoji: str,
    current_user: User = Depends(get_current_user),
):
    await remove_reaction_from_message(message_id, reaction_emoji, current_user=current_user)
