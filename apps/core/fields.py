"""Model fields shared by several apps."""
from django.core.files.base import ContentFile
from django.db import models
from django.db.models.fields.files import ImageFieldFile

from .images import (
    DEFAULT_MAX_BYTES,
    DEFAULT_MAX_SIDE,
    DEFAULT_QUALITY,
    DEFAULT_THUMB_MAX_BYTES,
    DEFAULT_THUMB_SIDE,
    encode_webp,
    load_image,
    new_name,
    thumb_name,
    validate_image_upload,
)


class WebPFieldFile(ImageFieldFile):
    """The file object of a WebPImageField, with the thumbnail's name and URL."""

    @property
    def thumb_name(self) -> str:
        self._require_file()
        return thumb_name(self.name)

    @property
    def thumb_url(self) -> str:
        """URL of the small version for lists; the main URL if the field has none."""
        self._require_file()
        if not self.field.thumb_side:
            return self.url
        return self.storage.url(self.thumb_name)


class WebPImageField(models.ImageField):
    """An ImageField that stores every new upload as small WebP files (D31).

    Two files are written, side by side: the main image (`<name>.webp`) and a
    thumbnail (`<name>_thumb.webp`) for list pages. Set thumb_side=None for a
    field that needs no thumbnail. Each is held to a byte budget, see images.py.

    The conversion happens when the model is saved, so it applies the same way
    whether the file comes from the admin, a form, a script or a test. A bad
    file is normally stopped earlier, by the validator, with a message shown
    next to the field; if one slips past (a script that skips validation),
    ImageRejected is raised from save() and nothing is stored.
    """

    attr_class = WebPFieldFile

    def __init__(
        self,
        *args,
        max_side: int = DEFAULT_MAX_SIDE,
        quality: int = DEFAULT_QUALITY,
        max_bytes: int = DEFAULT_MAX_BYTES,
        thumb_side: int | None = DEFAULT_THUMB_SIDE,
        thumb_max_bytes: int = DEFAULT_THUMB_MAX_BYTES,
        **kwargs,
    ):
        self.max_side = max_side
        self.quality = quality
        self.max_bytes = max_bytes
        self.thumb_side = thumb_side
        self.thumb_max_bytes = thumb_max_bytes
        kwargs["validators"] = [*kwargs.get("validators", []), validate_image_upload]
        super().__init__(*args, **kwargs)

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        kwargs.update(
            max_side=self.max_side,
            quality=self.quality,
            max_bytes=self.max_bytes,
            thumb_side=self.thumb_side,
            thumb_max_bytes=self.thumb_max_bytes,
        )
        # The validator is added by __init__ itself; do not freeze it into migrations.
        kwargs["validators"] = [v for v in kwargs.get("validators", []) if v is not validate_image_upload]
        if not kwargs["validators"]:
            del kwargs["validators"]
        return name, path, args, kwargs

    def pre_save(self, model_instance, add):
        file = getattr(model_instance, self.attname)
        if file and not file._committed:
            image = load_image(file)
            main = ContentFile(
                encode_webp(image, self.max_side, self.quality, self.max_bytes), name=new_name()
            )
            thumb = None
            if self.thumb_side:
                thumb = ContentFile(
                    encode_webp(image, self.thumb_side, self.quality, self.thumb_max_bytes)
                )
            file.save(main.name, main, save=False)
            if thumb is not None:
                try:
                    # The main name is random, so "<name>_thumb.webp" is free.
                    self.storage.save(thumb_name(file.name), thumb)
                except Exception:
                    self.storage.delete(file.name)  # do not leave half a pair behind
                    raise
        return super().pre_save(model_instance, add)
