"""Russian desktop copy and enum translations, independent of persisted values."""

from studium.application.errors import FrozenTaxonomyDependencyError
from studium.application.file_ports import FileIntegrity
from studium.application.services import ApplicationError
from studium.domain.communication import AuthorRole, CommunicationChannel, CommunicationState
from studium.domain.enums import (
    AssessmentType,
    AttemptResult,
    AttendanceStatus,
    EnrollmentStatus,
    GradeKind,
    ItemOutcome,
    StudentWorkStatus,
)
from studium.domain.repositories import RepositoryError, RepositoryFailure

TEXT = {
    "files_loading": "Чтение и проверка файлов…",
    "journal": "Журнал",
    "quick_attempt": "Записать попытку",
    "optional_grade": "Балл и оценка (необязательно)",
    "add_student_menu": "+ Добавить студента",
    "create_new_student": "Создать нового",
    "add_existing_student": "Добавить существующего",
    "onboarding_heading": "Начните учебный период в Studium",
    "onboarding_hint": "Три шага — и можно вести журнал, работы и посещаемость.",
    "step_term": "Шаг 1 · Создать учебный период",
    "step_course": "Шаг 2 · Добавить дисциплину",
    "step_group": "Шаг 3 · Создать группу",
    "group_course": "Создать группу и связать с дисциплиной",
    "journal_search": "Найти студента в журнале…",
    "journal_empty": "Добавьте студентов и работы, чтобы вести журнал.",
    "latest_activity": "Последняя активность",
    "student_file_empty": "У студента пока нет файлов. Добавьте их в сохранённую попытку или сообщение.",
    "questions_empty": "Вопросов по выбранным условиям пока нет.",
    "waiting_count": "Ожидают ответа: {count}",
    "bulk_attendance": "Отметить выбранных",
    "bulk_attendance_hint": "Выберите строки (Ctrl / Shift), затем статус. Сохранённые комментарии сохраняются.",
    "attendance_summary": "Посещаемость",
    "archive_student": "Удалить студента",
    "archive_student_confirm": "Архивировать студента во всех дисциплинах? Работы, файлы и вопросы сохранятся.",
    "files": "Файлы",
    "file_name": "Имя файла",
    "file_attempt": "Попытка",
    "file_add": "+ Добавить файл",
    "file_view": "Просмотреть",
    "file_preview": "Просмотр файла",
    "file_fit": "Вписать изображение в окно",
    "file_detach": "Убрать вложение",
    "file_refresh": "Обновить / проверить",
    "file_bytes": "байт",
    "file_empty": "Файлов пока нет. Выберите попытку и добавьте файлы.",
    "file_search": "Поиск по имени файла или работе…",
    "file_detach_confirm": "Убрать вложение из этой попытки? Файл и запись о прежней связи сохранятся.",
    "file_picker_filter": "Фото и PDF (*.jpg *.jpeg *.png *.webp *.pdf);;Документы (*.txt *.md *.csv *.tsv *.rtf *.docx *.xlsx *.pptx *.odt *.ods *.odp);;Все файлы (*)",
    "file_missing_hint": "Запись сохранена, но физический файл отсутствует. Он не считается удалённым.",
    "file_corrupted_hint": "Размер или SHA-256 не совпадает. Оригинал недоступен для безопасного открытия.",
    "file_metadata_only": "Встроенного preview для этого типа нет. Используйте «Открыть» для системного приложения.",
    "file_pdf_external": "QtPDF недоступен. Используйте «Открыть» для системного PDF-приложения.",
    "app": "Studium",
    "overview": "Обзор",
    "groups": "Группы",
    "works": "Работы",
    "settings": "Настройки",
    "period": "Учебный период",
    "new_period": "Новый период",
    "edit_period": "Изменить период",
    "courses": "Дисциплины",
    "new_course": "Новая дисциплина",
    "edit_course": "Изменить дисциплину",
    "new_group": "Новая группа",
    "edit_group": "Изменить группу",
    "create": "Создать",
    "add": "Добавить",
    "edit": "Изменить",
    "hide": "Удалить",
    "open": "Открыть",
    "save": "Сохранить",
    "cancel": "Отмена",
    "back": "← К группам",
    "name": "Название",
    "short_name": "Короткое название",
    "description": "Описание",
    "number": "Номер / название",
    "department": "Кафедра",
    "student_count": "Студентов",
    "notes": "Характеристика / заметки",
    "starts_on": "Начало",
    "ends_on": "Окончание",
    "students": "Студенты",
    "matrix": "Таблица работ",
    "course": "Дисциплина",
    "group": "Группа",
    "add_course": "Добавить дисциплину группе",
    "choose_course": "Выберите дисциплину",
    "new_student": "Новый студент",
    "existing_student": "Добавить из списка студентов",
    "edit_student": "Изменить студента",
    "student_card": "Карточка студента",
    "full_name": "ФИО",
    "preferred_name": "Обращение (необязательно)",
    "enrollment": "Участие",
    "search": "Поиск по ФИО…",
    "show_ended": "Показать завершивших участие",
    "withdraw": "Завершить участие",
    "student_work": "Работа студента",
    "status": "Состояние",
    "new_assessment": "Внеплановая работа",
    "edit_assessment": "Изменить работу",
    "assessment_title": "Название работы",
    "type": "Тип",
    "work_number": "Номер (необязательно)",
    "issued_at": "Дата и время выдачи",
    "due_at": "Срок сдачи",
    "max_score": "Максимальный балл",
    "work_notes": "Заметки о работе",
    "attempts": "Попыток",
    "history": "История попыток",
    "new_attempt": "+ Новая попытка",
    "attempt_number": "№",
    "occurred_at": "Дата предъявления",
    "result": "Результат попытки",
    "comment": "Комментарий преподавателя",
    "score": "Балл",
    "grade": "Оценка",
    "no_grade": "Без отдельной оценки",
    "pass": "Зачёт",
    "fail": "Незачёт",
    "grade_label": "Текст оценки",
    "score_hint": "Число, например 8,5; можно оставить пустым",
    "local_time": "Дата и время отображаются в часовом поясе Windows.",
    "issue_hint": "Если дату выдачи не задавать, сохранится время создания работы.",
    "history_hint": "Каждая сдача — новая запись. Предыдущие попытки доступны только для чтения.",
    "progress_hint": "Доработка и зачёт меняют итог. «Не принято» и комментарий сохраняют предыдущий итог.",
    "matrix_hint": "— Не предъявлено · ○ Предъявлено · ⚠ На доработку · ✓ Зачтено · ²/³ число записей истории. Клик / Enter — действие ячейки; меню — история.",
    "empty_start": "Начните с учебного периода, дисциплины и группы. Затем добавьте студентов и работы.",
    "overview_hint": "Выберите учебный период и откройте группу для работы со студентами.",
    "empty_groups": "Групп пока нет. Создайте первую группу.",
    "empty_offering": "Добавьте дисциплину этой группе в выбранном учебном периоде.",
    "empty_students": "Студентов пока нет. Добавьте нового или выберите из общего списка.",
    "empty_assessments": "Работ пока нет. Создайте домашнюю, контрольную или другую работу.",
    "empty_history": "Попыток пока нет. Добавьте первую сдачу.",
    "required": "Заполните обязательное поле: {field}.",
    "choose_row": "Выберите запись в таблице.",
    "choose_period": "Сначала создайте и выберите учебный период.",
    "choose_offering": "Сначала добавьте группе дисциплину в выбранном периоде.",
    "no_courses": "Сначала создайте дисциплину в разделе «Дисциплины».",
    "no_existing": "Нет доступных студентов. Создайте нового студента.",
    "confirm_title": "Подтверждение",
    "confirm_hide": "Удалить «{name}» из активного списка? История сохранится.",
    "confirm_withdraw": "Завершить участие студента в этой дисциплине? Работы и попытки сохранятся.",
    "confirm_student_hide": "Удалить студента из активной работы во всех дисциплинах? Участие, посещаемость, попытки и файлы сохранятся в истории.",
    "error_title": "Не удалось выполнить действие",
    "startup_error": "Не удалось открыть данные Studium. Проверьте доступ к папке данных и свободное место.",
    "unexpected": "Произошла ошибка. Повторите действие; если она повторится, проверьте доступ к папке данных.",
    "invalid_data": "Проверьте введённые значения и совместимость результата с оценкой.",
    "db_path": "Файл базы данных",
    "data_directory": "Папка данных",
    "app_version": "Версия приложения",
    "schema_version": "Версия схемы",
    "python_version": "Python",
    "qt_version": "Qt",
    "settings_hint": "Данные хранятся локально. Миграции применяются автоматически при запуске.",
    "read_only": "Участие завершено: история доступна для чтения.",
    "student_hide": "Удалить студента",
    "period_empty": "Нет учебного периода",
    "topics": "Темы",
    "skills": "Навыки",
    "learning_catalogue": "Темы и навыки",
    "lessons": "Занятия",
    "new_lesson": "+ Новое занятие",
    "lesson_date": "Дата занятия",
    "lesson_notes": "Заметки о занятии",
    "lesson_title": "Название занятия",
    "attendance": "Посещаемость",
    "new_topic": "Новая тема",
    "new_skill": "Новый навык",
    "parent_topic": "Родительская тема",
    "sort_order": "Порядок",
    "archive": "Удалить",
    "assessment_content": "Структура работы",
    "items": "Задания / части работы",
    "new_item": "Новая часть работы",
    "item_title": "Название задания / части работы",
    "up": "Выше",
    "down": "Ниже",
    "not_marked": "Не отмечено",
    "lesson_hint": "Выберите темы, которые реально разбирались на занятии.",
    "archive_topic_confirm": "Удалить тему и все её подтемы из активной работы? Учебные связи сохранятся.",
    "empty_lessons": "Занятий пока нет. Добавьте фактически состоявшееся занятие.",
    "catalogue_hint": "Темы и навыки общие для всех групп этой дисциплины.",
    "content_hint": "Выберите содержание, которое проверяет работа или её отдельная часть.",
}

