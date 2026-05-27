"""Tests for FileField multipart upload on the create endpoint (#241).

The write path is otherwise JSON-only; file uploads arrive as
``multipart/form-data``. These exercise the CREATE slice — the parent
write — plus the security invariants from the issue's acceptance criteria
(readonly-key rejection, path-traversal sanitisation).
"""

from __future__ import annotations

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client
from django.test.client import BOUNDARY
from django.test.client import MULTIPART_CONTENT
from django.test.client import encode_multipart

from tests.helpers import admin_override
from tests.test_project.uploads.models import Document

CREATE_URL = "/admin-react/api/v1/uploads/document/"
DETAIL_URL = "/admin-react/api/v1/uploads/document/{}/"


@pytest.mark.django_db
def test_multipart_create_saves_file(superuser_client: Client) -> None:
    """A multipart POST with a file creates the object and stores the file
    through the ModelForm → storage (never a parallel write path)."""
    upload = SimpleUploadedFile("report.txt", b"hello", content_type="text/plain")
    response = superuser_client.post(CREATE_URL, data={"title": "Q1", "attachment": upload})
    assert response.status_code == 201
    doc = Document.objects.get(title="Q1")
    assert doc.attachment  # a file was stored
    with doc.attachment.open("rb") as fh:
        assert fh.read() == b"hello"


@pytest.mark.django_db
def test_multipart_create_without_file_still_works(superuser_client: Client) -> None:
    """Multipart with only scalar fields works (attachment is blank=True)."""
    response = superuser_client.post(CREATE_URL, data={"title": "no-file"})
    assert response.status_code == 201
    assert Document.objects.get(title="no-file").attachment.name in ("", None)


@pytest.mark.django_db
def test_file_uploaded_to_readonly_field_rejected(superuser_client: Client) -> None:
    """A file posted to a readonly field → 400, nothing saved. FILES keys go
    through the same forbidden-key gate as scalar keys (#241 security)."""
    upload = SimpleUploadedFile("x.txt", b"data", content_type="text/plain")
    with admin_override(
        Document, get_readonly_fields=lambda self, request, obj=None: ("attachment",)
    ):
        response = superuser_client.post(CREATE_URL, data={"title": "ro", "attachment": upload})
    assert response.status_code == 400
    assert "read-only" in response.json()["error"]["message"]
    assert not Document.objects.filter(title="ro").exists()


@pytest.mark.django_db
def test_unknown_file_key_rejected(superuser_client: Client) -> None:
    """A file posted to a field the model doesn't have → 400 (#241)."""
    upload = SimpleUploadedFile("x.txt", b"data", content_type="text/plain")
    response = superuser_client.post(CREATE_URL, data={"title": "u", "ghost_file": upload})
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "bad_request"


@pytest.mark.django_db
def test_path_traversal_filename_is_neutralised(superuser_client: Client) -> None:
    """A malicious upload filename cannot escape ``upload_to`` — Django's
    storage sanitises it to a basename inside ``docs/`` (#241 security)."""
    upload = SimpleUploadedFile("../../../../etc/passwd", b"x", content_type="text/plain")
    response = superuser_client.post(CREATE_URL, data={"title": "evil", "attachment": upload})
    assert response.status_code == 201
    name = Document.objects.get(title="evil").attachment.name
    assert ".." not in name  # no parent-dir traversal survived
    assert "etc/passwd" not in name
    assert name.startswith("docs/")  # stored under upload_to, nowhere else


# --------------------------------------------------------------------------- #
# UPDATE multipart + ClearableFileInput clear-semantics (#241)                #
# --------------------------------------------------------------------------- #
@pytest.mark.django_db
def test_multipart_update_replaces_file(superuser_client: Client) -> None:
    """A multipart PATCH with a new file replaces the stored file."""
    doc = Document.objects.create(title="d", attachment=SimpleUploadedFile("old.txt", b"old"))
    new = SimpleUploadedFile("new.txt", b"new", content_type="text/plain")
    body = encode_multipart(BOUNDARY, {"title": "d", "attachment": new})
    response = superuser_client.patch(
        DETAIL_URL.format(doc.pk), data=body, content_type=MULTIPART_CONTENT
    )
    assert response.status_code == 200
    doc.refresh_from_db()
    with doc.attachment.open("rb") as fh:
        assert fh.read() == b"new"


@pytest.mark.django_db
def test_multipart_update_without_file_keeps_existing(superuser_client: Client) -> None:
    """An empty file input must NOT wipe the existing file (#241) — the
    critical clear-semantics invariant. Only `title` is submitted; the
    attachment is preserved via ClearableFileInput bound to the instance."""
    doc = Document.objects.create(title="d", attachment=SimpleUploadedFile("keep.txt", b"keep"))
    original_name = doc.attachment.name
    body = encode_multipart(BOUNDARY, {"title": "renamed"})  # no attachment part
    response = superuser_client.patch(
        DETAIL_URL.format(doc.pk), data=body, content_type=MULTIPART_CONTENT
    )
    assert response.status_code == 200
    doc.refresh_from_db()
    assert doc.title == "renamed"
    assert doc.attachment.name == original_name  # file preserved, not wiped
    with doc.attachment.open("rb") as fh:
        assert fh.read() == b"keep"


@pytest.mark.django_db
def test_multipart_update_clear_removes_file(superuser_client: Client) -> None:
    """A `<field>-clear` flag removes the file (Django's ClearableFileInput
    convention), and that key isn't rejected as an unknown field (#241)."""
    doc = Document.objects.create(title="d", attachment=SimpleUploadedFile("bye.txt", b"bye"))
    body = encode_multipart(BOUNDARY, {"title": "d", "attachment-clear": "on"})
    response = superuser_client.patch(
        DETAIL_URL.format(doc.pk), data=body, content_type=MULTIPART_CONTENT
    )
    assert response.status_code == 200
    doc.refresh_from_db()
    assert doc.attachment.name in ("", None)  # file removed
