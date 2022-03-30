import pytest

from app.helpers.permissions import user_belongs_to_server
from app.models.server import Server
from app.models.user import User
from app.services.servers import join_server


class TestPermissionsHelper:
    @pytest.mark.asyncio
    async def test_user_belongs_to_server_ok(self, db, current_user: User, server: Server):
        assert await user_belongs_to_server(user=current_user, server_id=str(server.pk)) is True

    @pytest.mark.asyncio
    async def test_user_belongs_to_server_nok(self, db, current_user: User, server: Server, guest_user: User):
        assert await user_belongs_to_server(user=guest_user, server_id=str(server.pk)) is False

    @pytest.mark.asyncio
    async def test_user_belongs_to_server_after_joining(self, db, current_user: User, server: Server, guest_user: User):
        assert await user_belongs_to_server(user=guest_user, server_id=str(server.pk)) is False
        await join_server(str(server.pk), current_user=guest_user, ignore_joining_rules=True)
        assert await user_belongs_to_server(user=guest_user, server_id=str(server.pk)) is True