ATTENDANCE_LABELS = {
    AttendanceStatus.PRESENT: "Присутствовал",
    AttendanceStatus.ABSENT: "Отсутствовал",
    AttendanceStatus.LATE: "Опоздал",
    AttendanceStatus.EXCUSED: "Уважительная причина",
    AttendanceStatus.UNKNOWN: "Неизвестно",
}

ASSESSMENT_LABELS = {
    AssessmentType.HOMEWORK: "Домашняя работа",
    AssessmentType.TEST: "Тест",
    AssessmentType.CONTROL_WORK: "Контрольная работа",
    AssessmentType.DEFENSE: "Защита",
    AssessmentType.LAB: "Лабораторная работа",
    AssessmentType.EXAM: "Экзамен",
    AssessmentType.OTHER: "Другое",
}
ATTEMPT_LABELS = {
    AttemptResult.PRESENTED: "Предъявлено",
    AttemptResult.NEEDS_REVISION: "На доработку",
    AttemptResult.ACCEPTED: "Зачтено",
    AttemptResult.SCORED: "Выставлен балл",
    AttemptResult.REJECTED: "Не принято",
    AttemptResult.COMMENT_ONLY: "Комментарий",
}
STATUS_LABELS = {
    StudentWorkStatus.NOT_STARTED: "— Не предъявлено",
    StudentWorkStatus.SUBMITTED: "○ Предъявлено",
    StudentWorkStatus.REVISION_REQUIRED: "⚠ На доработку",
    StudentWorkStatus.ACCEPTED: "✓ Зачтено",
    StudentWorkStatus.MISSED: "Пропущено",
    StudentWorkStatus.EXEMPT: "Освобождён",
    StudentWorkStatus.CANCELLED: "Отменено",
}
ENROLLMENT_LABELS = {
    EnrollmentStatus.ACTIVE: "Участвует",
    EnrollmentStatus.WITHDRAWN: "Участие завершено",
    EnrollmentStatus.COMPLETED: "Обучение завершено",
}
GRADE_LABELS = {
    GradeKind.PASS_FAIL: "Зачёт / незачёт",
    GradeKind.NUMERIC: "Числовая оценка",
    GradeKind.TRADITIONAL: "Текстовая / традиционная оценка",
}

