"""Bounded ZIP v1 program container; staging is never a live profile."""

import hashlib
import json
import os
import re
import stat
import tempfile
import zipfile
from dataclasses import replace
from pathlib import Path

from studium.application.errors import ApplicationError
from studium.application.program_exchange import (
    ProgramPackage,
    content_allowlist,
    validate_portable,
)
from studium.application.qa_services import document
from studium.domain.file_contract import validate_filename
from studium.domain.value_objects import EntityId
from studium.infrastructure.backup import BackupLimits, _zip_preflight
from studium.infrastructure.user_data import ensure_outside_repository

FORMAT = "studium-program"
VERSION = 1
LIMITS = BackupLimits(
    entries=1026,
    total_bytes=256 * 1024**2,
    database_bytes=8 * 1024**2,
    manifest_bytes=1024**2,
    directory_bytes=1024**2,
    compression_ratio=200,
)
MAX_FILE = 64 * 1024**2
CHUNK = 1024**2


def unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Повтор ключа JSON")
        result[key] = value
    return result


def load(raw):
    return json.loads(
        raw,
        object_pairs_hook=unique,
        parse_constant=lambda _: (_ for _ in ()).throw(ValueError("Некорректное число JSON")),
    )


def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as source:
        while chunk := source.read(CHUNK):
            h.update(chunk)
    return h.hexdigest()


