from app.models.user import User
from app.schemas.ws_events import CreateMarkChannelReadEvent
from app.services.channels import update_channels_read_state


async def process_channel_mark_event(event_model: CreateMarkChannelReadEvent, current_user: User):
    await update_channels_read_state(
        channel_ids=event_model.channel_ids, last_read_at=event_model.last_read_at, current_user=current_user
    )