REPOSITORY_ERRORS = {
    RepositoryFailure.NOT_FOUND: "Запись больше недоступна. Обновите список.",
    RepositoryFailure.DUPLICATE: "Такая запись уже существует или участие пересекается с предыдущим.",
    RepositoryFailure.INVALID_REFERENCE: "Для этой операции нужны активные группа, дисциплина, работа и участие студента.",
    RepositoryFailure.REVISION_CONFLICT: "Запись изменена в другом окне. Откройте её заново перед редактированием.",
    RepositoryFailure.IMMUTABLE_FACT: "Сохранённый факт нельзя перезаписать. Добавьте новую запись.",
    RepositoryFailure.INVALID_DATA: TEXT["invalid_data"],
    RepositoryFailure.STORAGE_UNAVAILABLE: "Хранилище недоступно или занято. Повторите действие и проверьте доступ к папке данных.",
}
APPLICATION_ERRORS = {
    "backup_cancelled": "Операция отменена. Временные файлы удалены.",
    "backup_pending_import": "Есть незавершённый импорт. Перезапустите Studium для штатного восстановления и повторите действие.",
    "backup_unsafe_path": "Выберите путь вне Git и хранилища Studium, без символических ссылок и junctions.",
    "backup_destination_parent": "Родительский каталог назначения должен существовать.",
    "backup_destination_not_empty": "Выберите отдельный пустой каталог. Непустое хранилище перезаписывать нельзя.",
    "backup_destination_changed": "Каталог назначения изменился во время операции. Повторите выбор.",
    "backup_source_changed": "Данные изменились во время операции или после предпросмотра. Архив не опубликован; повторите проверку.",
    "backup_checksum": "Размер или SHA-256 не совпадает. Файл повреждён; восстановление недоступно.",
    "backup_file_invalid": "Архив не соответствует управляемым файлам в снимке БД.",
    "backup_archive_invalid": "Архив повреждён или имеет некорректную структуру.",
    "backup_archive_unsafe": "Архив содержит небезопасные или повторяющиеся записи.",
    "backup_manifest_invalid": "Описание резервной копии отсутствует или некорректно.",
    "backup_format_unsupported": "Формат или версия резервной копии не поддерживается этой версией Studium.",
    "backup_schema_unsupported": "Версия или структура схемы не поддерживается. Восстановление недоступно.",
    "backup_database_invalid": "Снимок SQLite не прошёл проверку целостности или связей.",
    "backup_limits": "Архив превышает безопасные ограничения по размеру, количеству записей или сжатию.",
    "backup_snapshot_busy": "Не удалось получить согласованный снимок SQLite за отведённое время. Повторите действие.",
    "file_missing": "Файл не найден во внутреннем хранилище Studium. Запись и учебный контекст сохранены.",
    "file_corrupted": "Файл повреждён: размер или SHA-256 не совпадает. Запись сохранена.",
    "file_permission": "Нет доступа к файлу или папке Studium. Проверьте разрешения Windows.",
    "file_disk_full": "Недостаточно свободного места для сохранения файла.",
    "file_io_error": "Не удалось прочитать или сохранить файл. Проверьте папку данных и свободное место.",
    "file_invalid_source": "Выберите обычный файл, а не папку, ссылку или специальный файл.",
    "file_type_blocked": "Этот тип файла нельзя прикрепить. Исполняемые файлы, скрипты и ярлыки запрещены.",
    "file_too_large": "Файл превышает допустимый размер 1 ГиБ.",
    "file_source_changed": "Исходный файл изменился во время копирования. Повторите импорт после сохранения источника.",
    "file_unsafe_path": "Небезопасный путь в хранилище. Проверьте, что папки Studium не заменены ссылками.",
    "file_storage_busy": "Хранилище файлов занято другим окном Studium. Повторите действие.",
    "file_storage_unavailable": "Файловое хранилище не подключено.",
    "file_open_failed": "Windows не смогла открыть файл. Проверьте установленное приложение для этого типа.",
    "file_open_blocked": "Этот файл сохранён для учёта; открытие бинарного типа из Studium запрещено.",
    "file_preview_unsupported": "Встроенный просмотр не поддерживает этот формат. Используйте системное приложение.",
    "file_preview_invalid": "Не удалось прочитать изображение или PDF. Проверьте формат файла.",
    "file_preview_too_large": "Размер изображения превышает лимит безопасного preview (50 млн пикселей).",
    "file_preview_cache_failed": "Не удалось сохранить preview. Проверьте папку кэша и свободное место.",
    "file_finalize_pending": "Файл сохранён и связан с попыткой. Не удалось очистить журнал импорта; повторять импорт не нужно. Перезапустите Studium после проверки доступа к папке данных.",
    "file_rollback_pending": "Импорт не сохранён в БД, очистка файла отложена. Проверьте доступ к папке данных и перезапустите Studium.",
    "file_journal_invalid": "Журнал импорта повреждён. Файлы не удалены. Проверьте папку данных.",
    "file_attempt_required": "Сначала сохраните и выберите попытку для прикрепления файлов.",
    "file_link_detached": "Вложение уже убрано. Обновите список.",
    "file_asset_in_use": "Файл ещё связан с попыткой; сначала уберите вложение.",
    "inactive_student": "Студент скрыт из активного списка.",
    "already_withdrawn": "Участие уже завершено.",
    "hidden_work": "Работа скрыта; её нельзя создать повторно.",
    "grade_result_mismatch": "Зачёт требует результата «Зачтено», незачёт — «На доработку» или «Не принято».",
    "numeric_grade_requires_score": "Для числовой оценки введите балл.",
    "invalid_grade": TEXT["invalid_data"],
    "active_enrollment_required": "Для новой попытки требуется активное участие студента в дисциплине.",
    "concurrent_attempt": "История изменяется в другом окне. Повторите добавление попытки.",
    "unsafe_data_directory": "Папка данных указывает внутрь Git-репозитория. Выберите папку вне репозитория; проверьте LOCALAPPDATA и --data-dir.",
    "preferences_unavailable": "Не удалось сохранить выбранный период. Проверьте доступ к папке данных.",
    "invalid_number": "Введите числовой балл или оставьте поле пустым.",
    "topic_cycle": "Тема не может быть своей подтемой. Выберите другую родительскую тему.",
    "learning_course_mismatch": "Тема и навык должны относиться к той же дисциплине, что занятие или работа.",
    "learning_context_immutable": "Учебный контекст сохранённой записи нельзя менять.",
    "attendance_context_mismatch": "Выберите участие студента в дисциплине этого занятия.",
    "attendance_snapshot_required": "Посещаемость уже отмечена. Обновите список перед изменением.",
    "item_order_incomplete": "Состав частей работы изменился. Обновите список перед сменой порядка.",
}

