from fastapi import APIRouter, Depends
from starlette.requests import Request

from app.dependencies import get_current_user
from app.helpers.websockets import pusher_client
from app.models.user import User
from app.services.websockets import create_online_channel

router = APIRouter()


@router.post("/auth", include_in_schema=False)
async def post_websocket_authentication(
    request: Request,
    current_user: User = Depends(get_current_user),
):
    form_data = await request.form()
    channel_name = form_data["channel_name"]
    socket_id = form_data["socket_id"]
    provider = form_data["provider"]

    if not provider or provider != "pusher":
        raise NotImplementedError("can only use Pusher for auth.")

    expected_channel_name = f"private-{str(current_user.id)}"
    if not channel_name.startswith(expected_channel_name):
        raise Exception(f"problem establishing connection: unexpected channel name {channel_name}")

    await create_online_channel(form_data, current_user=current_user)

    auth = pusher_client.authenticate(channel=channel_name, socket_id=socket_id)
    return auth
