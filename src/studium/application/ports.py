"""Small transaction boundary shared by application use cases."""

from collections.abc import Callable
from contextlib import AbstractContextManager
from dataclasses import dataclass
from typing import Protocol

from studium.domain import content as c
from studium.domain import program as p
from studium.domain import qa as q
from studium.domain.communication import (
    QuestionCaseAssessment,
    QuestionCaseAttempt,
    QuestionCaseSkill,
    QuestionCaseTopic,
)
from studium.domain.entities import (
    AssessmentItemSkill,
    AssessmentItemTopic,
    AssessmentSkill,
    AssessmentTopic,
    LessonTopic,
    TopicSkill,
)
from studium.domain.repositories import (
    AcademicTermRepository,
    AssessmentRepository,
    AttemptRepository,
    CourseOfferingRepository,
    CourseRepository,
    EnrollmentRepository,
    GradeRepository,
    StudentGroupRepository,
    StudentRepository,
    StudentWorkRepository,
)
from studium.domain.repositories.analytics_facts import (
    AttemptItemResultRepository,
    SemanticLockRepository,
)
from studium.domain.repositories.communication import (
    MessageAttachmentRepository,
    MessageRepository,
    QuestionCaseRepository,
)
from studium.domain.repositories.content import ContentLinkRepository, ContentRepository
from studium.domain.repositories.files import AttemptAttachmentRepository, FileAssetRepository
from studium.domain.repositories.learning import (
    AssessmentItemRepository,
    AttendanceRepository,
    LearningLinkRepository,
    LessonRepository,
    SkillRepository,
    TopicRepository,
)
from studium.domain.value_objects import EntityId


