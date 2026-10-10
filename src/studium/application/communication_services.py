"""Local capture of correspondence, educational context and shared file assets."""

from dataclasses import asdict, dataclass, replace
from pathlib import Path

from studium.application.errors import ApplicationError
from studium.application.file_ports import FileIntegrity
from studium.domain import communication as c
from studium.domain.entities import FileAsset, Student

CONTEXT = {
    "assessment": ("assessments", c.QuestionCaseAssessment, "assessment_id"),
    "attempt": ("attempts", c.QuestionCaseAttempt, "attempt_id"),
    "topic": ("topics", c.QuestionCaseTopic, "topic_id"),
    "skill": ("skills", c.QuestionCaseSkill, "skill_id"),
}


@dataclass(frozen=True)
class QuestionEntry:
    case: c.QuestionCase
    student: Student
    course_name: str
    group_number: str
    term_name: str
    state: c.CommunicationState
    channel: c.CommunicationChannel
    preview: str


@dataclass(frozen=True)
class MessageFileEntry:
    attachment: c.MessageAttachment
    asset: FileAsset
    student: Student
    case: c.QuestionCase
    message: c.Message
    integrity: FileIntegrity


class CommunicationService:
    def create_question_case(
        self,
        student_id,
        body,
        sent_at,
        *,
        channel=c.CommunicationChannel.MANUAL,
        course_offering_id=None,
        title=None,
        context=None,
    ):
        """The case and initial student message/context commit atomically."""
        if student_id is None:
            raise ApplicationError("question_student_required")
        with self._transaction() as r:
            self._require(r.students, student_id)
            if course_offering_id is not None:
                self._context(r, course_offering_id)
            case = c.QuestionCase(
                metadata=self._meta(),
                student_id=student_id,
                opened_at=sent_at,
                course_offering_id=course_offering_id,
                title=title.strip() or None if title is not None else None,
            )
            r.question_cases.insert(case)
            r.messages.insert(
                c.Message(
                    metadata=self._meta(),
                    question_case_id=case.id,
                    author_role=c.AuthorRole.STUDENT,
                    channel=channel,
                    sent_at=sent_at,
                    body=body,
                )
            )
            for kind, ids in (context or {}).items():
                for id in ids:
                    self._attach_question_context(r, case, kind, id)
            return case

    def get_question_case(self, case_id, *, include_deleted=False):
        return self._require(self._r.question_cases, case_id, historical=include_deleted)

    def list_messages(self, case_id, *, include_deleted=False):
        with self._transaction() as r:
            self._require(r.question_cases, case_id, historical=True)
            return r.messages.for_case(case_id, include_deleted=include_deleted)

    def _add_message(self, case_id, role, body, sent_at, channel, **external):
        with self._transaction() as r:
            case = self._require(r.question_cases, case_id)
            self._require(r.students, case.student_id)
            if case.closed_at is not None:
                raise ApplicationError("question_closed")
            value = c.Message(
                metadata=self._meta(),
                question_case_id=case_id,
                author_role=role,
                body=body,
                sent_at=sent_at,
                channel=channel,
                **external,
            )
            if value.sent_at < case.opened_at:
                raise ApplicationError("question_message_date")
            r.messages.insert(value)
            return value

    def add_student_message(
        self, case_id, body, sent_at, *, channel=c.CommunicationChannel.MANUAL, **external
    ):
        return self._add_message(case_id, c.AuthorRole.STUDENT, body, sent_at, channel, **external)

    def add_teacher_message(
        self, case_id, body, sent_at, *, channel=c.CommunicationChannel.MANUAL, **external
    ):
        return self._add_message(case_id, c.AuthorRole.TEACHER, body, sent_at, channel, **external)

    def record_imported_message(self, case_id, imported):
        """Future adapter boundary: explicit student/case resolution happens first.

        Replaying an identical identity/fact returns the original, even a tombstone.
        A changed payload or a different case is a conflict, never an overwrite.
        """
        values = asdict(imported)
        # asdict recursively converts UtcInstant; retain the boundary value.
        values["sent_at"] = imported.sent_at
        candidate = c.Message(metadata=self._meta(), question_case_id=case_id, **values)
        with self._transaction() as r:
            existing = r.messages.find_external(candidate.external_key)
            if existing:
                if any(
                    getattr(existing, f) != getattr(candidate, f)
                    for f in ("question_case_id", "author_role", "channel", "sent_at", "body")
                ):
                    raise ApplicationError("external_message_conflict")
                return existing
            case = self._require(r.question_cases, case_id)
            self._require(r.students, case.student_id)
            if case.closed_at is not None:
                raise ApplicationError("question_closed")
            if candidate.sent_at < case.opened_at:
                raise ApplicationError("question_message_date")
            r.messages.insert(candidate)
            return candidate

    def close_question_case(self, original, *, closed_at=None):
        with self._transaction() as r:
            self._require(r.question_cases, original.id)
            at = closed_at or self._clock()
            messages = r.messages.for_case(original.id)
            if messages and at < max(m.sent_at for m in messages):
                raise ApplicationError("question_close_date")
            return self._update(r.question_cases, original, closed_at=at)

    def reopen_question_case(self, original):
        with self._transaction() as r:
            self._require(r.question_cases, original.id)
            return self._update(r.question_cases, original, closed_at=None)

    def archive_question_case(self, original):
        self._r.question_cases.soft_delete(
            original.id, expected_revision=original.revision, at=self._clock()
        )

    def archive_message(self, original):
        """Explicit correction by exclusion; the original body and role are retained."""
        with self._transaction() as r:
            self._require(r.question_cases, original.question_case_id)
            r.messages.soft_delete(
                original.id, expected_revision=original.revision, at=self._clock()
            )

    def list_question_cases(
        self,
        *,
        student_id=None,
        course_offering_id=None,
        state=None,
        search="",
        channel=None,
        assessment_id=None,
        attempt_id=None,
        include_deleted=False,
    ):
        needle = search.casefold()
        with self._transaction() as r:
            cases = r.question_cases.list(include_deleted=include_deleted)
            students = {x.id: x for x in r.students.list(include_deleted=True)}
            offerings = {x.id: x for x in r.offerings.list(include_deleted=True)}
            courses = {x.id: x for x in r.courses.list(include_deleted=True)}
            groups = {x.id: x for x in r.groups.list(include_deleted=True)}
            terms = {x.id: x for x in r.terms.list(include_deleted=True)}
            by_case = {}
            assessment_cases = (
                {
                    link.question_case_id
                    for link in r.question_case_assessments.list()
                    if link.assessment_id == assessment_id
                }
                if assessment_id
                else None
            )
            attempt_cases = (
                {
                    link.question_case_id
                    for link in r.question_case_attempts.list()
                    if link.attempt_id == attempt_id
                }
                if attempt_id
                else None
            )
            for message in r.messages.list():
                by_case.setdefault(message.question_case_id, []).append(message)
            result = []
            for case in cases:
                if student_id is not None and case.student_id != student_id:
                    continue
                if course_offering_id is not None and case.course_offering_id != course_offering_id:
                    continue
                if assessment_id is not None:
                    if case.id not in assessment_cases:
                        continue
                if attempt_id is not None:
                    if case.id not in attempt_cases:
                        continue
                messages = sorted(by_case.get(case.id, []), key=c.message_order)
                derived = c.communication_state(case, messages)
                if state is not None and derived != state:
                    continue
                if channel is not None and not any(m.channel == channel for m in messages):
                    continue
                student = students[case.student_id]
                if needle and not any(
                    needle in text.casefold()
                    for text in (student.full_name, case.title or "", *(m.body for m in messages))
                ):
                    continue
                offering = offerings.get(case.course_offering_id)
                result.append(
                    QuestionEntry(
                        case,
                        student,
                        (courses[offering.course_id].short_name or courses[offering.course_id].name)
                        if offering
                        else "—",
                        groups[offering.group_id].number if offering else "—",
                        terms[offering.term_id].name if offering else "—",
                        derived,
                        messages[-1].channel if messages else c.CommunicationChannel.MANUAL,
                        case.title or (messages[0].body if messages else ""),
                    )
                )
            return sorted(result, key=lambda x: (x.case.opened_at, x.case.id), reverse=True)

    def list_student_question_cases(self, student_id, **filters):
        return self.list_question_cases(student_id=student_id, **filters)

    def list_open_questions(self):
        return [q for q in self.list_question_cases() if q.case.closed_at is None]

    def list_questions_waiting_for_teacher(self):
        return self.list_question_cases(state=c.CommunicationState.WAITING)

    def list_questions_by_course_offering(self, offering_id):
        return self.list_question_cases(course_offering_id=offering_id)

    def search_questions(self, text):
        return self.list_question_cases(search=text)

    def _attach_question_context(self, r, case, kind, target_id):
        repository_name, entity_type, target_field = CONTEXT[kind]
        if case.course_offering_id is None:
            raise ApplicationError("question_offering_required")
        offering = self._require(r.offerings, case.course_offering_id)
        target = self._require(getattr(r, repository_name), target_id)
        if kind == "attempt":
            work = self._require(r.works, target.student_work_id)
            assessment = self._require(r.assessments, work.assessment_id)
            valid = work.student_id == case.student_id and assessment.offering_id == offering.id
        elif kind == "assessment":
            valid = target.offering_id == offering.id
        else:
            valid = target.course_id == offering.course_id
        if not valid:
            raise ApplicationError("question_context_mismatch")
        repository = getattr(r, "question_case_" + repository_name)
        previous = repository.find_pair(case.id, target_id)
        if previous:
            if previous.deleted_at is None:
                return previous
            updated = replace(
                previous, metadata=replace(previous.metadata.touch(self._clock()), deleted_at=None)
            )
            repository.update(updated, expected_revision=previous.revision)
            return updated
        value = entity_type(
            metadata=self._meta(), question_case_id=case.id, **{target_field: target_id}
        )
        repository.insert(value)
        return value

    def attach_question_context(self, case_id, kind, target_id):
        with self._transaction() as r:
            return self._attach_question_context(
                r, self._require(r.question_cases, case_id), kind, target_id
            )

    def detach_question_context(self, original, kind):
        with self._transaction() as r:
            self._require(r.question_cases, original.question_case_id)
            repository_name = CONTEXT[kind][0]
            getattr(r, "question_case_" + repository_name).soft_delete(
                original.id, expected_revision=original.revision, at=self._clock()
            )

    def list_question_context(self, case_id):
        with self._transaction() as r:
            self._require(r.question_cases, case_id, historical=True)
            return {
                kind: [
                    (link, self._require(getattr(r, name), getattr(link, field), historical=True))
                    for link in getattr(r, "question_case_" + name).for_owner(case_id)
                ]
                for kind, (name, _, field) in CONTEXT.items()
            }

    def question_context_choices(self, case_id):
        case = self.get_question_case(case_id)
        return self.capture_context_choices(case.student_id, case.course_offering_id)

    def capture_context_choices(self, student_id, course_offering_id):
        with self._transaction() as r:
            student = self._require(r.students, student_id, historical=True)
            if course_offering_id is None or student.deleted_at is not None:
                return {kind: [] for kind in CONTEXT}
            offering = self._require(r.offerings, course_offering_id, historical=True)
            assessments = r.assessments.for_offering(offering.id)
            works = [
                w
                for w in r.works.for_assessments([a.id for a in assessments])
                if w.student_id == student_id
            ]
            return {
                "assessment": assessments,
                "attempt": r.attempts.for_works([w.id for w in works]),
                "topic": r.topics.for_course(offering.course_id),
                "skill": r.skills.for_course(offering.course_id),
            }

    def question_work_for_assessment(self, case_id, assessment_id):
        with self._transaction() as r:
            case = self._require(r.question_cases, case_id, historical=True)
            return r.works.find_for_student(case.student_id, assessment_id, include_deleted=True)

    def question_attempt_titles(self, student_id, course_offering_id):
        """Batch labels disambiguate attempts from different assessments, including history."""
        with self._transaction() as r:
            assessments = {
                a.id: a
                for a in r.assessments.list(include_deleted=True)
                if a.offering_id == course_offering_id
            }
            works = {
                w.id: w
                for w in r.works.list(include_deleted=True)
                if w.student_id == student_id and w.assessment_id in assessments
            }
            return {
                a.id: assessments[works[a.student_work_id].assessment_id].title
                for a in r.attempts.list(include_deleted=True)
                if a.student_work_id in works
            }

    def import_file_for_message(self, message_id, source, *, caption=None):
        storage = self._file_adapters()
        with self._transaction() as r:
            message = self._require(r.messages, message_id)
            case = self._require(r.question_cases, message.question_case_id)
            self._require(r.students, case.student_id)
        meta = self._meta()
        with storage.import_file(Path(source), meta.id) as imported:
            asset = FileAsset(metadata=meta, **asdict(imported))
            with self._transaction() as r:
                message = self._require(r.messages, message_id)
                case = self._require(r.question_cases, message.question_case_id)
                self._require(r.students, case.student_id)
                links = r.message_attachments.for_owner(message_id, include_deleted=True)
                link = c.MessageAttachment(
                    metadata=self._meta(),
                    message_id=message_id,
                    file_asset_id=asset.id,
                    caption=caption,
                    sort_order=max((x.sort_order for x in links), default=-1) + 1,
                )
                r.file_assets.insert(asset)
                r.message_attachments.insert(link)
        return link

    def attach_file_asset_to_message(self, message_id, file_asset_id, *, caption=None):
        with self._transaction() as r:
            message = self._require(r.messages, message_id)
            case = self._require(r.question_cases, message.question_case_id)
            self._require(r.students, case.student_id)
            self._require(r.file_assets, file_asset_id)
            # A detached attachment is historical, not silently resurrected.
            previous = r.message_attachments.find_pair(message_id, file_asset_id)
            if previous is not None:
                if previous.deleted_at is not None:
                    raise ApplicationError("file_link_detached")
                return previous
            links = r.message_attachments.for_owner(message_id, include_deleted=True)
            link = c.MessageAttachment(
                metadata=self._meta(),
                message_id=message_id,
                file_asset_id=file_asset_id,
                caption=caption,
                sort_order=max((x.sort_order for x in links), default=-1) + 1,
            )
            r.message_attachments.insert(link)
            return link

    def list_message_attachments(self, message_id, *, include_detached=False):
        with self._transaction() as r:
            message = self._require(r.messages, message_id, historical=True)
            case = self._require(r.question_cases, message.question_case_id, historical=True)
            student = self._require(r.students, case.student_id, historical=True)
            result = []
            for link in r.message_attachments.for_owner(
                message_id, include_deleted=include_detached
            ):
                asset = self._require(r.file_assets, link.file_asset_id, historical=True)
                result.append(
                    MessageFileEntry(
                        link, asset, student, case, message, self._file_adapters().verify(asset)
                    )
                )
            return sorted(result, key=lambda x: (x.attachment.sort_order, x.attachment.id))

    def detach_message_attachment(self, attachment_id, *, expected_revision):
        self._r.message_attachments.soft_delete(
            attachment_id, expected_revision=expected_revision, at=self._clock()
        )
