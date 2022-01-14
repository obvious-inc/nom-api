import http

from fastapi import APIRouter, Body

from app.schemas.auth import AuthWalletSchema, AccessTokenSchema
from app.services.auth import generate_wallet_token

router = APIRouter()


@router.post('/login',
             response_description="Generate access token",
             response_model=AccessTokenSchema,
             status_code=http.HTTPStatus.CREATED
             )
async def login_with_wallet(data: AuthWalletSchema = Body(...)):
    token = await generate_wallet_token(data.dict())
    response = AccessTokenSchema(access_token=token)
    return response
