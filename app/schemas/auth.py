from typing import Optional

from pydantic import BaseModel, Field


class WalletMessageSchema(BaseModel):
    address: Optional[str] = None
    signed_at: Optional[str] = None


class AuthWalletSchema(BaseModel):
    message: WalletMessageSchema = Field()
    signature: str = Field()

    class Config:
        allow_population_by_field_name = True
        json_encoders = {WalletMessageSchema: dict}
        schema_extra = {
            "example": {
                "message": {
                    "address": "0x1231237072081028432784128371234898237233",
                    "signed_at": "2022-01-01T12:12:12.123Z",
                },
                "signature": "0x1231237072081028432784128371234898237233479",
            }
        }


class AccessTokenSchema(BaseModel):
    access_token: str = Field()
    token_type: str = Field(default="bearer")

    class Config:
        allow_population_by_field_name = True
        schema_extra = {
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIweDI1MDVmYTg2MTQwMDhGNTNGQjg1YmE0RTgwREFiOUZEZTUyNjYyNTMiLCJleHAiOjE2NDIwMjg2MjR9.bDZW6RHWpkQpwqkDopjSoiNDc2sHglWQ2TjdkM_5F84",
                "token_type": "bearer",
            }
        }