class LocalProgramExchange:
    def __init__(self, profile_root=None):
        self.profile_root = Path(profile_root).resolve() if profile_root else None

    def read(self, path):
        try:
            return self._read(Path(path))
        except (
            ApplicationError,
            OSError,
            KeyError,
            TypeError,
            RecursionError,
            zipfile.BadZipFile,
            UnicodeError,
        ) as error:
            raise ValueError("Повреждённый или небезопасный файл учебной программы") from error

    def _read(self, path):
        if path.is_symlink() or path.is_junction() or not path.is_file():
            raise ValueError("Выберите обычный файл программы")
        before = (
            digest(path)
            if path.stat().st_size <= LIMITS.total_bytes + LIMITS.directory_bytes
            else None
        )
        if before is None:
            raise ValueError("Пакет превышает лимит 256 МиБ")
        with path.open("rb") as stream:
            _zip_preflight(stream, LIMITS)
            with zipfile.ZipFile(stream) as archive:
                seen, total = set(), 0
                for info in archive.infolist():
                    name = info.filename
                    if not (
                        name in {"manifest.json", "program.json"}
                        or re.fullmatch(r"files/[0-9a-f-]{36}", name)
                    ):
                        raise ValueError("Недопустимый путь внутри пакета")
                    mode = info.external_attr >> 16
                    if (
                        name.casefold() in seen
                        or info.orig_filename != name
                        or stat.S_IFMT(mode) not in {0, stat.S_IFREG}
                        or info.external_attr & 0x410
                        or info.flag_bits & 1
                        or info.compress_type not in {zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED}
                    ):
                        raise ValueError("Повтор имени или небезопасная ZIP entry")
                    seen.add(name.casefold())
                    bound = (
                        LIMITS.manifest_bytes
                        if name == "manifest.json"
                        else LIMITS.database_bytes
                        if name == "program.json"
                        else MAX_FILE
                    )
                    total += info.file_size
                    if (
                        info.file_size > bound
                        or total > LIMITS.total_bytes
                        or info.file_size > max(info.compress_size, 1) * LIMITS.compression_ratio
                    ):
                        raise ValueError("Превышены ограничения размера/сжатия пакета")
                manifest = load(archive.read("manifest.json"))
                if set(manifest) != {
                    "format",
                    "version",
                    "origin",
                    "content_hash",
                    "files",
                    "excluded_files",
                }:
                    raise ValueError("Некорректный manifest программы")
                if (
                    manifest["format"] != FORMAT
                    or type(manifest["version"]) is not int
                    or manifest["version"] != VERSION
                ):
                    raise ValueError("Неизвестная версия формата программы")
                if not re.fullmatch(r"urn:uuid:[0-9a-f-]{36}", manifest["origin"]):
                    raise ValueError("Некорректное происхождение редакции")
                EntityId(manifest["origin"][9:])
                raw = archive.read("program.json")
                if hashlib.sha256(raw).hexdigest() != manifest["content_hash"]:
                    raise ValueError("Контрольная сумма программы не совпадает")
                payload = load(raw)
                if set(payload) != {"course", "content", "edition"} or set(payload["course"]) != {
                    "name",
                    "short_name",
                    "description",
                }:
                    raise ValueError("Некорректный паспорт дисциплины")
                if (
                    not all(isinstance(v, str) for v in payload["course"].values())
                    or not payload["course"]["name"].strip()
                ):
                    raise ValueError("Некорректная дисциплина")
                edition = payload["edition"]
                if (
                    set(edition) != {"number", "label"}
                    or type(edition["number"]) is not int
                    or edition["number"] < 1
                    or not isinstance(edition["label"], str)
                ):
                    raise ValueError("Некорректный номер редакции программы")
                if payload["content"] != content_allowlist(payload["content"], include_files=True):
                    raise ValueError("Формат содержит неподдерживаемые поля")
                validate_portable(payload["content"])
                expected = {"manifest.json", "program.json"}
                ids = set()
                for entry in manifest["files"]:
                    if set(entry) != {"id", "name", "size", "sha256"}:
                        raise ValueError("Некорректная запись файла")
                    EntityId(entry["id"])
                    validate_filename(entry["name"])
                    if (
                        entry["id"] in ids
                        or type(entry["size"]) is not int
                        or not 0 <= entry["size"] <= MAX_FILE
                        or not re.fullmatch(r"[0-9a-f]{64}", entry["sha256"])
                    ):
                        raise ValueError("Некорректная идентичность/размер файла")
                    ids.add(entry["id"])
                    name = "files/" + entry["id"]
                    expected.add(name)
                    h, size = hashlib.sha256(), 0
                    with archive.open(name) as source:
                        while chunk := source.read(CHUNK):
                            size += len(chunk)
                            if size > entry["size"]:
                                raise ValueError("Размер файла не совпадает")
                            h.update(chunk)
                    if size != entry["size"] or h.hexdigest() != entry["sha256"]:
                        raise ValueError("Контрольная сумма вложения не совпадает")
                if seen != expected or ids != set(payload["content"]["file_asset_ids"]):
                    raise ValueError("Состав файлов не совпадает со структурой программы")
                if type(manifest["excluded_files"]) is not int or manifest["excluded_files"] < 0:
                    raise ValueError("Некорректное число исключённых файлов")
                package = ProgramPackage(
                    manifest["origin"],
                    manifest["content_hash"],
                    raw.decode(),
                    tuple(manifest["files"]),
                    manifest["excluded_files"],
                    before,
                )
        if digest(path) != before:
            raise ValueError("Файл изменился во время чтения")
        return package

    def stage(self, package, path, folder):
        current = self.read(path)
        if current != package:
            raise ValueError("Файл изменился после preview")
        result = {}
        with zipfile.ZipFile(path) as archive:
            for entry in package.files:
                # Separate ID directories permit identical original filenames.
                target = folder / entry["id"] / entry["name"]
                target.parent.mkdir()
                h, size = hashlib.sha256(), 0
                with archive.open("files/" + entry["id"]) as source, target.open("xb") as dest:
                    while chunk := source.read(CHUNK):
                        size += len(chunk)
                        if size > entry["size"]:
                            raise ValueError("Размер вложения изменился")
                        dest.write(chunk)
                        h.update(chunk)
                if size != entry["size"] or h.hexdigest() != entry["sha256"]:
                    raise ValueError("Вложение изменилось после preview")
                result[entry["id"]] = target
        if digest(path) != package.archive_hash:
            raise ValueError("Пакет изменился при подготовке")
        return result

    def write(self, package, destination, sources):
        destination = destination.absolute()
        ensure_outside_repository(destination)
        if destination.suffix.lower() != ".studium-program":
            raise ValueError("Используйте расширение .studium-program")
        resolved = destination.resolve()
        if self.profile_root and (
            resolved.is_relative_to(self.profile_root / "files")
            or resolved == self.profile_root / "preferences.json"
            or resolved.name.startswith("studium.sqlite")
            and resolved.parent == self.profile_root
        ):
            raise ValueError("Нельзя заменить рабочую БД или файлы профиля экспортом")
        if destination.is_symlink() or destination.is_junction():
            raise ValueError("Нельзя записать пакет через ссылку")
        destination.parent.mkdir(parents=True, exist_ok=True)
        descriptor, name = tempfile.mkstemp(
            prefix=".studium-program-", suffix=".tmp", dir=destination.parent
        )
        temporary = Path(name)
        try:
            manifest = {
                "format": FORMAT,
                "version": VERSION,
                "origin": package.origin,
                "content_hash": package.content_hash,
                "files": list(package.files),
                "excluded_files": package.excluded_files,
            }
            with os.fdopen(descriptor, "w+b") as stream:
                with zipfile.ZipFile(stream, "w", compression=zipfile.ZIP_STORED) as archive:
                    archive.writestr("manifest.json", document(manifest).encode())
                    archive.writestr("program.json", package.payload_json.encode())
                    for entry in package.files:
                        with (
                            sources[entry["id"]].open("rb") as source,
                            archive.open("files/" + entry["id"], "w") as target,
                        ):
                            size = 0
                            while chunk := source.read(CHUNK):
                                size += len(chunk)
                                if size > MAX_FILE:
                                    raise ValueError("Вложение больше 64 МиБ")
                                target.write(chunk)
                stream.flush()
                os.fsync(stream.fileno())
            verified = self.read(temporary)
            if replace(verified, archive_hash="") != package:
                raise ValueError("Ошибка проверки созданного пакета")
            os.replace(temporary, destination)
            return verified
        finally:
            temporary.unlink(missing_ok=True)