FILE_LABELS = {
    FileIntegrity.AVAILABLE: "Доступен",
    FileIntegrity.MISSING: "Файл отсутствует",
    FileIntegrity.CORRUPTED: "Файл повреждён",
}
DOMAIN_ERRORS = {
    "AcademicTerm ends before it starts": "Окончание периода должно быть не раньше начала.",
    "due_at precedes issued_at": "Срок сдачи должен быть не раньше даты выдачи.",
    "score must be finite and nonnegative": "Балл должен быть конечным числом не меньше нуля.",
    "max_score must be finite and positive": "Максимальный балл должен быть конечным числом больше нуля.",
    "score cannot exceed max_score": "Балл не может превышать максимум.",
    "SCORED requires a numeric score": "Для результата «Выставлен балл» введите балл.",
    "updated_at cannot move backwards": "Время Windows изменилось. Проверьте часы перед сохранением.",
    "sort_order must be a nonnegative integer": "Порядок должен быть целым числом не меньше нуля.",
    "Topic cannot be its own parent": "Тема не может быть своей подтемой.",
}


def error_message(error):
    if isinstance(error, FrozenTaxonomyDependencyError):
        kinds = {
            "version": "Версия программы",
            "planned_work": "Работа плана",
            "student_assignment": "Назначение студенту",
        }
        lines = [
            f"{kinds[v.kind]}: {v.title} · {' · '.join(v.context)} · {v.id}"
            for v in error.dependencies
        ]
        return (
            "Архивирование отменено: тема или навык используются в сохранённом содержании. "
            "Они нужны для выдачи и сохранения классификации прежних назначений.\n\n"
            + "\n".join(lines)
        )
    if isinstance(error, RepositoryError):
        return REPOSITORY_ERRORS[error.failure]
    if isinstance(error, ApplicationError):
        return APPLICATION_ERRORS.get(str(error), TEXT["invalid_data"])
    if isinstance(error, ValueError):
        return DOMAIN_ERRORS.get(str(error), TEXT["invalid_data"])
    return TEXT["unexpected"]


