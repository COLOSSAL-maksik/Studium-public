"""Portable teaching content and immutable variant composition; no Qt/ORM."""

import json
from dataclasses import dataclass
from enum import StrEnum
from itertools import combinations
from math import comb
from random import Random

from studium.domain.entities import StudiumEntity
from studium.domain.enums import AssessmentType, LessonType
from studium.domain.value_objects import AcademicWeekNumber, EntityId, require_text


def tag_document(values=()):
    """One reusable, case-insensitive tag contract for all four libraries."""
    tags = {}
    for value in values:
        value = value.strip()
        require_text(value, "tag")
        tags.setdefault(value.casefold(), value)
    return json.dumps(sorted(tags.values(), key=str.casefold), ensure_ascii=False)


@dataclass(frozen=True, kw_only=True)
class TeachingContent(StudiumEntity):
    title: str
    course_id: EntityId | None
    notes: str = ""
    tags_json: str = "[]"
    details_json: str = "{}"

    def __post_init__(self):
        require_text(self.title, "title")
        tags = json.loads(self.tags_json)
        if not isinstance(tags, list) or not all(isinstance(t, str) for t in tags):
            raise ValueError("Expected a list of text tags")
        object.__setattr__(self, "tags_json", tag_document(tags))
        if not isinstance(json.loads(self.details_json), dict):
            raise ValueError("Expected a metadata object")

    @property
    def tags(self):
        return tuple(json.loads(self.tags_json))


@dataclass(frozen=True, kw_only=True)
class HomeworkDefinition(TeachingContent):
    label: str = ""
    description: str = ""
    type: AssessmentType = AssessmentType.HOMEWORK

    def __post_init__(self):
        super().__post_init__()
        if self.course_id is None:
            raise ValueError("Homework requires a Course")
        if not isinstance(self.type, AssessmentType):
            raise ValueError("Expected assessment type")


# Same canonical record/table; legacy name remains a compatibility API.
WorkDefinition = HomeworkDefinition


class ProblemPurpose(StrEnum):
    SEMINAR = "SEMINAR"
    CONTROL = "CONTROL"
    EXAM = "EXAM"
    CONSULTATION = "CONSULTATION"


def purpose_document(values=()):
    return json.dumps(sorted({ProblemPurpose(value).value for value in values}))


@dataclass(frozen=True, kw_only=True)
class Problem(TeachingContent):
    statement: str = ""
    correct_answer: str = ""
    solution: str = ""
    difficulty: str = ""
    identifier: str = ""
    purposes_json: str = "[]"
    is_family: bool = False
    family_id: EntityId | None = None
    variant_code: str = ""
    parameters: str = ""

    def __post_init__(self):
        super().__post_init__()
        if self.course_id is None:
            raise ValueError("Problem requires a Course")
        purposes = json.loads(self.purposes_json)
        if not isinstance(purposes, list):
            raise ValueError("Expected purpose list")
        object.__setattr__(self, "purposes_json", purpose_document(purposes))
        if type(self.is_family) is not bool or (self.is_family and self.family_id):
            raise ValueError("Invalid problem family")
        if self.family_id:
            require_text(self.variant_code, "variant_code")
            if self.statement or self.tags or self.purposes:
                raise ValueError("Variant inherits its shared statement and classification")
        elif self.variant_code:
            raise ValueError("Variant code requires a family")

    @property
    def purposes(self):
        return tuple(ProblemPurpose(value) for value in json.loads(self.purposes_json))


@dataclass(frozen=True, kw_only=True)
class ProblemCollection(StudiumEntity):
    course_id: EntityId
    title: str
    notes: str = ""

    def __post_init__(self):
        require_text(self.title, "title")


@dataclass(frozen=True, kw_only=True)
class ProblemCollectionMember(StudiumEntity):
    collection_id: EntityId
    problem_id: EntityId


@dataclass(frozen=True, kw_only=True)
class SeminarMaterial(TeachingContent):
    planned_week: AcademicWeekNumber | None = None
    plan_text: str = ""
    full_text: str = ""
    type: LessonType = LessonType.SEMINAR

    def __post_init__(self):
        super().__post_init__()
        if self.course_id is None:
            raise ValueError("Seminar requires a Course")
        if self.planned_week is not None and not isinstance(self.planned_week, AcademicWeekNumber):
            raise ValueError("Expected an academic week")


@dataclass(frozen=True, kw_only=True)
class SeminarMaterialTopic(StudiumEntity):
    seminar_material_id: EntityId
    topic_id: EntityId


class LiteratureType(StrEnum):
    TEXTBOOK = "TEXTBOOK"
    STUDY_GUIDE = "STUDY_GUIDE"
    METHOD_GUIDE = "METHOD_GUIDE"
    ARTICLE = "ARTICLE"
    OTHER = "OTHER"


@dataclass(frozen=True, kw_only=True)
class LiteratureItem(TeachingContent):
    authors: str = ""
    year: int | None = None
    type: LiteratureType = LiteratureType.OTHER

    def __post_init__(self):
        super().__post_init__()
        if self.year is not None and (type(self.year) is not int or not 1 <= self.year <= 9999):
            raise ValueError("Year must be between 1 and 9999")
        if not isinstance(self.type, LiteratureType):
            raise ValueError("Expected a literature type")


