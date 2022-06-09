import pytest

from app.helpers.permissions import _calc_final_permissions, user_belongs_to_server
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

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "required, user_roles, section_overwrites, channel_overwrites, expected_result",
        [
            (["messages.create"], {"@everyone": ["messages.create"]}, {}, {}, True),
            (["messages.list"], {"@everyone": ["messages.list", "messages.create"]}, {}, {}, True),
            (["messages.create"], {"@everyone": ["messages.list"]}, {}, {}, False),
            (
                ["messages.create"],
                {"@everyone": ["messages.list", "messages.create"]},
                {},
                {"@everyone": ["messages.list"]},
                False,
            ),
            (
                ["messages.create"],
                {"@everyone": ["messages.list"], "mod": ["messages.create", "messages.list", "members.kick"]},
                {},
                {},
                True,
            ),
            (
                ["messages.create"],
                {"@everyone": ["messages.list"], "mod": ["messages.create", "messages.list", "members.kick"]},
                {},
                {"mod": ["messages.list", "members.kick"]},
                False,
            ),
            (
                ["messages.create"],
                {"@everyone": []},
                {"@everyone": ["messages.list"]},
                {},
                False,
            ),
            (
                ["messages.create"],
                {"@everyone": []},
                {"@everyone": ["messages.create"]},
                {},
                True,
            ),
            (
                ["messages.create"],
                {"@everyone": {""}},
                {"@everyone": ["messages.create"]},
                {"@everyone": []},
                False,
            ),
        ],
    )
    async def test_permission_calculations(
        self, required, user_roles, channel_overwrites, section_overwrites, expected_result
    ):
        user_permissions = await _calc_final_permissions(
            user_roles=user_roles, section_overwrites=section_overwrites, channel_overwrites=channel_overwrites
        )
        u_perms = list(user_permissions)
        calc_result = all([r_perm in u_perms for r_perm in required])
        assert calc_result == expected_result
