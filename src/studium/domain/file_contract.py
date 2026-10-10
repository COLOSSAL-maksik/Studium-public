"""Portable keys and conservative local file policy; no filesystem access."""

import re

FILE_EXTENSIONS = frozenset(
    ".jpg .jpeg .png .webp .gif .bmp .tif .tiff .pdf .txt .md .csv .tsv .rtf "
    ".doc .docx .xlsx .pptx .odt .ods .odp .zip .7z .bin".split()
)
# .bin may be stored for metadata but never passed to an executable association.
OPEN_EXTENSIONS = FILE_EXTENSIONS - {".bin"}
KEY_PATTERN = re.compile(
    r"files/[0-9a-f]{2}/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\.[a-z0-9]{1,8}"
)


def validate_storage_key(key: str) -> None:
    if not KEY_PATTERN.fullmatch(key) or "." + key.rsplit(".", 1)[-1] not in FILE_EXTENSIONS:
        raise ValueError("Invalid file storage key")


def validate_filename(name: str) -> None:
    if not name.strip() or any(ord(c) < 32 or c in "/\\:" for c in name):
        raise ValueError("Invalid original filename")
