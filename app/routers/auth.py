import http

from fastapi import APIRouter, Body, Depends

from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.auth import AccessTokenSchema, AuthWalletSchema, RefreshTokenCreateSchema
from app.services.auth import create_refresh_token, generate_wallet_token, revoke_tokens

router = APIRouter()


@router.post(
    "/login",
    response_description="Generate access token",
    response_model=AccessTokenSchema,
    status_code=http.HTTPStatus.CREATED,
)
async def login_with_wallet(data: AuthWalletSchema = Body(...)):
    return await generate_wallet_token(data)


@router.post(
    "/refresh",
    summary="Refresh access token",
    response_model=AccessTokenSchema,
    status_code=http.HTTPStatus.CREATED,
)
async def post_refresh_token(
    token: RefreshTokenCreateSchema = Body(...),
):
    return await create_refresh_token(token)


@router.post("/revoke", summary="Revoke all tokens", status_code=http.HTTPStatus.NO_CONTENT)
async def post_revoke_tokens(current_user: User = Depends(get_current_user)):
    await revoke_tokens(current_user=current_user)
