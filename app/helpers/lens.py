from gql import Client, gql
from gql.transport.aiohttp import AIOHTTPTransport

from app.config import get_settings
from app.models.user import User
from app.services.crud import update_item


class LensClient:
    def __init__(self):
        self.client = Client(transport=AIOHTTPTransport(url=get_settings().lens_protocol_endpoint))

    async def get_default_profile(self, wallet_address: str):
        async with self.client as session:
            query = gql(
                """
                query($request: DefaultProfileRequest!) {
                  defaultProfile(request: $request) {
                    id
                    name
                    bio
                    picture {
                      ... on NftImage {
                        contractAddress
                        tokenId
                        uri
                        verified
                      }
                      ... on MediaSet {
                        original {
                          url
                          mimeType
                        }
                      }
                      __typename
                    }
                    handle
                  }
                }
            """
            )

            result = await session.execute(query, variable_values={"request": {"ethereumAddress": wallet_address}})
            return result.get("defaultProfile")

    @staticmethod
    async def update_user_lens_data(user: User):
        lens_profile = await LensClient().get_default_profile(wallet_address=user.wallet_address)
        if not lens_profile:
            return

        update_data = {"lens_id": lens_profile.get("id"), "lens_handle": lens_profile.get("handle")}
        await update_item(item=user, data=update_data)
