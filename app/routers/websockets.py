from typing import Optional

from fastapi import APIRouter, Depends, Form

from app.dependencies import get_current_app, get_current_user
from app.helpers.pusher import pusher_client
from app.models.app import App
from app.models.user import User

router = APIRouter()


@router.post("/auth", include_in_schema=False)
async def post_websocket_authentication(
    provider: Optional[str] = Form(...),
    channel_name: str = Form(...),
    socket_id: str = Form(...),
    current_user: User = Depends(get_current_user),
    current_app: App = Depends(get_current_app),
):
    if not provider or provider != "pusher":
        raise NotImplementedError("can only use Pusher for auth.")

    if current_user:
        pusher_channel_id = str(current_user.pk)
    elif current_app:
        pusher_channel_id = str(current_app.pk)
    else:
        raise Exception("no current user or app")

    expected_start_channel_name = f"private-{pusher_channel_id}"
    if not channel_name.startswith(expected_start_channel_name):
        raise Exception(f"problem establishing connection: unexpected channel name {channel_name}")

    auth = pusher_client.authenticate(channel=channel_name, socket_id=socket_id)
    return auth
