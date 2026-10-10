"""Regeneratable Qt image cache and default application adapter."""

import os
from uuid import uuid4

from PySide6.QtCore import QSize, Qt, QUrl
from PySide6.QtGui import QDesktopServices, QImageReader

from studium.application.errors import ApplicationError
from studium.infrastructure.file_storage import file_error

IMAGE_FORMATS = {b"jpg", b"jpeg", b"png", b"webp", b"gif", b"bmp", b"tif", b"tiff"}


class QtFileOpener:
    def open(self, path):
        if not QDesktopServices.openUrl(QUrl.fromLocalFile(str(path))):
            raise ApplicationError("file_open_failed")


class QtThumbnailCache:
    def __init__(self, storage):
        self.storage = storage

    def image(self, asset, source, *, maximum):
        if type(maximum) is not int or not 32 <= maximum <= 2000:
            raise ValueError("Invalid preview dimensions")
        try:
            relative = (self.storage.paths.cache_dir / "thumbnails").relative_to(self.storage.root)
            directory = self.storage.controlled_path(relative.as_posix())
            directory.mkdir(parents=True, exist_ok=True)
            key = f"{relative.as_posix()}/{asset.id.value}-{asset.sha256}-{maximum}-v1.png"
            cached = self.storage.controlled_path(key)
            if cached.exists():
                reader = QImageReader(str(cached), b"png")
                size = reader.size()
                if size.isValid() and max(size.width(), size.height()) <= maximum:
                    image = reader.read()
                    if not image.isNull():
                        return cached
            reader = QImageReader(str(source))
            reader.setAutoTransform(True)
            if bytes(reader.format()).lower() not in IMAGE_FORMATS:
                raise ApplicationError("file_preview_unsupported")
            size = reader.size()
            if not size.isValid() or size.width() * size.height() > 50_000_000:
                raise ApplicationError("file_preview_too_large")
            reader.setScaledSize(
                size.scaled(QSize(maximum, maximum), Qt.AspectRatioMode.KeepAspectRatio)
            )
            image = reader.read()
            if image.isNull():
                raise ApplicationError("file_preview_invalid")
            image = image.scaled(
                maximum,
                maximum,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            temporary = self.storage.controlled_path(f"cache/thumbnails/{uuid4()}.tmp")
            try:
                if not image.save(str(temporary), "PNG"):
                    raise ApplicationError("file_preview_cache_failed")
                os.replace(temporary, cached)
            finally:
                temporary.unlink(missing_ok=True)
            return cached
        except OSError as error:
            raise file_error(error) from None