def context_label(context):
    return f"{context.course.short_name or context.course.name} · {context.group.number} · {context.term.name}"


# Phase 5 correspondence labels (storage enums remain language-independent).
TEXT.update(
    {
        "questions": "Вопросы",
        "question_body_required": "Введите исходный текст сообщения.",
        "question_student_required": "Выберите студента. Сначала добавьте его в группу.",
        "new_question": "Новый вопрос",
        "question_case": "Вопрос и переписка",
        "message": "Сообщение",
        "channel": "Канал",
        "sent_at": "Дата / время",
        "author": "Автор",
        "paste_message": "Вставить текст из буфера",
        "question_title": "Тема вопроса",
        "question_context": "Учебный контекст",
        "question_no_offering": "Общий вопрос · без дисциплины",
        "student_message": "+ Сообщение студента",
        "teacher_message": "+ Ответ преподавателя",
        "question_close": "Закрыть вопрос",
        "question_reopen": "Открыть снова",
        "question_archive": "Архивировать вопрос",
        "question_archive_confirm": "Скрыть вопрос из активного списка? Переписка и вложения сохранятся.",
        "question_link": "Добавить связь",
        "question_unlink": "Убрать связь",
        "question_open_work": "Открыть связанную работу",
        "questions_all": "Все",
        "questions_search": "Поиск по студенту, теме вопроса и тексту сообщений",
        "questions_scope": "Сохранённые вопросы за все учебные периоды. Канал показывает последнее сообщение. Ответ сохраняется в Studium.",
    }
)
CHANNEL_LABELS = {
    CommunicationChannel.MANUAL: "Вручную",
    CommunicationChannel.EMAIL: "Email",
    CommunicationChannel.TELEGRAM: "Telegram",
    CommunicationChannel.OTHER: "Другое",
}
COMMUNICATION_STATES = {
    CommunicationState.WAITING: "Ожидает ответа",
    CommunicationState.ANSWERED: "Ответ дан",
    CommunicationState.CLOSED: "Закрыт",
}
AUTHOR_LABELS = {AuthorRole.STUDENT: "Студент", AuthorRole.TEACHER: "Преподаватель"}
QUESTION_CONTEXT_LABELS = {
    "assessment": "Работа",
    "attempt": "Попытка",
    "topic": "Темы",
    "skill": "Навыки",
}
APPLICATION_ERRORS.update(
    {
        "problem_variant_required": "Выберите конкретный вариант схемы из семейства задач.",
        "problem_variant_inherits_classification": "Темы, навыки и назначение задаются в общем условии семейства.",
        "homework_requires_revision": "Для домашнего задания выберите «На доработку»; результат «Не принято» доступен другим видам работ.",
        "lesson_cancelled": "Занятие отменено. Перенесите его перед изменением посещаемости.",
        "program_context_has_facts": "В этом контексте уже есть учебные факты. Создайте отдельный контекст для другой программы.",
        "assessment_content_locked": "После первой попытки структура работы сохраняется. Для другого состава создайте новую работу.",
        "problem_assignment_has_snapshot": "Задачи уже назначены со снимком условия. Для другого состава создайте новый рубежный контроль; выданная история сохраняется.",
        "ticket_control_required": "Свяжите набор вариантов с рубежным контролем перед применением задач для проверки.",
        "control_work_required": "Это действие доступно для рубежного контроля.",
        "ticket_task_count_mismatch": "Число частей рубежного контроля должно совпадать с числом задач в варианте.",
        "question_student_required": TEXT["question_student_required"],
        "question_closed": "Вопрос закрыт. Откройте его снова перед добавлением сообщения.",
        "question_message_date": "Дата сообщения предшествует открытию вопроса.",
        "question_close_date": "Закрытие не может предшествовать последнему сообщению.",
        "question_offering_required": "Для учебных связей создайте вопрос с выбранной дисциплиной и группой.",
        "question_context_mismatch": "Связь должна относиться к дисциплине вопроса, а попытка — к тому же студенту.",
        "external_message_conflict": "Внешнее сообщение уже сохранено с другими фактами. Требуется явное разрешение конфликта.",
    }
)
DOMAIN_ERRORS.update(
    {
        "body must not be blank": "Введите текст сообщения.",
        "Question closes before opening": "Закрытие не может предшествовать открытию вопроса.",
    }
)

