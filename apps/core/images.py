"""Upload handling for photos: check, shrink, convert to WebP.

Many visitors are in villages with weak mobile coverage, so what matters here
is not only that photos look fine but that they are small. Every photo this
site serves goes through this module first:

- The file is judged by what it really contains, not by its name or the
  content type the browser claimed.
- Only JPEG, PNG and WebP are accepted. Size and pixel count are limited
  before anything is decoded, so an oversized or "decompression bomb" file
  is refused cheaply.
- The EXIF orientation is applied to the pixels, then all metadata is
  dropped (it is simply not written to the output).
- Each stored image has a size budget in bytes, not just a pixel limit.
  Quality starts at `quality` and is lowered step by step; if the floor
  quality is still too big (a busy, textured picture such as a field or a
  leaf), the picture itself is made a bit smaller, a few times. The budget
  is a target: a picture that cannot reach it is stored as small as the
  steps allow, not refused.
- The result is WebP under a random name, so original file names (often
  Persian or "IMG_2231") never reach a URL.

The original upload is not kept (D31).
"""
import io
import os
import uuid

from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from PIL import Image, ImageOps

MAX_UPLOAD_BYTES = 10 * 1024 * 1024
# Checked from the image header, before decoding. A 12-megapixel phone photo
# is 12_000_000; this leaves room for much larger cameras.
MAX_PIXELS = 40_000_000
ALLOWED_FORMATS = {"JPEG", "PNG", "WEBP"}

# The numbers behind D31. Sizes in pixels (longest side) and bytes.
DEFAULT_MAX_SIDE = 800
DEFAULT_MAX_BYTES = 50_000
DEFAULT_THUMB_SIDE = 320
DEFAULT_THUMB_MAX_BYTES = 12_000
DEFAULT_QUALITY = 80

MIN_QUALITY = 40  # below this WebP gets visibly blocky
QUALITY_STEP = 10
SHRINK_FACTOR = 0.85  # each extra shrink makes the picture 15% smaller
MIN_SIDE = 200  # never shrink a picture below this to meet a byte budget


class ImageRejected(ValueError):
    """The upload is not an acceptable image. The message is meant to be shown."""


def _open(file) -> Image.Image:
    file = getattr(file, "file", file)
    file.seek(0)
    size = getattr(file, "size", None)
    if size is None:
        file.seek(0, io.SEEK_END)
        size = file.tell()
        file.seek(0)
    if size == 0:
        raise ImageRejected("فایل خالی است.")
    if size > MAX_UPLOAD_BYTES:
        raise ImageRejected(
            f"حجم تصویر بیشتر از {MAX_UPLOAD_BYTES // (1024 * 1024)} مگابایت است."
        )
    try:
        image = Image.open(file)
    except Exception:  # unreadable, unknown format, or a decompression bomb
        raise ImageRejected("این فایل تصویر معتبری نیست.") from None
    if image.format not in ALLOWED_FORMATS:
        raise ImageRejected("فقط تصویر jpg، png یا webp پذیرفته می‌شود.")
    if image.width * image.height > MAX_PIXELS:
        raise ImageRejected("ابعاد تصویر بیش از حد بزرگ است.")
    return image


def load_image(file) -> Image.Image:
    """Check an upload and return it fully decoded, upright, as RGB or RGBA.

    Raises ImageRejected if it is not an acceptable image.
    """
    image = _open(file)
    try:
        image.load()  # a truncated or corrupt file fails here
        image = ImageOps.exif_transpose(image)
    except Exception:
        raise ImageRejected("این فایل تصویر معتبری نیست.") from None
    has_alpha = image.mode in ("RGBA", "LA") or "transparency" in image.info
    return image.convert("RGBA" if has_alpha else "RGB")


def _webp_bytes(image: Image.Image, quality: int) -> bytes:
    buffer = io.BytesIO()
    # No exif= argument: metadata is not written.
    image.save(buffer, format="WEBP", quality=quality, method=6)
    return buffer.getvalue()


def encode_webp(
    image: Image.Image,
    max_side: int = DEFAULT_MAX_SIDE,
    quality: int = DEFAULT_QUALITY,
    max_bytes: int = DEFAULT_MAX_BYTES,
) -> bytes:
    """Shrink `image` to `max_side` (never enlarging) and encode it as WebP.

    Aims for at most `max_bytes`: first by lowering the quality, then, if the
    floor quality is not enough, by making the picture smaller. Returns the
    smallest attempt if the budget cannot be met.
    """
    work = image.copy()
    work.thumbnail((max_side, max_side), Image.Resampling.LANCZOS)  # shrinks only
    while True:
        q = quality
        while True:
            data = _webp_bytes(work, q)
            if len(data) <= max_bytes:
                return data
            if q <= MIN_QUALITY:
                break
            q = max(MIN_QUALITY, q - QUALITY_STEP)
        width, height = work.size
        smaller = (round(width * SHRINK_FACTOR), round(height * SHRINK_FACTOR))
        if min(smaller) < MIN_SIDE:
            return data
        work = work.resize(smaller, Image.Resampling.LANCZOS)


def new_name() -> str:
    return f"{uuid.uuid4().hex}.webp"


def thumb_name(name: str) -> str:
    """products/ab12.webp -> products/ab12_thumb.webp"""
    root, ext = os.path.splitext(name)
    return f"{root}_thumb{ext}"


def process_image(
    file,
    max_side: int = DEFAULT_MAX_SIDE,
    quality: int = DEFAULT_QUALITY,
    max_bytes: int = DEFAULT_MAX_BYTES,
) -> ContentFile:
    """One WebP ContentFile made from an uploaded image, or ImageRejected."""
    data = encode_webp(load_image(file), max_side, quality, max_bytes)
    return ContentFile(data, name=new_name())


def validate_image_upload(file) -> None:
    """Model/form validator: refuse a new upload that load_image() would refuse.

    A file that is already stored was checked when it was uploaded, so it is not
    opened again on every full_clean().
    """
    if getattr(file, "_committed", False):
        return
    try:
        load_image(file)
    except ImageRejected as exc:
        # Not "invalid_image": that is Django's own code for its image form field, and a
        # model error carrying it gets its message replaced by Django's generic one.
        raise ValidationError(str(exc), code="image_rejected") from None
    finally:
        getattr(file, "file", file).seek(0)
