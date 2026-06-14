"""
Unit tests for the cloud-storage API.

These tests mock out MinIO (boto3 client) and PostgreSQL so they run
with zero external dependencies — perfect for CI.

Install test deps:
    pip install pytest pytest-asyncio httpx

Run:
    pytest tests/ -v
"""

import io
import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

# ---------------------------------------------------------------------------
# We need to patch external dependencies BEFORE importing main, because
# storage.py calls boto3.client() at import time and database.py connects
# to Postgres at import time.
# ---------------------------------------------------------------------------

# Patch boto3 so storage.py doesn't try to reach DigitalOcean Spaces
with patch("boto3.client") as _mock_boto:
    _mock_boto.return_value = MagicMock()

    # Patch SQLAlchemy engine creation so no real DB is needed
    with patch("sqlalchemy.create_engine") as _mock_engine:
        _mock_engine.return_value = MagicMock()

        import sys, os
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))
        from main import app


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_client(db_mock, storage_mock):
    """Return a TestClient with DB and storage dependencies overridden."""
    from main import get_db

    app.dependency_overrides[get_db] = lambda: db_mock
    with patch("main.client", storage_mock):
        yield TestClient(app)
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def db():
    mock = MagicMock()
    mock.query.return_value.all.return_value = []
    mock.query.return_value.filter.return_value.first.return_value = None
    return mock


@pytest.fixture
def s3():
    return MagicMock()


@pytest.fixture
def client_app(db, s3):
    from main import get_db
    app.dependency_overrides[get_db] = lambda: db
    with patch("main.client", s3):
        with TestClient(app) as c:
            yield c
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# /upload
# ---------------------------------------------------------------------------

class TestUpload:

    def test_upload_returns_file_id(self, client_app, db, s3):
        """A valid upload should return a JSON body with an 'id' key."""
        response = client_app.post(
            "/upload",
            files={"file": ("hello.txt", b"hello world", "text/plain")},
        )
        assert response.status_code == 200
        body = response.json()
        assert "id" in body
        # id should be a non-empty string (UUID)
        assert len(body["id"]) > 0

    def test_upload_saves_to_minio(self, client_app, db, s3):
        """After a successful upload, put_object must have been called once."""
        client_app.post(
            "/upload",
            files={"file": ("photo.png", b"\x89PNG\r\n", "image/png")},
        )
        s3.put_object.assert_called_once()

    def test_upload_saves_record_to_db(self, client_app, db, s3):
        """After a successful upload, a File record must be committed to DB."""
        client_app.post(
            "/upload",
            files={"file": ("doc.pdf", b"%PDF", "application/pdf")},
        )
        db.add.assert_called_once()
        db.commit.assert_called_once()


# ---------------------------------------------------------------------------
# /files
# ---------------------------------------------------------------------------

class TestListFiles:

    def test_list_files_empty(self, client_app, db, s3):
        """With no files in DB, /files should return an empty list."""
        db.query.return_value.all.return_value = []
        response = client_app.get("/files")
        assert response.status_code == 200
        assert response.json() == []

    def test_list_files_returns_records(self, client_app, db, s3):
        """Files present in DB should appear in the response."""
        from models import File
        fake_file = File(
            id="abc-123",
            filename="notes.txt",
            storage_key="abc-123-notes.txt",
            size=42,
        )
        db.query.return_value.all.return_value = [fake_file]

        response = client_app.get("/files")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["filename"] == "notes.txt"


# ---------------------------------------------------------------------------
# /download/{file_id}
# ---------------------------------------------------------------------------

class TestDownload:

    def _make_file(self):
        from models import File
        return File(
            id="file-1",
            filename="report.pdf",
            storage_key="file-1-report.pdf",
            size=100,
        )

    def test_download_streams_content(self, client_app, db, s3):
        """A download for a known file should return 200 with file bytes."""
        db.query.return_value.filter.return_value.first.return_value = self._make_file()

        # Simulate the streaming body MinIO returns
        s3.get_object.return_value = {"Body": io.BytesIO(b"PDF content here")}
        s3.head_object.return_value = {"ContentType": "application/pdf"}

        response = client_app.get("/download/file-1")
        assert response.status_code == 200
        assert response.content == b"PDF content here"

    def test_download_sets_content_disposition(self, client_app, db, s3):
        """Response headers must include Content-Disposition with the filename."""
        db.query.return_value.filter.return_value.first.return_value = self._make_file()
        s3.get_object.return_value = {"Body": io.BytesIO(b"data")}
        s3.head_object.return_value = {"ContentType": "application/pdf"}

        response = client_app.get("/download/file-1")
        assert "report.pdf" in response.headers.get("content-disposition", "")


# ---------------------------------------------------------------------------
# /files/{file_id}  DELETE
# ---------------------------------------------------------------------------

class TestDelete:

    def _make_file(self):
        from models import File
        return File(
            id="del-1",
            filename="old.txt",
            storage_key="del-1-old.txt",
            size=10,
        )

    def test_delete_existing_file(self, client_app, db, s3):
        """Deleting a known file should return {'status': 'deleted'}."""
        db.query.return_value.filter.return_value.first.return_value = self._make_file()
        response = client_app.delete("/files/del-1")
        assert response.status_code == 200
        assert response.json() == {"status": "deleted"}

    def test_delete_removes_from_minio(self, client_app, db, s3):
        """delete_object must be called on MinIO when a file is deleted."""
        db.query.return_value.filter.return_value.first.return_value = self._make_file()
        client_app.delete("/files/del-1")
        s3.delete_object.assert_called_once()

    def test_delete_commits_db(self, client_app, db, s3):
        """The file record must be removed and the session committed."""
        f = self._make_file()
        db.query.return_value.filter.return_value.first.return_value = f
        client_app.delete("/files/del-1")
        db.delete.assert_called_once_with(f)
        db.commit.assert_called_once()

    def test_delete_missing_file_returns_error(self, client_app, db, s3):
        """Deleting a non-existent file should return an error message."""
        db.query.return_value.filter.return_value.first.return_value = None
        response = client_app.delete("/files/does-not-exist")
        assert response.status_code == 200
        assert response.json() == {"error": "file not found"}


# ---------------------------------------------------------------------------
# /metrics
# ---------------------------------------------------------------------------

class TestMetrics:

    def test_metrics_endpoint_reachable(self, client_app, db, s3):
        """Prometheus /metrics endpoint must return 200 with text/plain."""
        response = client_app.get("/metrics")
        assert response.status_code == 200
        assert "text/plain" in response.headers["content-type"]

    def test_metrics_contains_upload_counter(self, client_app, db, s3):
        """After an upload, file_uploads_total must appear in /metrics."""
        client_app.post(
            "/upload",
            files={"file": ("x.txt", b"x", "text/plain")},
        )
        metrics_response = client_app.get("/metrics")
        assert b"file_uploads_total" in metrics_response.content