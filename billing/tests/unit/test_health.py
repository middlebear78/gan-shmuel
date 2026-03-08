from unittest.mock import patch, MagicMock


class TestHealth:
    def test_health_ok(self, client):
        with patch("app.db.session") as mock_session:
            mock_session.execute = MagicMock
            res = client.get("/health")
            assert res.status_code == 200
