"""Tests for FileField/ImageField surfacing (Issue #57, read half).

Multipart upload + clearing is tracked as a follow-up. This PR
closes the read half: the SPA can see the current file (name, url,
size) so view-only flows render correctly.
"""

from __future__ import annotations

from django.db import models

from django_admin_react.api.serializers import field_type_for
from django_admin_react.api.views.detail import _serialize_file_value


def test_field_type_for_file_is_file() -> None:
    assert field_type_for(models.FileField(upload_to="x")) == "file"


def test_field_type_for_image_is_image() -> None:
    assert field_type_for(models.ImageField(upload_to="x")) == "image"


# --------------------------------------------------------------------------- #
# _serialize_file_value                                                       #
# --------------------------------------------------------------------------- #
def test_serialize_file_value_none_when_empty() -> None:
    assert _serialize_file_value(None) is None
    assert _serialize_file_value("") is None


class _FakeFieldFile:
    """Stand-in for Django's FieldFile so the test doesn't need storage."""

    def __init__(self, name, url, size=None, raise_size=False):
        self.name = name
        self.url = url
        self._size = size
        self._raise_size = raise_size

    def __bool__(self) -> bool:
        return bool(self.name)

    @property
    def size(self):
        if self._raise_size:
            raise OSError("boom")
        return self._size


def test_serialize_file_value_shape() -> None:
    f = _FakeFieldFile("docs/report.pdf", "/media/docs/report.pdf", size=1234)
    assert _serialize_file_value(f) == {
        "name": "docs/report.pdf",
        "url": "/media/docs/report.pdf",
        "size": 1234,
    }


def test_serialize_file_value_size_unavailable_is_none() -> None:
    """Backends that don't expose size cheaply → size: None (no 500)."""
    f = _FakeFieldFile("docs/x.pdf", "/media/x", raise_size=True)
    out = _serialize_file_value(f)
    assert out is not None
    assert out["size"] is None
    assert out["name"] == "docs/x.pdf"


def test_serialize_file_value_url_failure_returns_none_url() -> None:
    """If .url raises, surface url: null but keep name."""

    class _NoUrl:
        name = "x"

        @property
        def url(self):
            raise ValueError("no storage")

    out = _serialize_file_value(_NoUrl())
    assert out == {"name": "x", "url": None, "size": None}
