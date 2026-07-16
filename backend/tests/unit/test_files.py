"""Upload validation tests."""
import pytest
from PIL import Image
import io

from app.core.exceptions import ValidationAppError
from app.utils.files import sanitize_filename, validate_image_upload


def _jpeg_bytes(w=200, h=200) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (w, h), color=(120, 40, 40)).save(buf, format="JPEG")
    return buf.getvalue()


def test_sanitize_filename():
    assert ".." not in sanitize_filename("../../etc/passwd")
    assert sanitize_filename("a b.jpg").endswith(".jpg")


def test_validate_good_image():
    data = _jpeg_bytes()
    mime, name, w, h = validate_image_upload("car.jpg", "image/jpeg", data)
    assert mime == "image/jpeg"
    assert w == 200


def test_reject_path_traversal():
    data = _jpeg_bytes()
    with pytest.raises(ValidationAppError):
        validate_image_upload("../evil.jpg", "image/jpeg", data)


def test_reject_tiny_image():
    data = _jpeg_bytes(20, 20)
    with pytest.raises(ValidationAppError):
        validate_image_upload("tiny.jpg", "image/jpeg", data)
