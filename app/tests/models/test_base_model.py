from app.models.user import UserModel


class TestBaseModel:
    def test_create_user_created_at_default(self, db):
        user = UserModel(email="test@newshades.xyz")
        assert user.created_at is not None
