"""Attempt ownership and contextual student file queries, without UI/ORM access."""

from dataclasses import asdict, dataclass, replace
from pathlib import Path

from studium.application.errors import ApplicationError
from studium.application.file_ports import FileIntegrity
from studium.domain.entities import Assessment, Attempt, AttemptAttachment, FileAsset, Student
from studium.domain.file_contract import OPEN_EXTENSIONS
from studium.domain.repositories import RepositoryError, RepositoryFailure


@dataclass(frozen=True)
class FileEntry:
    attachment: AttemptAttachment
    asset: FileAsset
    student: Student
    assessment: Assessment
    attempt: Attempt
    integrity: FileIntegrity


class AttachmentService:
    """Composed into StudiumService; physical effects are supplied through ports."""

    def _file_adapters(self):
        if self._file_storage is None:
            raise ApplicationError("file_storage_unavailable")
        return self._file_storage

    def import_file_for_attempt(self, attempt_id, source, *, caption=None, details_json="{}"):
        storage = self._file_adapters()
        # Validate the target before touching any source bytes, then revalidate
        # inside the write transaction after the copy.
        self._require(self._r.attempts, attempt_id)
        meta = self._meta()
        with storage.import_file(Path(source), meta.id) as imported:
            asset = FileAsset(metadata=meta, **asdict(imported))
            with self._transaction() as r:
                attempt = self._require(r.attempts, attempt_id)
                work = self._require(r.works, attempt.student_work_id)
                self._require(r.students, work.student_id)
                self._require(r.assessments, work.assessment_id)
                links = r.attempt_attachments.for_attempt(attempt_id, include_deleted=True)
                link = AttemptAttachment(
                    metadata=self._meta(),
                    attempt_id=attempt_id,
                    file_asset_id=asset.id,
                    caption=caption,
                    details_json=details_json,
                    sort_order=max((link.sort_order for link in links), default=-1) + 1,
                )
                r.file_assets.insert(asset)
                r.attempt_attachments.insert(link)
        return link

    def get_file_asset(self, file_asset_id, *, include_deleted=False):
        return self._require(self._r.file_assets, file_asset_id, historical=include_deleted)

    def verify_file_integrity(self, file_asset_id):
        # Missing/corrupt bytes never mutate metadata or deleted_at.
        return self._file_adapters().verify(
            self.get_file_asset(file_asset_id, include_deleted=True)
        )

    def accessible_file_path(self, file_asset_id):
        asset = self.get_file_asset(file_asset_id, include_deleted=True)
        integrity = self._file_adapters().verify(asset)
        if integrity != FileIntegrity.AVAILABLE:
            raise ApplicationError("file_" + integrity.value)
        return self._file_adapters().path(asset)

    def open_file_asset(self, file_asset_id):
        asset = self.get_file_asset(file_asset_id, include_deleted=True)
        path = self.accessible_file_path(asset.id)
        if path.suffix.lower() not in OPEN_EXTENSIONS:
            raise ApplicationError("file_open_blocked")
        if self._file_opener is None:
            raise ApplicationError("file_open_failed")
        self._file_opener.open(path)

    def image_preview(self, file_asset_id, *, maximum=1400):
        asset = self.get_file_asset(file_asset_id, include_deleted=True)
        if not asset.mime_type.startswith("image/"):
            raise ApplicationError("file_preview_unsupported")
        path = self.accessible_file_path(asset.id)
        if self._thumbnails is None:
            raise ApplicationError("file_preview_unsupported")
        return self._thumbnails.image(asset, path, maximum=maximum)

    def get_thumbnail(self, file_asset_id):
        return self.image_preview(file_asset_id, maximum=240)

    def _file_entries(self, r, links):
        entries = []
        assets, attempts, works, students, assessments = {}, {}, {}, {}, {}

        def get(cache, repository, id):
            if id not in cache:
                cache[id] = self._require(repository, id, historical=True)
            return cache[id]

        for link in links:
            asset = get(assets, r.file_assets, link.file_asset_id)
            attempt = get(attempts, r.attempts, link.attempt_id)
            work = get(works, r.works, attempt.student_work_id)
            student = get(students, r.students, work.student_id)
            assessment = get(assessments, r.assessments, work.assessment_id)
            entries.append(
                FileEntry(
                    link, asset, student, assessment, attempt, self._file_adapters().verify(asset)
                )
            )
        return entries

    def list_attempt_attachments(self, attempt_id, *, include_detached=False):
        with self._transaction() as r:
            self._require(r.attempts, attempt_id, historical=True)
            return self._file_entries(
                r, r.attempt_attachments.for_attempt(attempt_id, include_deleted=include_detached)
            )

    def list_student_files(self, student_id, *, include_detached=False):
        with self._transaction() as r:
            self._require(r.students, student_id, historical=True)
            entries = self._file_entries(
                r, r.attempt_attachments.for_student(student_id, include_deleted=include_detached)
            )
        return sorted(
            entries,
            key=lambda e: (
                -e.attempt.occurred_at.epoch_microseconds,
                -e.attempt.attempt_no,
                e.attachment.sort_order,
                e.attachment.id,
            ),
        )

    def detach_attachment(self, attachment_id, *, expected_revision):
        self._r.attempt_attachments.soft_delete(
            attachment_id, expected_revision=expected_revision, at=self._clock()
        )

    def update_attachment(self, original, *, caption=None, sort_order=0, details_json="{}"):
        if original.deleted_at is not None:
            raise ApplicationError("file_link_detached")
        updated = replace(
            original,
            metadata=original.metadata.touch(self._clock()),
            caption=caption,
            sort_order=sort_order,
            details_json=details_json,
        )
        self._r.attempt_attachments.update(updated, expected_revision=original.revision)
        return updated

    def archive_file_asset(self, file_asset_id, *, expected_revision):
        with self._transaction() as r:
            for name in (
                "homework_attachments",
                "problem_attachments",
                "seminar_attachments",
                "literature_attachments",
                "ticket_problem_files",
                "program_attachments",
                "student_problem_files",
                "homework_pack_attachments",
                "methodical_attachments",
                "assessment_attachments",
            ):
                if any(
                    link.file_asset_id == file_asset_id
                    for link in getattr(r, name).list(
                        include_deleted=name == "ticket_problem_files"
                    )
                ):
                    raise ApplicationError("file_asset_in_use")
            if r.attempt_attachments.for_asset(file_asset_id) or r.message_attachments.for_asset(
                file_asset_id
            ):
                raise ApplicationError("file_asset_in_use")
            asset = self._require(r.file_assets, file_asset_id, historical=True)
            if asset.revision != expected_revision:
                raise RepositoryError(RepositoryFailure.REVISION_CONFLICT, "File metadata changed")
            r.file_assets.soft_delete(
                file_asset_id, expected_revision=expected_revision, at=self._clock()
            )
