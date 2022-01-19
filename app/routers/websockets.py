from typing import Optional

from fastapi import APIRouter, Depends, Form

from app.dependencies import get_current_user
from app.helpers.websockets import pusher_client
from app.models.user import User

router = APIRouter()


@router.post("/auth", include_in_schema=False)
async def post_websocket_authentication(
    provider: Optional[str] = Form(...),
    channel_name: str = Form(...),
    socket_id: str = Form(...),
    current_user: User = Depends(get_current_user),
):
    if not provider or provider != "pusher":
        raise NotImplementedError("can only use Pusher for auth.")

    expected_channel_name = f"private-{str(current_user.id)}"
    if channel_name != expected_channel_name:
        raise Exception(f"problem establishing connection: unexpected channel name {channel_name}")
    auth = pusher_client.authenticate(channel=channel_name, socket_id=socket_id)
    return auth