class MaterialFileRole(StrEnum):
    STATEMENT = "STATEMENT"
    REFERENCE = "REFERENCE"
    SOLUTION = "SOLUTION"


@dataclass(frozen=True, kw_only=True)
class MaterialAttachment(StudiumEntity):
    file_asset_id: EntityId
    sort_order: int = 0
    caption: str = ""
    role: MaterialFileRole = MaterialFileRole.STATEMENT

    def __post_init__(self):
        if type(self.sort_order) is not int or self.sort_order < 0:
            raise ValueError("Expected a nonnegative file order")
        if not isinstance(self.role, MaterialFileRole):
            raise ValueError("Expected a file role")


@dataclass(frozen=True, kw_only=True)
class HomeworkAttachment(MaterialAttachment):
    homework_definition_id: EntityId


@dataclass(frozen=True, kw_only=True)
class ProblemAttachment(MaterialAttachment):
    problem_id: EntityId


@dataclass(frozen=True, kw_only=True)
class SeminarAttachment(MaterialAttachment):
    seminar_material_id: EntityId


@dataclass(frozen=True, kw_only=True)
class LiteratureAttachment(MaterialAttachment):
    literature_item_id: EntityId


@dataclass(frozen=True, kw_only=True)
class TicketSet(StudiumEntity):
    course_offering_id: EntityId
    title: str
    criteria_json: str
    assessment_id: EntityId | None = None

    def __post_init__(self):
        require_text(self.title, "title")
        if not isinstance(json.loads(self.criteria_json), dict):
            raise ValueError("Expected criteria snapshot object")


@dataclass(frozen=True, kw_only=True)
class Ticket(StudiumEntity):
    ticket_set_id: EntityId
    number: int

    def __post_init__(self):
        if type(self.number) is not int or self.number < 1:
            raise ValueError("Expected a positive variant number")


@dataclass(frozen=True, kw_only=True)
class TicketProblem(StudiumEntity):
    ticket_id: EntityId
    problem_id: EntityId
    position: int
    source_revision: int
    title_snapshot: str
    statement_snapshot: str
    teacher_snapshot_json: str

    @property
    def title(self):
        return self.title_snapshot

    def __post_init__(self):
        if type(self.position) is not int or self.position < 1 or self.source_revision < 1:
            raise ValueError("Invalid problem order/revision")
        require_text(self.title_snapshot, "title")
        if not isinstance(json.loads(self.teacher_snapshot_json), dict):
            raise ValueError("Expected teacher snapshot")


@dataclass(frozen=True, kw_only=True)
class TicketProblemFile(StudiumEntity):
    ticket_problem_id: EntityId
    file_asset_id: EntityId
    role: MaterialFileRole
    sort_order: int


@dataclass(frozen=True, kw_only=True)
class TicketAssignment(StudiumEntity):
    ticket_set_id: EntityId
    ticket_id: EntityId
    enrollment_id: EntityId


@dataclass(frozen=True)
class GenerationCriteria:
    course_id: EntityId
    variants: int
    problems_per_variant: int = 1
    tags: tuple[str, ...] = ()
    collection_id: EntityId | None = None
    seed: int = 0
    purpose: ProblemPurpose | None = None
    problem_ids: tuple[EntityId, ...] = ()

    def __post_init__(self):
        if type(self.variants) is not int or not 1 <= self.variants <= 1000:
            raise ValueError("Variants must be between 1 and 1000")
        if type(self.problems_per_variant) is not int or not 1 <= self.problems_per_variant <= 30:
            raise ValueError("Problems per variant must be between 1 and 30")
        if type(self.seed) is not int:
            raise ValueError("Seed must be an integer")
        if self.purpose is not None and not isinstance(self.purpose, ProblemPurpose):
            raise ValueError("Expected problem purpose")


def generate_variants(pool, criteria):
    """Unique unordered combinations, bounded work even for a huge pool."""
    pool = tuple(sorted({p.id: p for p in pool}.values(), key=lambda p: p.id))
    count, size = criteria.variants, criteria.problems_per_variant
    if len(pool) < size or comb(len(pool), size) < count:
        raise ValueError("insufficient_problem_pool")
    random = Random(criteria.seed)
    if comb(len(pool), size) <= 10000:
        options = list(combinations(range(len(pool)), size))
        random.shuffle(options)
        choices = options[:count]
    else:
        choices, seen = [], set()
        while len(choices) < count:
            choice = tuple(sorted(random.sample(range(len(pool)), size)))
            if choice not in seen:
                seen.add(choice)
                choices.append(choice)
    return tuple(tuple(pool[i] for i in choice) for choice in choices)


@dataclass(frozen=True)
class FAQDraftContract:
    """Future manual conversion copies reviewed text, never derives it with AI."""

    question: str
    answer: str
    source_question_case_id: EntityId | None = None
    course_id: EntityId | None = None
    topic_ids: tuple[EntityId, ...] = ()
    active: bool = False

    def __post_init__(self):
        require_text(self.question, "question")
        require_text(self.answer, "answer")
