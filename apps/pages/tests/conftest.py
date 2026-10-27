"""Shared fixtures for the pages tests."""
import io

import pytest
from PIL import Image


@pytest.fixture(autouse=True)
def media_root(settings, tmp_path):
    """Uploaded photos go to a throwaway folder, never into the real media/."""
    settings.MEDIA_ROOT = tmp_path
    return tmp_path


def make_image_bytes(fmt="PNG", color="green", size=(10, 10)) -> bytes:
    buf = io.BytesIO()
    Image.new(mode="RGB", size=size, color=color).save(buf, format=fmt)
    return buf.getvalue()
