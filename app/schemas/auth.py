from typing import List, Optional

from pydantic import BaseModel, Field

from app.schemas.base import APIBaseCreateSchema


class AuthWalletSchema(BaseModel):
    message: str = Field()
    signature: str = Field()
    address: str = Field()
    signed_at: str = Field()
    nonce: int = Field()

    class Config:
        allow_population_by_field_name = True
        schema_extra = {
            "example": {
                "message": "NewShades wants you to sign in with your web3 account\n0x123123707208102843278412837123...",
                "signature": "0x04cc5c3082e888cb28e99b78e7eb7b75a2fed2000083026683643e65356304d166eb0c27d69c9bccdfc...",
                "address": "0x1231237072081028432784128371234898237233",
                "signed_at": "2022-01-01T12:12:12.123Z",
                "nonce": 123123,
            }
        }


class AccessTokenSchema(BaseModel):
    access_token: str = Field()
    refresh_token: str = Field()
    token_type: str = Field(default="bearer")

    class Config:
        allow_population_by_field_name = True
        schema_extra = {
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.....bDZW6RHWpkQpwqkDopjSoiNDc2sHglWQ2TjdkM_1234",
                "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6Ikpasdfa.....bDZW6RHWpkQpwqkDopjSoiNDc2sHglWQ2TjdkM_1234",
                "token_type": "bearer",
            }
        }


class RefreshTokenCreateSchema(APIBaseCreateSchema):
    user: Optional[str]
    app: Optional[str]
    refresh_token: str
    scopes: Optional[List[str]] = []

    class Config:
        allow_population_by_field_name = True
        schema_extra = {
            "example": {
                "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6Ikpasdfa.....bDZW6RHWpkQpwqkDopjSoiNDc2sHglWQ2TjdkM_1234",
                "scopes": ["messages.list", "messages.create"],
            }
        }


class AuthorizationCodeCreateSchema(APIBaseCreateSchema):
    app: str
    code: str
    client_id: str
    redirect_uri: str
    response_type: str
    scope: str
    auth_time: int
    expires_in: int
    nonce: Optional[str] = ""
    channel: str

    class Config:
        allow_population_by_field_name = True


class AccountIdentityHeaders(BaseModel):
    signature_scheme: str
    hash_scheme: str
    signature: str


class OperationPayload(BaseModel):
    account: str
    timestamp: int
    type: str
    body: dict


class AccountBroadcastIdentitySchema(BaseModel):
    headers: AccountIdentityHeaders
    payload: OperationPayload

    class Config:
        allow_population_by_field_name = True
        schema_extra = {
            "example": {
                "headers": {
                    "signature_scheme": "EIP-712",
                    "hash_scheme": "SHA256",
                    "signature": "0x123123123123123",
                },
                "payload": {
                    "account": "0x1231237072081028432784128371234898237233",
                    "timestamp": 123123123,
                    "type": "account-broadcast",
                    "body": {
                        "signers": ["0x12312370720810284327841283712348982372331231237072081028432784"],
                    },
                },
            }
        }