TEXT.update(
    {
        "progress": "Прогресс",
        "analytics": "Аналитика",
        "assessment_results": "Результаты",
        "evidence": "Факты по темам и навыкам",
        "analytics_refresh": "Обновить показатели",
        "no_data": "Нет данных",
        "not_applicable": "Не применимо",
        "compare_at": "Сравнить с моментом",
        "comparison_at": "Момент сравнения (часовой пояс Windows)",
        "analytics_scope": "Показатели рассчитаны по сохранённым фактам. Сравнение использует даты фактов; оно не восстанавливает прежние редакции и архивирования.",
        "evidence_hint": "Наблюдаемые факты: попытки, результаты частей, вопросы и занятия. Количество вопросов и посещение темы не оценивают знание.",
        "item_results": "Результаты частей работы",
        "record_item_result": "Записать результат части",
        "item_result_hint": "Результат относится к выбранной попытке и сохраняется в истории. Для исправления работы добавьте новую попытку. Достаточно результата или балла.",
        "content_locked_hint": "После первой попытки содержание работы и учебные связи защищены от изменений. Можно менять порядок отображения; новые задания оформляйте отдельной работой.",
    }
)
ITEM_OUTCOME_LABELS = {
    ItemOutcome.CORRECT: "Верно",
    ItemOutcome.PARTIAL: "Частично",
    ItemOutcome.INCORRECT: "Неверно",
    ItemOutcome.NOT_EVALUATED: "Не оценивалось",
}
APPLICATION_ERRORS.update(
    {
        "content_semantic_locked": TEXT["content_locked_hint"],
        "frozen_taxonomy_archived": "Сохранённая классификация содержит архивную или отсутствующую тему/навык. Назначьте новое согласованное содержание. Прежняя версия и её связи не изменяются.",
        "insufficient_problem_pool": "Недостаточно подходящих задач для указанного числа различных вариантов. Добавьте задачи, уменьшите число вариантов или измените критерии.",
        "duplicate_variant": "Такой состав уже есть в другом варианте. Выберите другую задачу.",
        "problem_not_eligible": "Задача не подходит под критерии или уже включена в этот вариант.",
        "variant_roster_count_mismatch": "Число вариантов должно совпадать с текущим числом студентов для автоматического назначения. Измените количество или отключите автоматическое назначение.",
        "invalid_ticket_draft": "Состав черновика изменился или не соответствует критериям. Сформируйте варианты заново.",
        "item_result_empty": "Укажите результат части или балл.",
        "item_result_context_mismatch": "Часть работы должна относиться к работе выбранной попытки.",
        "item_result_exists": "Для этой части уже сохранён результат. Новое предъявление оформляйте новой попыткой.",
    }
)
