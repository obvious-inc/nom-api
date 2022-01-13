import http

from fastapi import APIRouter, Body

from app.models.auth import AuthWalletModel, AccessTokenModel
from app.services.auth import generate_wallet_token

router = APIRouter()


@router.post('/login',
             response_description="Generate access token",
             response_model=AccessTokenModel,
             status_code=http.HTTPStatus.CREATED
             )
async def create_token(data: AuthWalletModel = Body(...)):
    token = await generate_wallet_token(data.dict())
    response = AccessTokenModel(access_token=token)
    return response
