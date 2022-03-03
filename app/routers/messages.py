import http

from fastapi import APIRouter, Body, Depends

from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.messages import MessageCreateSchema, MessageSchema, MessageUpdateSchema
from app.services.messages import (
    add_reaction_to_message,
    create_message,
    create_reply_message,
    delete_message,
    remove_reaction_from_message,
    update_message,
)

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


@router.patch(
    "/{message_id}",
    response_model=MessageSchema,
    summary="Update message",
)
async def patch_edit_message(
    message_id: str,
    update_data: MessageUpdateSchema = Body(...),
    current_user: User = Depends(get_current_user),
):
    return await update_message(message_id, update_data=update_data, current_user=current_user)


@router.delete(
    "/{message_id}",
    summary="Remove message",
    status_code=http.HTTPStatus.NO_CONTENT,
)
async def delete_remove_message(
    message_id: str,
    current_user: User = Depends(get_current_user),
):
    await delete_message(message_id, current_user=current_user)


@router.post(
    "/{message_id}/reactions/{reaction_emoji}",
    summary="Add reaction to message",
    status_code=http.HTTPStatus.NO_CONTENT,
)
async def post_add_reaction(
    message_id: str,
    reaction_emoji: str,
    current_user: User = Depends(get_current_user),
):
    await add_reaction_to_message(message_id, reaction_emoji=reaction_emoji, current_user=current_user)


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


@router.post(
    "/{message_id}/replies",
    response_model=MessageSchema,
    summary="Create reply to original message",
    status_code=http.HTTPStatus.CREATED,
)
async def post_create_reply(
    message_id: str,
    message: MessageCreateSchema = Body(...),
    current_user: User = Depends(get_current_user),
):
    return await create_reply_message(message_id, message_model=message, current_user=current_user)
