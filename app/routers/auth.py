import http

from fastapi import APIRouter, Body, Depends

from app.helpers.connection import get_db
from app.schemas.auth import AccessTokenSchema, AuthWalletSchema
from app.services.auth import generate_wallet_token

router = APIRouter()


@router.post(
    "/login",
    response_description="Generate access token",
    response_model=AccessTokenSchema,
    status_code=http.HTTPStatus.CREATED,
)
async def login_with_wallet(data: AuthWalletSchema = Body(...), db=Depends(get_db)):
    token = await generate_wallet_token(data)
    response = AccessTokenSchema(access_token=token)
    return response