@dataclass(frozen=True)
class Repositories:
    terms: AcademicTermRepository
    courses: CourseRepository
    groups: StudentGroupRepository
    offerings: CourseOfferingRepository
    students: StudentRepository
    enrollments: EnrollmentRepository
    assessments: AssessmentRepository
    works: StudentWorkRepository
    attempts: AttemptRepository
    grades: GradeRepository
    topics: TopicRepository
    skills: SkillRepository
    lessons: LessonRepository
    attendance: AttendanceRepository
    items: AssessmentItemRepository
    topic_skills: LearningLinkRepository[TopicSkill]
    lesson_topics: LearningLinkRepository[LessonTopic]
    assessment_topics: LearningLinkRepository[AssessmentTopic]
    assessment_skills: LearningLinkRepository[AssessmentSkill]
    item_topics: LearningLinkRepository[AssessmentItemTopic]
    item_skills: LearningLinkRepository[AssessmentItemSkill]
    file_assets: FileAssetRepository
    attempt_attachments: AttemptAttachmentRepository
    question_cases: QuestionCaseRepository
    messages: MessageRepository
    message_attachments: MessageAttachmentRepository
    question_case_assessments: LearningLinkRepository[QuestionCaseAssessment]
    question_case_attempts: LearningLinkRepository[QuestionCaseAttempt]
    question_case_topics: LearningLinkRepository[QuestionCaseTopic]
    question_case_skills: LearningLinkRepository[QuestionCaseSkill]
    item_results: AttemptItemResultRepository
    content_locks: SemanticLockRepository
    homework_definitions: ContentRepository[c.HomeworkDefinition]
    problems: ContentRepository[c.Problem]
    problem_collections: ContentRepository[c.ProblemCollection]
    problem_collection_members: ContentLinkRepository[c.ProblemCollectionMember]
    seminar_materials: ContentRepository[c.SeminarMaterial]
    seminar_material_topics: ContentLinkRepository[c.SeminarMaterialTopic]
    literature_items: ContentRepository[c.LiteratureItem]
    homework_attachments: ContentLinkRepository[c.HomeworkAttachment]
    problem_attachments: ContentLinkRepository[c.ProblemAttachment]
    seminar_attachments: ContentLinkRepository[c.SeminarAttachment]
    literature_attachments: ContentLinkRepository[c.LiteratureAttachment]
    ticket_sets: ContentRepository[c.TicketSet]
    tickets: ContentLinkRepository[c.Ticket]
    ticket_problems: ContentLinkRepository[c.TicketProblem]
    ticket_problem_files: ContentLinkRepository[c.TicketProblemFile]
    ticket_assignments: ContentLinkRepository[c.TicketAssignment]
    work_programs: ContentRepository[p.WorkProgram]
    program_modules: ContentLinkRepository[p.ProgramModule]
    program_works: ContentLinkRepository[p.ProgramWork]
    program_topics: ContentLinkRepository[p.ProgramTopic]
    seminar_problems: ContentLinkRepository[p.SeminarProblem]
    module_topics: ContentLinkRepository[p.ProgramModuleTopic]
    program_skills: ContentLinkRepository[p.ProgramSkill]
    program_materials: ContentLinkRepository[p.ProgramMaterial]
    program_literature: ContentLinkRepository[p.ProgramLiterature]
    program_attachments: ContentLinkRepository[p.ProgramAttachment]
    homework_packs: ContentRepository[p.HomeworkPack]
    homework_pack_works: ContentLinkRepository[p.HomeworkPackWork]
    homework_pack_attachments: ContentLinkRepository[p.HomeworkPackAttachment]
    methodical_materials: ContentRepository[p.MethodicalMaterial]
    methodical_attachments: ContentLinkRepository[p.MethodicalAttachment]
    knowledge_entries: ContentRepository[p.KnowledgeEntry]
    knowledge_sources: ContentLinkRepository[p.KnowledgeSource]
    knowledge_materials: ContentLinkRepository[p.KnowledgeMaterial]
    definition_problems: ContentLinkRepository[p.DefinitionProblem]
    assessment_problems: ContentLinkRepository[p.AssessmentProblem]
    student_problem_assignments: ContentLinkRepository[p.StudentProblemAssignment]
    student_problem_files: ContentLinkRepository[p.StudentProblemFile]
    attempt_skill_results: ContentLinkRepository[p.AttemptSkillResult]
    assessment_attachments: ContentLinkRepository[p.AssessmentAttachment]
    problem_topics: ContentLinkRepository[p.ProblemTopic]
    problem_skills: ContentLinkRepository[p.ProblemSkill]
    definition_topics: ContentLinkRepository[p.DefinitionTopic]
    definition_skills: ContentLinkRepository[p.DefinitionSkill]
    methodical_topics: ContentLinkRepository[p.MethodicalTopic]
    methodical_skills: ContentLinkRepository[p.MethodicalSkill]
    knowledge_topics: ContentLinkRepository[p.KnowledgeTopic]
    knowledge_skills: ContentLinkRepository[p.KnowledgeSkill]

    directions: ContentRepository[q.Direction] | None = None
    course_programs: ContentRepository[q.CourseProgram] | None = None
    program_versions: ContentRepository[q.ProgramVersion] | None = None
    program_directions: ContentRepository[q.ProgramDirection] | None = None
    legacy_program_maps: ContentRepository[q.LegacyProgramMap] | None = None
    semester_plans: ContentRepository[q.SemesterPlan] | None = None
    plan_modules: ContentRepository[q.PlanModule] | None = None
    planned_works: ContentRepository[q.PlannedWork] | None = None
    plan_history: ContentRepository[q.PlanHistory] | None = None
    issued_works: ContentRepository[q.IssuedWork] | None = None
    scoring_rules: ContentRepository[q.ScoringRule] | None = None
    submissions: ContentRepository[q.Submission] | None = None
    reviews: ContentRepository[q.Review] | None = None
    review_grades: ContentRepository[q.ReviewGrade] | None = None
    review_files: ContentRepository[q.ReviewFile] | None = None
    review_returns: ContentRepository[q.ReviewReturn] | None = None
    required_work_sets: ContentRepository[q.RequiredWorkSet] | None = None
    required_work_bindings: ContentRepository[q.RequiredWorkBinding] | None = None
    answer_templates: ContentRepository[q.AnswerTemplate] | None = None
    debt_restorations: ContentRepository[q.DebtRestoration] | None = None
    version_references: ContentRepository[q.VersionReference] | None = None


Transaction = Callable[[], AbstractContextManager[Repositories]]


class Preferences(Protocol):
    def active_term(self) -> EntityId | None: ...
    def select_term(self, id: EntityId) -> None: ...
