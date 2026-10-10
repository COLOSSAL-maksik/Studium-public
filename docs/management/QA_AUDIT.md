# Архитектурный аудит Studium QA

Аудит 30/30 на `main` / `ef5414faa594eba0f339d4208d605c92e98de903`. 2026-10-10.
**2 реализовано по коду, 22 частично, 6 отсутствует; 0 закрытых manual acceptance.**
[Требования](QA_REGISTER.md), [точный план QA-A](#qa-a-pr-plan),
[блокирующие контракты](#blocking-contracts).

## Метод и границы доказательств

Прочитаны действующие [AGENTS.md](../../AGENTS.md), [README](../../README.md),
[архитектура](../architecture.md), [модель данных](../data-model.md),
[технические ADR/OPEN](../decisions.md), management docs, domain/application,
ORM/SQL/репозитории, UI и существующие synthetic tests.
Для каждого ID ниже перечислены конкретные production symbols и test functions.
Это **статическое evidence**: существующий тест проверяет указанную основу,
но не доказывает весь новый сценарий и в этом аудите не запускался.
Наличие инфраструктуры отмечается как частичная реализация, если требуемая
семантика/пользовательский путь отсутствует. Visual defect без native воспроизведения
не объявляется доказанным дефектом текущего main.

Публичные workflow results базового SHA подтверждены отдельно чтением GitHub:
[Quality](https://github.com/COLOSSAL-maksik/Studium-public/actions/runs/38081188251)
и [Repository safety](https://github.com/COLOSSAL-maksik/Studium-public/actions/runs/38081144482)
— completed/success. Это прежние результаты базы, не проверки QA и не manual PASS.
`main` защищён, required contexts — quality/repository-safety.

Этот PR изменяет только Markdown docs. Код, миграции, dependencies, CI,
installer и Bender не меняются. Actions не запускаются; приложение, pytest/Ruff,
package/Windows/manual checks **NOT RUN**. Проверки документации и repository
safety фиксируются в описании PR. Реализация QA-A не начата, merge не выполняется.

## Архитектурные выводы

1. Каноническая дисциплина — Course, контекст преподавания — CourseOffering.
   WorkProgram сейчас объединяет reusable содержание и календарь периода.
   Направление — один свободный текст; version — display field, не история редакций.
2. Head schema `0009_daily_workflow`, 79 user tables. ProgramModule/ProgramWork
   принадлежат WorkProgram, выдача копирует часть плана в Assessment. Их последующие
   изменения не синхронизированы. SQLite range/scope guards предотвращают часть
   конфликтов, но revision counter не хранит before/after plan history.
3. Attempt — immutable факт с attempt_no; результат StudentWork вычисляется по
   номеру, не по occurred_at. Grade optional, NUMERIC равна Attempt score/max.
   PRESENTED/NEEDS_REVISION/ACCEPTED заменяют status/score, SCORED меняет score и
   не означает зачёт; REJECTED/COMMENT_ONLY нейтральны. Новый Homework REJECTED
   запрещён. Эти contracts нельзя незаметно заменить последним review event.
4. Числа float/REAL не удовлетворяют exact decimals. Min отсутствует; max у
   Assessment блокируется после первой Attempt (ADR-030), Attempt.max — historical
   snapshot. Для QA-030 нужна новая версия правил с exact facts, а не снятие lock.
5. FileAsset bytes/UUID/hash immutable; attach/import/recovery уже есть. Pending
   picker пока хранит пути без карточек; existing-owner import имеет немедленные
   side effects. Review/return не представлены отдельными событиями, поэтому
   queue по pending submission нельзя надёжно получить из одной Grade.
6. Journal bulk-read/frozen view сохраняются. Текущая колонка посещаемости — неделя
   с несколькими Lessons, header module/kind. QA-A меняет plan/deadline position;
   полная module/week/lesson/work структура — QA-B, без переписывания фактов.
7. Topic hierarchy/cycle locks/distinct analytics уже есть; problem editor плоский.
   Generator/snapshots есть, но group-level route. Central design/calendar есть;
   KnowledgeWidget уже имеет требуемый порядок и empty/list switch.

## Предлагаемые границы новых данных

Это проектное предложение для последующих PR, не принятая или выполненная миграция.
Сначала фиксируются контракты B1–B6 и mapping/guards в QA-A-PR-01.

- Независимые program content/version tables становятся каноническим содержанием
  программы. Legacy work_programs с обязательным term остаются compatibility/history,
  explicit map связывает старый UUID и новую версию. Не объединять записи по имени.
  В новом UI новая программа создаётся без legacy семестрового поля.
- Direction/ProgramDirection — normalized codes/names, один список на программу;
  code identity не зависит от display name. Свободная legacy строка сохраняется.
- SemesterPlan на конкретном CourseOffering содержит календарь/offset и draft state;
  его PlanModule/PlannedAssessment содержат независимые сроки, связи с content
  module/definition и стабильную идентичность. Один content используется многими
  планами; изменение plan не изменяет другую группу или содержание банка.
- Immutable PlanRevision/PlanChange хранит первоначально зафиксированный и current
  план, причины/время/affected IDs. Старое утраченное прошлое не реконструируется.
  Preview без записи; подтверждённый пакет — одна transaction с revision checks.
- Planned issue отдельно от фактического IssuanceEvent; legacy issued_at остаётся
  исходным фактом с unknown provenance. Exact due_at имеет прежний приоритет над
  week-only сроком; actual issue не изменяется при reschedule.
- ScoringRule версионируется отдельно от locked legacy Assessment.max_score;
  exact result/rule snapshot привязан к Attempt/Grade. Рекомендуется Decimal в
  domain и scaled INTEGER после фиксации precision/range B4; old REAL сохраняется
  literal legacy fact. Не кастовать exact значение в REAL для сравнения/записи.
- QA-B добавит concrete review/return/student-file/teacher-file links к submission,
  без polymorphic owner и автоматической отправки; queue/summary derived bulk DTO.
  Связь review→Attempt/Grade и numbering должна быть определена до score contracts.

Дополнительные факты включаются в прежние backup/recovery и deletion contracts;
стабильные FK, soft delete, no physical cascade, immutable bytes остаются.
Каждая новая schema должна иметь frozen SQL и явные SQLite triggers/indexes;
никакого create_all/reset, переписывания historical migrations или blind cloning.

## Матрица реализации

| ID | Этап | Приоритет | Реализация по коду | Требование |
|---|---|---|---|---|
| ST-QA-002 | QA-A | P2 | Отсутствует | [Несколько направлений подготовки у рабочей программы](QA_AUDIT.md#st-qa-002) |
| ST-QA-003 | QA-A | P2 | Частично | [Единая рабочая программа на весь курс дисциплины](QA_AUDIT.md#st-qa-003) |
| ST-QA-006 | QA-A | P2 | Отсутствует | [Понятные отображаемые названия рабочих программ](QA_AUDIT.md#st-qa-006) |
| ST-QA-010 | QA-A | P2 | Частично | [План семестра перед формированием журнала](QA_AUDIT.md#st-qa-010) |
| ST-QA-011 | QA-A | P2 | Частично | [Гибкое изменение сроков модулей и работ](QA_AUDIT.md#st-qa-011) |
| ST-QA-013 | QA-A | P2 | Частично | [Плановая и фактическая дата выдачи ДЗ](QA_AUDIT.md#st-qa-013) |
| ST-QA-030 | QA-A | P1 | Частично | [Индивидуальные балльные границы каждой работы](QA_AUDIT.md#st-qa-030) |
| ST-QA-008 | QA-B | P2 | Частично | [Создание работ только в соответствующем разделе](QA_AUDIT.md#st-qa-008) |
| ST-QA-009 | QA-B | P2 | Частично | [Разделить работы по типам](QA_AUDIT.md#st-qa-009) |
| ST-QA-012 | QA-B | P1 | Частично | [Отдельные ячейки посещаемости, ДЗ и РК](QA_AUDIT.md#st-qa-012) |
| ST-QA-015 | QA-B | P2 | Отсутствует | [Цветовые обозначения посещаемости](QA_AUDIT.md#st-qa-015) |
| ST-QA-017 | QA-B | P1 | Отсутствует | [Единая очередь проверки работ](QA_AUDIT.md#st-qa-017) |
| ST-QA-027 | QA-B | P1 | Частично | [Регистрация сдачи из карточки студента](QA_AUDIT.md#st-qa-027) |
| ST-QA-028 | QA-B | P1 | Частично | [Проверенный преподавателем файл](QA_AUDIT.md#st-qa-028) |
| ST-QA-029 | QA-B | P1 | Частично | [Summary на главном экране прогресса студента](QA_AUDIT.md#st-qa-029) |
| ST-QA-014 | QA-C | P2 | Частично | [Генерация вариантов внутри конкретной работы](QA_AUDIT.md#st-qa-014) |
| ST-QA-021 | QA-C | P2 | Частично | [Миниатюры файлов до сохранения записи](QA_AUDIT.md#st-qa-021) |
| ST-QA-022 | QA-C | P2 | Отсутствует | [Структурированные правильные ответы](QA_AUDIT.md#st-qa-022) |
| ST-QA-023 | QA-C | P2 | Частично | [Настоящая иерархия тем и подтем](QA_AUDIT.md#st-qa-023) |
| ST-QA-001 | QA-D | P2 | Реализовано | [Единый выбор дат через календарь](QA_AUDIT.md#st-qa-001) |
| ST-QA-004 | QA-D | P3 | Частично | [Исправить оформление календарей](QA_AUDIT.md#st-qa-004) |
| ST-QA-005 | QA-D | P2 | Частично | [Единая дизайн-система компонентов](QA_AUDIT.md#st-qa-005) |
| ST-QA-007 | QA-D | P3 | Частично | [Кнопка «Добавить студента»](QA_AUDIT.md#st-qa-007) |
| ST-QA-016 | QA-D | P2 | Отсутствует | [Изменяемая высота области аналитики](QA_AUDIT.md#st-qa-016) |
| ST-QA-018 | QA-D | P2 | Частично | [Полностью кликабельные карточки](QA_AUDIT.md#st-qa-018) |
| ST-QA-019 | QA-D | P3 | Частично | [Убрать непонятную дублирующую кнопку «Навыки»](QA_AUDIT.md#st-qa-019) |
| ST-QA-020 | QA-D | P2 | Частично | [Контекстное меню дерева тем](QA_AUDIT.md#st-qa-020) |
| ST-QA-024 | QA-D | P2 | Частично | [Убрать пустые пространства и лишнюю прокрутку](QA_AUDIT.md#st-qa-024) |
| ST-QA-025 | QA-D | P2 | Реализовано | [Перестроить компоновку «Базы знаний»](QA_AUDIT.md#st-qa-025) |
| ST-QA-026 | QA-D | P2 | Частично | [Визуальные артефакты тёмной темы](QA_AUDIT.md#st-qa-026) |

## Карточки аудита

### QA-A

<a id="st-qa-002"></a>

#### ST-QA-002 — Несколько направлений подготовки у рабочей программы

**P2 · Отсутствует.** Есть только одно свободное поле WorkProgram.direction. Справочника кодов, необязательных названий и связи M2M нет; темы/definitions уже переиспользуются.

**Production evidence:**

- [src/studium/domain/program.py](../../src/studium/domain/program.py) — `WorkProgram`
- [src/studium/presentation/desktop/programs.py](../../src/studium/presentation/desktop/programs.py) — `ProgramForm`
- [src/studium/infrastructure/database/models/program.py](../../src/studium/infrastructure/database/models/program.py) — `WorkProgramRow`

**Существующие тесты основы (NOT RUN; новый полный сценарий ими не доказан):**

- [tests/integration/test_program_workflow.py](../../tests/integration/test_program_workflow.py) — `test_multiple_programs_exact_context_and_reusable_work`

- **Модель:** Direction(code, optional name) и ProgramDirection с конкретными FK, уникальностью нормализованного кода и пары; legacy direction сохраняется отдельно.
- **Сервисы:** CRUD справочника/связей через ProgramService, scope/version validation, optimistic revision и атомарная запись списка.
- **UI:** Множественный выбор/ввод направлений в форме программы; список кодов в read DTO.
- **Миграции:** Additive таблицы и явный backfill только однозначных кодов. Свободный текст не делить эвристически; неизвестное оставлять legacy + явный выбор преподавателя.
- **Зависимости:** Основа для 006; связывается с версией содержания 003.
- **Риски сохранности:** Автоматическое выделение кодов из произвольной строки и слияние по названию могут потерять смысл; не клонировать темы/задачи по направлению.
- **Критерии приёмки:** Одна программа с тремя кодами, необязательные названия, duplicate reject; legacy строка/UUID/links сохранены; одни и те же темы и задачи без копий.

**Ручная приёмка:** NOT RUN. **Закрывающий implementation PR:** отсутствует в этом аудите.

<a id="st-qa-003"></a>

#### ST-QA-003 — Единая рабочая программа на весь курс дисциплины

**P2 · Частично.** Course и CourseOffering разделены, но WorkProgram требует term_id, semester, first_week_start, weeks и offset. create_offering/set_offering_program отвергают другой период; version — строка, а не immutable редакция содержания.

**Production evidence:**

- [src/studium/domain/program.py](../../src/studium/domain/program.py) — `WorkProgram`; `ProgramModule`; `ProgramWork`
- [src/studium/application/program_services.py](../../src/studium/application/program_services.py) — `set_offering_program`; `_default_program`
- [src/studium/application/services.py](../../src/studium/application/services.py) — `create_offering`
- [src/studium/infrastructure/database/migrations/versions/v0007.sql](../../src/studium/infrastructure/database/migrations/versions/v0007.sql) — `course_offerings_program_context_insert`; `work_programs_calendar_lock`

**Существующие тесты основы (NOT RUN; новый полный сценарий ими не доказан):**

- [tests/integration/test_program_workflow.py](../../tests/integration/test_program_workflow.py) — `test_multiple_programs_exact_context_and_reusable_work`
- [tests/integration/test_program_migration.py](../../tests/integration/test_program_migration.py) — `test_populated_v6_copy_program_mapping_files_tickets_reopen`

- **Модель:** Независимое содержание программы и его версия; отдельный SemesterPlan на CourseOffering, календарь и экземпляры модулей/работ. Темы/definitions принадлежат содержанию, семестровое размещение — реализации.
- **Сервисы:** Разделить ProgramService content commands и offering-plan commands; analytics/calendar читают план выбранного offering. После фактов смена версии только явным безопасным workflow.
- **UI:** Программа без обязательного периода; выбор существующей версии в новом семестре; отдельная настройка календаря группы.
- **Миграции:** Предлагается additive canonical content/version + plan tables с explicit legacy mapping; старые NOT NULL work_programs и FK остаются compatibility/history. Не переписывать v1–v9 и не сливать legacy программы автоматически.
- **Зависимости:** 002; основа 006/010/011/013/030. Контракт версии требует ответа B1.
- **Риски сохранности:** Одна текущая программа может быть общей для групп: изменение календаря сейчас действует сразу на них. Backfill должен создать отдельные планы offering с сохранением календаря и старых ссылок.
- **Критерии приёмки:** Одна версия используется в двух периодах с разными календарями; изменение плана одной группы не меняет другую; все old IDs, facts, snapshots и assets остаются доступны.

**Ручная приёмка:** NOT RUN. **Закрывающий implementation PR:** отсутствует в этом аудите.

<a id="st-qa-006"></a>

#### ST-QA-006 — Понятные отображаемые названия рабочих программ

**P2 · Отсутствует.** Селекторы и таблицы показывают program.title; направление иногда отдельной колонкой. Общего вычисляемого display name с кодами/разрешением коллизий нет.

**Production evidence:**

- [src/studium/presentation/desktop/programs.py](../../src/studium/presentation/desktop/programs.py) — `OfferingProgramForm.reload_programs`; `DisciplinePage`; `WorkProgramPage.refresh`

**Существующие тесты основы (NOT RUN; новый полный сценарий ими не доказан):**

- [tests/integration/test_program_desktop.py](../../tests/integration/test_program_desktop.py) — `test_program_create_explicit_offering_and_enum_values`

- **Модель:** Computed read DTO/formatter: исходное title + упорядоченные коды + версия при коллизии; title не перезаписывается.
- **Сервисы:** Единый application query formatter для всех потребителей, стабильная сортировка кодов и контекст коллизий.
- **UI:** Применить в селекторах/таблицах/назначении; tooltip полного имени и доступность с клавиатуры.
- **Миграции:** Для самого display name не нужна; использует новые связи 002/003.
- **Зависимости:** 002 и 003.
- **Риски сохранности:** Не использовать вычисленное имя как identity и не менять source title. Версия/год должны различать записи, не выдумывать год.
- **Критерии приёмки:** Две одноимённые программы с разными кодами различимы во всех выборах; одинаковые коды различаются версией; длинное имя доступно целиком.

**Ручная приёмка:** NOT RUN. **Закрывающий implementation PR:** отсутствует в этом аудите.

<a id="st-qa-010"></a>

#### ST-QA-010 — План семестра перед формированием журнала

**P2 · Частично.** WorkProgramPage уже редактирует произвольные модули/работы; planned_works и issue_program_work идемпотентны. Это общий план программы, а не отдельный План семестра группы; create_offering автоматически создаёт default-программу.

**Production evidence:**

- [src/studium/presentation/desktop/programs.py](../../src/studium/presentation/desktop/programs.py) — `WorkProgramPage`; `ModuleForm`; `ProgramWorkForm`
- [src/studium/application/program_services.py](../../src/studium/application/program_services.py) — `planned_works`; `add_program_work`; `issue_program_work`
- [src/studium/application/services.py](../../src/studium/application/services.py) — `create_offering`

**Существующие тесты основы (NOT RUN; новый полный сценарий ими не доказан):**

- [tests/integration/test_program_workflow.py](../../tests/integration/test_program_workflow.py) — `test_module_bounds_overlap_and_work_date`; `test_planned_structure_creates_no_fake_attempts_and_issue_is_idempotent`
- [tests/integration/test_program_regressions.py](../../tests/integration/test_program_regressions.py) — `test_journal_30_by_17_and_charts_fixed_query_budget`

- **Модель:** SemesterPlan draft/configured, PlanModule, PlannedAssessment со stable IDs, типом, module, сроками и будущими scoring rules.
- **Сервисы:** Save plan атомарно, idempotent reopen, no duplicate assignments; change preview и guards наличия Attempt/Grade; чтение плана не выдаёт работу.
- **UI:** Вход План семестра после создания группы, Настроить позже, редактирование в течение семестра; журнал читает сохранённый план.
- **Миграции:** Additive plan tables/backfill 003; первоначальный snapshot только текущего известного плана, не реконструкция утраченного прошлого.
- **Зависимости:** 003; основа 011/013/030 и будущего 008/012.
- **Риски сохранности:** Нельзя удалять работы с фактами или повторно материализовать Assessment при reopen; soft delete с последствиями и историческим просмотром.
- **Критерии приёмки:** 17 и 18 недель, любое число непересекающихся модулей; отложенная настройка; повторное открытие без INSERT; история остаётся после удаления из активного плана.

**Ручная приёмка:** NOT RUN. **Закрывающий implementation PR:** отсутствует в этом аудите.

<a id="st-qa-011"></a>

#### ST-QA-011 — Гибкое изменение сроков модулей и работ

**P2 · Частично.** update_program_module/update_program_work и обычный edit Assessment доступны. SQLite защищает пересечения/границы, но нет before/after history, причины, предложения исправления и атомарного подтверждённого переноса нескольких элементов. Правка ProgramWork не обновляет уже выданную Assessment.

**Production evidence:**

- [src/studium/application/program_services.py](../../src/studium/application/program_services.py) — `update_program_module`; `update_program_work`
- [src/studium/application/services.py](../../src/studium/application/services.py) — `update_assessment`
- [src/studium/infrastructure/database/migrations/versions/v0007.sql](../../src/studium/infrastructure/database/migrations/versions/v0007.sql) — `program_modules_program_context_update`; `program_works_program_context_update`
- [src/studium/presentation/desktop/programs.py](../../src/studium/presentation/desktop/programs.py) — `ModuleForm`; `ProgramWorkForm`

**Существующие тесты основы (NOT RUN; новый полный сценарий ими не доказан):**

- [tests/integration/test_program_workflow.py](../../tests/integration/test_program_workflow.py) — `test_module_bounds_overlap_and_work_date`
- [tests/integration/test_program_desktop.py](../../tests/integration/test_program_desktop.py) — `test_work_schedule_week_constrains_date_and_updates`

- **Модель:** Immutable PlanRevision/PlanChange с old/new values, UTC, reason и explicit affected IDs; current pointer + original captured snapshot.
- **Сервисы:** Preview impact без записи, proposal с revisions, одна транзакция apply; не менять соседние модули без подтверждения. Перенос выданной работы должен согласовать план и current deadline без изменения сдач.
- **UI:** Диалог 6→7, список конфликтов, предлагаемые поправки, подтверждение; самостоятельный перенос ДЗ/РК и просмотр истории.
- **Миграции:** Additive history/revision tables. При отсутствии старого audit baseline обозначить как впервые зафиксированный, не исторически первоначальный.
- **Зависимости:** 010/003; совместная приёмка 013. B2 о выходе срока за модуль, B3 о датах.
- **Риски сохранности:** Промежуточные UPDATE могут конфликтовать с overlap triggers; apply должен валидировать итоговый набор и иметь rollback при позднем сбое/stale revision. Текущий timeliness пересчитывается, прошлые факты не редактируются.
- **Критерии приёмки:** 6→7 с конфликтом соседнего 7–12: cancel оставляет всё; подтверждённый пакет укладывается в 17 недель; история и reason сохранены; чужая revision вызывает полный rollback.

**Ручная приёмка:** NOT RUN. **Закрывающий implementation PR:** отсутствует в этом аудите.

<a id="st-qa-013"></a>

#### ST-QA-013 — Плановая и фактическая дата выдачи ДЗ

**P2 · Частично.** ProgramWork.issue_date/due_date и Assessment.issued_at/due_at/planned weeks есть. issued_at берётся из плановой issue_date либо clock; фактическая выдача не отделена. Journal ставит ДЗ после недель модуля и не задаёт колонке week; перенос плана и deadline расходятся.

**Production evidence:**

- [src/studium/domain/program.py](../../src/studium/domain/program.py) — `ProgramWork`
- [src/studium/domain/entities/__init__.py](../../src/studium/domain/entities/__init__.py) — `Assessment`
- [src/studium/application/program_services.py](../../src/studium/application/program_services.py) — `issue_program_work`; `_program_instant`
- [src/studium/application/journal.py](../../src/studium/application/journal.py) — `JournalService.journal`

**Существующие тесты основы (NOT RUN; новый полный сценарий ими не доказан):**

- [tests/integration/test_program_workflow.py](../../tests/integration/test_program_workflow.py) — `test_planned_structure_creates_no_fake_attempts_and_issue_is_idempotent`
- [tests/integration/test_content_workflow.py](../../tests/integration/test_content_workflow.py) — `test_week_overdue_only_after_last_day_and_exact_deadline_priority`; `test_planned_issue_and_legacy_without_weeks`

- **Модель:** Planned issue LocalDate, actual issue UtcInstant nullable + provenance, original/current due и module; Planned/Issued как явная проекция issuance fact.
- **Сервисы:** Отдельная явная выдача без Attempt; идемпотентность; change deadline не меняет actual issue; журнал вычисляет неделю current due, включая legacy exact due.
- **UI:** Даты и состояния в карточке ДЗ, выдача раньше начала модуля, новая позиция существующей work column.
- **Миграции:** Additive issuance facts/plan fields. Legacy issued_at сохранять буквально; его происхождение неоднозначно, actual issue не угадывать. Старые exact due не нормализовать молча.
- **Зависимости:** 010/011; B3. Закладка недели для ДЗ в QA-A, полная отдельная колонка каждого занятия — 012 в QA-B.
- **Риски сохранности:** Создание Assessment сейчас происходит по нажатию плановой ячейки: это нельзя автоматически считать подтверждённой выдачей. Учебный offset и midnight boundaries должны быть стабильны.
- **Критерии приёмки:** Плановая выдача на 2-й неделе, actual на 1-й, due 6→7: actual неизменна, UUID/история прежние, ДЗ перемещается на неделю 7, Planned не создаёт фактов сдачи.

**Ручная приёмка:** NOT RUN. **Закрывающий implementation PR:** отсутствует в этом аудите.

<a id="st-qa-030"></a>

#### ST-QA-030 — Индивидуальные балльные границы каждой работы

**P1 · Частично.** У Assessment свой nullable max_score; Attempt/Grade хранят nullable score/max, история immutable. Min отсутствует, числа float/SQLite REAL, UI number_value парсит QLineEdit в float, display_score форматирует через :g. ProgramWork не имеет границ; issue_program_work не переносит scoring. После первой Attempt max_score защищён semantic lock. Ниже-min guard отсутствует.

**Production evidence:**

- [src/studium/domain/entities/__init__.py](../../src/studium/domain/entities/__init__.py) — `Assessment`; `Attempt`; `Grade`
- [src/studium/domain/services/progress.py](../../src/studium/domain/services/progress.py) — `StudentWorkProgress.from_history`
- [src/studium/application/services.py](../../src/studium/application/services.py) — `add_attempt`; `_grade`
- [src/studium/application/journal.py](../../src/studium/application/journal.py) — `compact_progress`
- [src/studium/presentation/desktop/dialogs.py](../../src/studium/presentation/desktop/dialogs.py) — `number_value`
- [src/studium/presentation/desktop/models.py](../../src/studium/presentation/desktop/models.py) — `display_score`
- [src/studium/infrastructure/database/models/__init__.py](../../src/studium/infrastructure/database/models/__init__.py) — `AssessmentRow`; `AttemptRow`; `GradeRow`
- [src/studium/infrastructure/database/migrations/versions/v0005.sql](../../src/studium/infrastructure/database/migrations/versions/v0005.sql) — `assessments_semantic_lock`

**Существующие тесты основы (NOT RUN; новый полный сценарий ими не доказан):**

- [tests/unit/test_domain.py](../../tests/unit/test_domain.py) — `test_grade_variants_and_validation`; `test_rejected_comment_preserve_accepted_result`; `test_scored_does_not_mean_accepted`
- [tests/integration/test_application.py](../../tests/integration/test_application.py) — `test_invalid_grade_rolls_back_attempt`; `test_grade_variants`
- [tests/integration/test_analytics.py](../../tests/integration/test_analytics.py) — `test_scores_use_current_projection_and_attempt_maximum`

- **Модель:** ScoreValue на Decimal, индивидуальная версионируемая ScoringRule(min,max), immutable exact result/rule snapshot с FK к Attempt/Grade. Null, реальный 0 и nonnumeric state различны; min уже решён как нижняя граница начисления.
- **Сервисы:** Guard inclusive min≤score≤max, один numeric source of truth, Grade NUMERIC совпадает с Attempt; NEEDS_REVISION без баллов, SCORED не означает зачёт. Новая rule влияет только на последующие проверки.
- **UI:** Поля min/max плана; decimal input без float; score/max в журнале, student card, history, factual analytics и reporting. Использовать исторический denominator.
- **Миграции:** Additive exact-score/rule records, legacy REAL сохранены без реконструкции недоступной исходной точности. Старый semantic lock не ослаблять: новые версии правил независимы от locked max. SQL representation зависит от B4.
- **Зависимости:** 010/013; B4 о precision, B5 о review/Attempt и B6 о retro rule. Смысл min не является открытым вопросом.
- **Риски сохранности:** Преобразование REAL в Decimal не восстанавливает исходный текст. Нельзя автонулить pending/revision или перенормировать прошлые оценки. REJECTED нейтрален, запрещён для нового HOMEWORK; не менять legacy projection скрытно.
- **Критерии приёмки:** 18/30 и 30/30 разрешены, 17.99/30.01 отвергнуты; decimal roundtrip; pending/revision=null; 0 только если входит в диапазон; изменение rule не меняет прежнее 24/30; все виды Grade и legacy чтение сохранены.

**Ручная приёмка:** NOT RUN. **Закрывающий implementation PR:** отсутствует в этом аудите.

### QA-B

<a id="st-qa-008"></a>

#### ST-QA-008 — Создание работ только в соответствующем разделе

**P2 · Частично.** Создание работ уже есть в WorksPage/программе, однако в главной панели журнала toolbar вызывает create_assessment. new_assessment подписан как внеплановая работа.

**Production evidence:**

- [src/studium/presentation/desktop/pages.py](../../src/studium/presentation/desktop/pages.py) — `GroupsPage.__init__`; `GroupsPage.create_assessment`; `WorksPage.create`
- [src/studium/presentation/desktop/messages.py](../../src/studium/presentation/desktop/messages.py) — `TEXT`

**Существующие тесты основы (NOT RUN; новый полный сценарий ими не доказан):**

- [tests/integration/test_phase65_desktop.py](../../tests/integration/test_phase65_desktop.py) — `test_group_workspace_context_survives_navigation_and_refresh`

- **Модель:** Без изменения фактов AssessmentType; planned/unplanned — отдельный признак/связь.
- **Сервисы:** Переиспользовать прежние create/edit/hide commands в плане и Работах.
- **UI:** Убрать создание из панели журнала, дать входы в План семестра и Работы.
- **Миграции:** Не нужна для переноса действия.
- **Зависимости:** 010 и 009.
- **Риски сохранности:** Не удалять существующие внеплановые assessments и попытки; planned-cell issue отличается от создания definition.
- **Критерии приёмки:** В журнале нет кнопки создания, все старые работы/истории доступны, обе категории создаются в соответствующем разделе.

**Ручная приёмка:** NOT RUN. **Закрывающий implementation PR:** отсутствует в этом аудите.

<a id="st-qa-009"></a>

#### ST-QA-009 — Разделить работы по типам

**P2 · Частично.** AssessmentType, фильтры и student categories есть, но WorksPage группы — одна таблица с верхней панелью операций; четырёх подкатегорий и row context actions нет.

**Production evidence:**

- [src/studium/domain/enums/__init__.py](../../src/studium/domain/enums/__init__.py) — `AssessmentType`
- [src/studium/presentation/desktop/pages.py](../../src/studium/presentation/desktop/pages.py) — `WorksPage`
- [src/studium/presentation/desktop/student_works.py](../../src/studium/presentation/desktop/student_works.py) — `WORK_CATEGORIES`; `StudentWorksWidget`

**Существующие тесты основы (NOT RUN; новый полный сценарий ими не доказан):**

- [tests/integration/test_iteration4_workflows.py](../../tests/integration/test_iteration4_workflows.py) — `test_student_categories_three_attempts_files_and_progress_are_readonly`

- **Модель:** DTO grouping: HOMEWORK; CONTROL_WORK/TEST; EXAM; остальные — Другие, без изменения persisted enum.
- **Сервисы:** Переиспользовать list/create/edit/hide_assessment и content commands.
- **UI:** Четыре категории, + Добавить в каждой, пустые состояния, контекст строки Открыть/Изменить/Удалить/Структура.
- **Миграции:** Не нужна; mapping типов документировать.
- **Зависимости:** 010 для плановой выдачи; 008 использует новые входы.
- **Риски сохранности:** Не потерять LAB/DEFENSE/OTHER и TEST в фильтрах; planned/unplanned не переопределяет тип.
- **Критерии приёмки:** Каждый из семи persisted типов видим в ровно одной категории; row actions работают только с выбранной записью; старые UUID/facts прежние.

**Ручная приёмка:** NOT RUN. **Закрывающий implementation PR:** отсутствует в этом аудите.

<a id="st-qa-012"></a>

#### ST-QA-012 — Отдельные ячейки посещаемости, ДЗ и РК

**P1 · Частично.** Работы имеют свои колонки и attendance route, но JournalService объединяет все занятия недели в lessons tuple и value N/M; header группирует module/kind вместо module/week. matrix_menu добавляет quick_attempt и для attendance.

**Production evidence:**

- [src/studium/application/journal.py](../../src/studium/application/journal.py) — `JournalColumn`; `JournalService.journal`
- [src/studium/presentation/desktop/journal.py](../../src/studium/presentation/desktop/journal.py) — `JournalModel`; `GroupedJournalHeader`
- [src/studium/presentation/desktop/pages.py](../../src/studium/presentation/desktop/pages.py) — `matrix_menu`; `open_matrix_cell`; `open_journal_attendance`
- [src/studium/presentation/desktop/widgets.py](../../src/studium/presentation/desktop/widgets.py) — `JournalTable`

**Существующие тесты основы (NOT RUN; новый полный сценарий ими не доказан):**

- [tests/integration/test_iteration4_workflows.py](../../tests/integration/test_iteration4_workflows.py) — `test_bulk_attendance_changes_only_three_selected_cells`
- [tests/integration/test_program_regressions.py](../../tests/integration/test_program_regressions.py) — `test_journal_30_by_17_and_charts_fixed_query_budget`
- [tests/integration/test_iteration3_desktop.py](../../tests/integration/test_iteration3_desktop.py) — `test_frozen_journal_pixel_alignment_after_scroll`

- **Модель:** Read JournalColumn со stable lesson/assessment ID и module/week. Attendance/Attempt/Grade schema не заменять.
- **Сервисы:** Bulk snapshot, отдельная колонка каждого Lesson/Assessment, current due из QA-A; menu/action dispatch по column kind.
- **UI:** Header module→week→lesson/work; attendance без попыток; work cell score/state/history; frozen names и horizontal scroll.
- **Миграции:** Не нужна для представления; использует план/даты QA-A.
- **Зависимости:** 010/011/013/030; основа 015 и сквозной приёмки 027/028.
- **Риски сохранности:** Нельзя связывать историю по индексу колонки: перенос меняет индекс. Массовая attendance только explicit lesson/Enrollment; отменённое занятие сохраняется.
- **Критерии приёмки:** Две пары и два ДЗ в одной неделе дают четыре колонки, attendance-menu без attempt; 30×18+десятки работ без N+1, scroll/selection корректны после переноса.

**Ручная приёмка:** NOT RUN. **Закрывающий implementation PR:** отсутствует в этом аудите.

<a id="st-qa-015"></a>

#### ST-QA-015 — Цветовые обозначения посещаемости

**P2 · Отсутствует.** Коды attendance и central Colors есть; JournalModel возвращает ForegroundRole, но не BackgroundRole/status fills. Пять мягких заливок отсутствуют.

**Production evidence:**

- [src/studium/presentation/desktop/journal.py](../../src/studium/presentation/desktop/journal.py) — `JournalModel.data`
- [src/studium/presentation/desktop/widgets.py](../../src/studium/presentation/desktop/widgets.py) — `JournalRowDelegate`
- [src/studium/presentation/desktop/design.py](../../src/studium/presentation/desktop/design.py) — `Colors`
- [src/studium/application/journal.py](../../src/studium/application/journal.py) — `JournalService.journal`

**Существующие тесты основы (NOT RUN; новый полный сценарий ими не доказан):**

- [tests/integration/test_visual_desktop.py](../../tests/integration/test_visual_desktop.py) — `test_text_and_primary_action_contrast`
- [tests/integration/test_iteration4_workflows.py](../../tests/integration/test_iteration4_workflows.py) — `test_bulk_attendance_changes_only_three_selected_cells`

- **Модель:** Только typed attendance status в cell DTO, без новых учебных данных.
- **Сервисы:** Нет нового бизнес-сервиса.
- **UI:** Central status palette и delegate/BackgroundRole, текстовые коды и contrast selected state.
- **Миграции:** Не нужна.
- **Зависимости:** 012; общая палитра согласуется с 005 позднее.
- **Риски сохранности:** Агрегат N/M не имеет единственного attendance status; заливки вводить после раздельных колонок. Selection не скрывает символ.
- **Критерии приёмки:** Пять состояний читаемы в Light/Dark, selected/unselected, 100/125/150%; значения Attendance не меняются.

**Ручная приёмка:** NOT RUN. **Закрывающий implementation PR:** отсутствует в этом аудите.

<a id="st-qa-017"></a>

#### ST-QA-017 — Единая очередь проверки работ

**P1 · Отсутствует.** Attempt.occurred_at и metadata.created_at различают предъявление и ввод; history/analytics есть. Общей очереди ДЗ/РК, configurable 7 дней и завершения review конкретной pending Attempt нет.

**Production evidence:**

- [src/studium/domain/entities/__init__.py](../../src/studium/domain/entities/__init__.py) — `Attempt`
- [src/studium/application/services.py](../../src/studium/application/services.py) — `add_attempt`; `student_recent_activity`
- [src/studium/presentation/desktop/main_window.py](../../src/studium/presentation/desktop/main_window.py) — `MainWindow.refresh`
- [src/studium/application/analytics.py](../../src/studium/application/analytics.py) — `AnalyticsService`

**Существующие тесты основы (NOT RUN; новый полный сценарий ими не доказан):**

- [tests/integration/test_analytics.py](../../tests/integration/test_analytics.py) — `test_deadline_min_timestamp_not_attempt_number_and_denominator`

- **Модель:** Explicit submission/review lifecycle 028; preference calendar-day SLA=7. Queue DTO derived из pending facts, не persisted aggregate.
- **Сервисы:** Bulk all-group FIFO query occurred_at + deterministic UUID tie-break; age/deadline/near-due, контекст student/group/course/files; не путать вопросы с работами.
- **UI:** Главная counts/oldest, общая queue и local warnings; filters; reviewed уходит из active projection, остаётся history.
- **Миграции:** Review facts из 028; preference без учебной миграции; indexes подтверждаются query budget.
- **Зависимости:** 027→028→017; B5 lifecycle, B7 calendar-day boundary/near-due. Preview QA-B обязателен до окончательной унификации 021.
- **Риски сохранности:** Новая grade Attempt не должна выглядеть как повторная сдача. Старые PRESENTED без review links требуют консервативного legacy reconciliation, не guess удаления.
- **Критерии приёмки:** Все группы, backdated capture, equal timestamps и новая сдача; due ровно 7 calendar days в выбранном offset; reviewed удаляется только из active view; query count не растёт по строкам.

**Ручная приёмка:** NOT RUN. **Закрывающий implementation PR:** отсутствует в этом аудите.

<a id="st-qa-027"></a>

#### ST-QA-027 — Регистрация сдачи из карточки студента

**P1 · Частично.** Из карточки доступны история/записать попытку; service присваивает новый номер, files добавляются после сохранения Attempt отдельно. Единой формы сдачи с мультифайлами и preview/cancel до commit нет.

**Production evidence:**

- [src/studium/presentation/desktop/student_works.py](../../src/studium/presentation/desktop/student_works.py) — `StudentWorksWidget.open_selected_work`
- [src/studium/presentation/desktop/dialogs.py](../../src/studium/presentation/desktop/dialogs.py) — `HistoryDialog.add_attempt`
- [src/studium/presentation/desktop/files.py](../../src/studium/presentation/desktop/files.py) — `FilesWidget`
- [src/studium/application/services.py](../../src/studium/application/services.py) — `record_attempt`; `add_attempt`

**Существующие тесты основы (NOT RUN; новый полный сценарий ими не доказан):**

- [tests/integration/test_phase65_desktop.py](../../tests/integration/test_phase65_desktop.py) — `test_quick_cancel_does_not_create_work_or_attempt`; `test_quick_attempt_preserves_history_and_automatic_number`
- [tests/integration/test_file_desktop.py](../../tests/integration/test_file_desktop.py) — `test_attempt_picker_multi_import_and_separate_attempt_lists`

- **Модель:** Использовать StudentWork/Attempt occurred_at и FileAsset; submission identity явная, review event не новая сдача.
- **Сервисы:** Один orchestration use case capture submission + attachments с compensation file/DB, existing group work selection и atomic numbering.
- **UI:** + Зарегистрировать сдачу, student fixed, существующие ДЗ/РК, actual date/comment, pending removable previews DOC/DOCX/PDF/JPG/PNG/WebP.
- **Миграции:** Для base capture не нужна; lifecycle extension 028 и exact score contracts QA-A учитываются.
- **Зависимости:** 012/030; основа 028/017. Минимальный pending preview нужен здесь, полная унификация 021 позже.
- **Риски сохранности:** Не создавать Assessment неявно; cancel не создаёт Work/Attempt/FileAsset. Частичный import batch не должен оставить orphan attempt с половиной файлов.
- **Критерии приёмки:** Первая и повторная сдача, два файла, remove/cancel, source неизменен; после commit новая Attempt видна в карточке/журнале/queue, старые UUID/номера/файлы сохранены.

**Ручная приёмка:** NOT RUN. **Закрывающий implementation PR:** отсутствует в этом аудите.

<a id="st-qa-028"></a>

#### ST-QA-028 — Проверенный преподавателем файл

**P1 · Частично.** Immutable FileAsset и несколько AttemptAttachment реализованы; AttachmentService.open_file_asset открывает managed original. Role student/teacher, Review/Returned, checked_at/returned_at и история переходов отсутствуют; generic details_json не заменяет этот контракт.

**Production evidence:**

- [src/studium/domain/entities/__init__.py](../../src/studium/domain/entities/__init__.py) — `AttemptAttachment`
- [src/studium/application/file_services.py](../../src/studium/application/file_services.py) — `AttachmentService.open_file_asset`; `AttachmentService.import_file_for_attempt`
- [src/studium/infrastructure/file_storage.py](../../src/studium/infrastructure/file_storage.py) — `LocalFileStorage`
- [src/studium/presentation/desktop/files.py](../../src/studium/presentation/desktop/files.py) — `FilesWidget`

**Существующие тесты основы (NOT RUN; новый полный сценарий ими не доказан):**

- [tests/integration/test_files.py](../../tests/integration/test_files.py) — `test_attempt_versions_and_student_aggregation`; `test_shared_asset_detach_keeps_other_attempt_link`; `test_open_uses_only_controlled_path_and_no_source_filename`
- [tests/integration/test_iteration4_files_deletion.py](../../tests/integration/test_iteration4_files_deletion.py) — `test_managed_file_survives_source_removal_and_runtime_reopen`

- **Модель:** Immutable AttemptReview с outcome/comment/checked_at и отдельный ReturnEvent(returned_at); explicit teacher-file link к FileAsset, student originals прежние. История states derivable из событий.
- **Сервисы:** Check/return commands с revisions и concrete FK; external edit только рабочей копии + import новой версии, compensation и scoped grade association.
- **UI:** Оригиналы/проверенные файлы отдельно, несколько teacher files, result/comments/dates, действия Проверить/Отметить возврат; automatic send отсутствует.
- **Миграции:** Additive review/return/file-role links с guards. Legacy файлы не назначать автоматически teacher/student role по имени; old history read-only.
- **Зависимости:** 027/030, B5. Даёт основу 017 и 029; minimal pending picker QA-B.
- **Риски сохранности:** Открытие read-only original во внешнем редакторе не является разрешением переписать bytes. Не обходить immutable Attempt/Grade, не считать возврат сдачей.
- **Критерии приёмки:** DOCX original и две проверенные версии имеют разные immutable assets; source removed/reopen/backup сохраняет hashes; Checked≠Returned, repeated submission новая Attempt, без сетевой отправки.

**Ручная приёмка:** NOT RUN. **Закрывающий implementation PR:** отсутствует в этом аудите.

<a id="st-qa-029"></a>

#### ST-QA-029 — Summary на главном экране прогресса студента

**P1 · Частично.** StudentProgressWidget имеет категории ДЗ/РК/экзамен, generic Сводка/Highlights и фактические DTO, но initial tab ДЗ и highlights скрыты; нет первой отдельной category summary с requested counts/scores и переходами.

**Production evidence:**

- [src/studium/presentation/desktop/analytics.py](../../src/studium/presentation/desktop/analytics.py) — `StudentProgressWidget`; `SummaryHighlights`
- [src/studium/application/analytics.py](../../src/studium/application/analytics.py) — `AnalyticsService.student_progress`; `AnalyticsService.student_work_facts`
- [src/studium/application/analytics_models.py](../../src/studium/application/analytics_models.py) — `StudentProgressSummary`; `AttendanceSummary`

**Существующие тесты основы (NOT RUN; новый полный сценарий ими не доказан):**

- [tests/integration/test_iteration4_workflows.py](../../tests/integration/test_iteration4_workflows.py) — `test_student_categories_three_attempts_files_and_progress_are_readonly`
- [tests/integration/test_analytics.py](../../tests/integration/test_analytics.py) — `test_student_zero_completion_and_missing_values_are_distinct`; `test_attendance_denominator_unknown_excused_and_unmarked`

- **Модель:** Read-only typed counts by category и exact historical scores; без новых aggregates/mastery.
- **Сервисы:** Один согласованный bulk snapshot и documented denominators; ожидают проверки из explicit lifecycle, not-sent overdue отдельно.
- **UI:** Initial Summary ДЗ/РК/attendance; навигация к категориям/экзаменам/evidence/charts; числовые результаты без рейтинга.
- **Миграции:** Для summary не нужна, читает lifecycle/score schema.
- **Зависимости:** 012/017/028/030; определить B8 denominators для выполнено/зачтено.
- **Риски сохранности:** Нельзя складывать reviewed события с submissions как число попыток и принимать None за 0. Cancelled lessons/excused/unmarked должны следовать existing analytics contract.
- **Критерии приёмки:** Первый экран содержит все requested counts и РК scores; сумма определяется документированным scope; клики ведут к фактам; чтение не делает INSERT/UPDATE.

**Ручная приёмка:** NOT RUN. **Закрывающий implementation PR:** отсутствует в этом аудите.

### QA-C

<a id="st-qa-014"></a>

#### ST-QA-014 — Генерация вариантов внутри конкретной работы

**P2 · Частично.** Generator/review/save/assign и snapshots есть; GroupsPage всё ещё содержит вкладку Варианты. AssessmentContentDialog.open_variants возвращается к ней; UI генерации не жёстко связан с текущей работой.

**Production evidence:**

- [src/studium/presentation/desktop/pages.py](../../src/studium/presentation/desktop/pages.py) — `GroupsPage.__init__`
- [src/studium/presentation/desktop/learning.py](../../src/studium/presentation/desktop/learning.py) — `AssessmentContentDialog.open_variants`
- [src/studium/presentation/desktop/tickets.py](../../src/studium/presentation/desktop/tickets.py) — `TicketGeneratorPage`
- [src/studium/application/content_services.py](../../src/studium/application/content_services.py) — `ContentService`
- [src/studium/application/program_services.py](../../src/studium/application/program_services.py) — `apply_ticket_set_for_evaluation`

**Существующие тесты основы (NOT RUN; новый полный сценарий ими не доказан):**

- [tests/integration/test_content_workflow.py](../../tests/integration/test_content_workflow.py) — `test_twenty_variants_assign_replace_snapshot_and_no_answer_leak`; `test_unsaved_problem_change_rejected_atomically`
- [tests/integration/test_workflow_desktop.py](../../tests/integration/test_workflow_desktop.py) — `test_generator_ui_save_select_set_unassign_restore`

- **Модель:** Переиспользовать TicketSet.assessment_id и snapshots; explicit assignment history при замене, без второго генератора.
- **Сервисы:** Enforce current offering+assessment при генерации/assign/replace; preview confirmation и lock после Attempts.
- **UI:** Работа→Задачи и варианты, просмотр варианта студента; банк остаётся общим; убрать standalone group tab после переноса всех входов.
- **Миграции:** Только если current revisioned TicketAssignment не сохраняет каждое прежнее назначение: additive assignment events. Старые наборы не удалять.
- **Зависимости:** 009/012/030; bank 022/023 учитываются в snapshots позже.
- **Риски сохранности:** Revision сама не журнал истории: замена assignment может потерять прежний контекст. Не переустанавливать assessment items после первого Attempt.
- **Критерии приёмки:** Один generator для ДЗ/РК, cancel replacement ничего не меняет, old set/assignment доступен; teacher answers не входят в student view.

**Ручная приёмка:** NOT RUN. **Закрывающий implementation PR:** отсутствует в этом аудите.

<a id="st-qa-021"></a>

#### ST-QA-021 — Миниатюры файлов до сохранения записи

**P2 · Частично.** FileDropZone поддерживает multi-file/drop; MaterialFiles.pending для нового owner хранит только paths/count. Preview и detach доступны для сохранённых assets, pending миниатюр/remove нет. Для existing owner импорт происходит немедленно.

**Production evidence:**

- [src/studium/presentation/desktop/workflow_widgets.py](../../src/studium/presentation/desktop/workflow_widgets.py) — `FileDropZone`
- [src/studium/presentation/desktop/library.py](../../src/studium/presentation/desktop/library.py) — `MaterialFiles.import_paths`; `MaterialFiles.import_pending`
- [src/studium/presentation/desktop/files.py](../../src/studium/presentation/desktop/files.py) — `FilePreviewDialog`
- [src/studium/infrastructure/file_preview.py](../../src/studium/infrastructure/file_preview.py) — `QtThumbnailCache`

**Существующие тесты основы (NOT RUN; новый полный сценарий ими не доказан):**

- [tests/integration/test_workflow_desktop.py](../../tests/integration/test_workflow_desktop.py) — `test_reusable_drop_multifile_import_from_library`; `test_drop_zone_rejects_url_directory_and_disabled`
- [tests/integration/test_file_desktop.py](../../tests/integration/test_file_desktop.py) — `test_pdf_builtin_preview_and_unknown_metadata`; `test_invalid_image_error_is_friendly_and_does_not_crash`

- **Модель:** Ephemeral PendingFile DTO, без окончательного FileAsset до save.
- **Сервисы:** Safe bounded local-path preview и import orchestration через прежние ports; source-change check и compensation.
- **UI:** Единый pending attachment picker: thumbnail image/PDF first page, DOC icons, name/size, remove/preview/multiple/drop; lazy background decoding.
- **Миграции:** Не нужна; cache/temp preview вне source tree.
- **Зависимости:** Minimal version нужен для 027/028 в QA-B; окончательная унификация всех форм QA-C.
- **Риски сохранности:** Не использовать managed-asset-only preview с фиктивными assets; не запускать macros, не менять пользовательский source, worker result после cancel игнорируется.
- **Критерии приёмки:** Cancel/remove до save оставляют ноль assets/links/bytes; long names, malformed image/PDF, DOC/DOCX icons, hundred files lazy без freeze и source unchanged.

**Ручная приёмка:** NOT RUN. **Закрывающий implementation PR:** отсутствует в этом аудите.

<a id="st-qa-022"></a>

#### ST-QA-022 — Структурированные правильные ответы

**P2 · Отсутствует.** Problem.correct_answer — свободный текст, варианты имеют своё поле; структурированных quantities/templates нет, snapshots копируют только текст.

**Production evidence:**

- [src/studium/domain/content.py](../../src/studium/domain/content.py) — `Problem`
- [src/studium/presentation/desktop/library.py](../../src/studium/presentation/desktop/library.py) — `ContentEditor.text_tab`; `ContentEditor.values`
- [src/studium/application/content_services.py](../../src/studium/application/content_services.py) — `ContentService`

**Существующие тесты основы (NOT RUN; новый полный сценарий ими не доказан):**

- [tests/integration/test_problem_variants.py](../../tests/integration/test_problem_variants.py) — `test_family_taxonomy_and_scheme_snapshots_survive_edits`
- [tests/integration/test_content_workflow.py](../../tests/integration/test_content_workflow.py) — `test_twenty_variants_assign_replace_snapshot_and_no_answer_leak`

- **Модель:** ProblemAnswerParameter(name,symbol,value numeric/symbolic,unit,formula/explanation,order) + optional template contract; вариант имеет собственные ответы; legacy free text сохраняется.
- **Сервисы:** CRUD/reorder/version and answer snapshots при выдаче; Decimal numeric values без автоматической проверки/solver.
- **UI:** Произвольные строки параметров, шаблоны, variant-specific values и текстовый комментарий.
- **Миграции:** Additive answer/template links и teacher snapshot representation; свободный текст не парсить автоматически.
- **Зависимости:** 014 snapshots; B9 template ownership и numeric/symbolic semantics. Никаких runtime Bender imports.
- **Риски сохранности:** Teacher answers не должны утечь в student export; изменение банка не меняет старый assigned snapshot.
- **Критерии приёмки:** Несколько величин/units/formulas, symbolic и exact numeric, свой ответ варианта, reorder; старый текст доступен; student view не содержит ответ.

**Ручная приёмка:** NOT RUN. **Закрывающий implementation PR:** отсутствует в этом аудите.

<a id="st-qa-023"></a>

#### ST-QA-023 — Настоящая иерархия тем и подтем

**P2 · Частично.** Topic.parent_topic_id, cycle guards, hierarchy и distinct rollup существуют; в редакторе задачи taxonomy — плоский CheckList и поиск по title без ancestor context.

**Production evidence:**

- [src/studium/presentation/desktop/library.py](../../src/studium/presentation/desktop/library.py) — `ContentEditor.refresh_taxonomy`; `ContentEditor.search_taxonomy`
- [src/studium/presentation/desktop/learning.py](../../src/studium/presentation/desktop/learning.py) — `LearningCatalogueDialog.refresh`
- [src/studium/application/learning_services.py](../../src/studium/application/learning_services.py) — `LearningService.topic_hierarchy`
- [src/studium/application/analytics.py](../../src/studium/application/analytics.py) — `AnalyticsService`

**Существующие тесты основы (NOT RUN; новый полный сценарий ими не доказан):**

- [tests/integration/test_iteration4_workflows.py](../../tests/integration/test_iteration4_workflows.py) — `test_topic_hierarchy_module_subtopic_and_skill`
- [tests/integration/test_analytics.py](../../tests/integration/test_analytics.py) — `test_hierarchy_distinct_questions_lessons_attendance_and_results`; `test_course_evidence_scope_student_filter_and_no_topic_skill_inference`

- **Модель:** Существующие Topic/ProblemTopic достаточны, selected IDs точные.
- **Сервисы:** Hierarchy query + search с ancestor context, без implicit expansion выбранного parent в детей.
- **UI:** Tree multiselect, depth/expand/collapse, parent и конкретные subtopics, selection сохраняется при search.
- **Миграции:** Не нужна.
- **Зависимости:** Canonical taxonomy существующая; согласуется с 020, не ждёт его для QA-C.
- **Риски сохранности:** Parent rollup допустим только как distinct aggregate explicit facts; выбор parent не создаёт child links. Frozen semantic taxonomy нельзя переименовать обходом guards.
- **Критерии приёмки:** Три уровня, parent-only/child-only/mixed search возвращают ровно selected links; parent-only задача не проверяет все детей.

**Ручная приёмка:** NOT RUN. **Закрывающий implementation PR:** отсутствует в этом аудите.

### QA-D

<a id="st-qa-001"></a>

#### ST-QA-001 — Единый выбор дат через календарь

**P2 · Реализовано.** Все обнаруженные QDateEdit/QDateTimeEdit подключают direct_calendar/StudyCalendar: FormDialog, ProgramWorkForm и AnalyticsComparison. Ручной dd.MM.yyyy ввод и domain date/range validation есть. Полный native click/input acceptance не проведён.

**Production evidence:**

- [src/studium/presentation/desktop/dialogs.py](../../src/studium/presentation/desktop/dialogs.py) — `FormDialog.day`; `FormDialog.timestamp`
- [src/studium/presentation/desktop/workflow_widgets.py](../../src/studium/presentation/desktop/workflow_widgets.py) — `direct_calendar`
- [src/studium/presentation/desktop/programs.py](../../src/studium/presentation/desktop/programs.py) — `ProgramWorkForm.week_date`
- [src/studium/presentation/desktop/analytics.py](../../src/studium/presentation/desktop/analytics.py) — `AnalyticsComparison`
- [src/studium/domain/value_objects/__init__.py](../../src/studium/domain/value_objects/__init__.py) — `LocalDate`

**Существующие тесты основы (NOT RUN; новый полный сценарий ими не доказан):**

- [tests/integration/test_workflow_desktop.py](../../tests/integration/test_workflow_desktop.py) — `test_datepicker_one_selection_updates_value_and_signal`
- [tests/integration/test_visual_desktop.py](../../tests/integration/test_visual_desktop.py) — `test_calendar_keyboard_survives_theme_change`
- [tests/unit/test_domain.py](../../tests/unit/test_domain.py) — `test_calendar_date_is_not_instant`; `test_term_interval_and_name`

- **Модель:** Изменений модели не требуется.
- **Сервисы:** Прежняя validation остаётся.
- **UI:** Проверить все актуальные формы; новые QA-A поля сразу подключать к общему компоненту, исправлять только воспроизведённые пробелы.
- **Миграции:** Не нужна.
- **Зависимости:** Совместная приёмка 004/005 и новых дат QA-A.
- **Риски сохранности:** Qt может корректировать недопустимый ввод; native приёмка должна подтвердить понятную ошибку, отсутствие silent wrong date и timezone conversion только для instants.
- **Критерии приёмки:** Календарь по нажатию и ручной ввод во всех date fields; невозможные даты/обратные диапазоны не сохраняются, keyboard/calendar signal корректны.

**Ручная приёмка:** NOT RUN. **Закрывающий implementation PR:** отсутствует в этом аудите.

<a id="st-qa-004"></a>

#### ST-QA-004 — Исправить оформление календарей

**P3 · Частично.** StudyCalendar уже имеет безсеточный вид, navigation icons, theme/current-day painting и QSS. Причина всех reported рамок/clipping на текущем Windows не воспроизведена; явной screen-edge popup policy нет.

**Production evidence:**

- [src/studium/presentation/desktop/calendar.py](../../src/studium/presentation/desktop/calendar.py) — `StudyCalendar`
- [src/studium/presentation/desktop/theme.py](../../src/studium/presentation/desktop/theme.py) — `theme_stylesheet`

**Существующие тесты основы (NOT RUN; новый полный сценарий ими не доказан):**

- [tests/integration/test_visual_desktop.py](../../tests/integration/test_visual_desktop.py) — `test_calendar_keyboard_survives_theme_change`

- **Модель:** Не требуется.
- **Сервисы:** Не требуется.
- **UI:** Диагностика popup/frame по Qt owner, central radius/spacing/shadow при поддержке, clamp popup к available geometry.
- **Миграции:** Не нужна.
- **Зависимости:** 001/005.
- **Риски сохранности:** Стили не должны ломать month/year input, keyboard и screen scaling.
- **Критерии приёмки:** Light/Dark, popup у каждого края экрана при 100/125/150% DPI без clipping/двойной рамки; даты и keyboard работают.

**Ручная приёмка:** NOT RUN. **Закрывающий implementation PR:** отсутствует в этом аудите.

<a id="st-qa-005"></a>

#### ST-QA-005 — Единая дизайн-система компонентов

**P2 · Частично.** Есть design.py tokens, Light/Dark, central QSS и AcademicStyle painted arrows. Это база; все requested компоненты/состояния на трёх DPI текущим аудитом не приняты.

**Production evidence:**

- [src/studium/presentation/desktop/design.py](../../src/studium/presentation/desktop/design.py) — `Colors`; `SPACES`; `RADII`; `TYPE`
- [src/studium/presentation/desktop/theme.py](../../src/studium/presentation/desktop/theme.py) — `AcademicStyle.drawPrimitive`; `theme_stylesheet`; `apply_theme`
- [src/studium/presentation/desktop/icons.py](../../src/studium/presentation/desktop/icons.py) — `icon`

**Существующие тесты основы (NOT RUN; новый полный сценарий ими не доказан):**

- [tests/integration/test_visual_desktop.py](../../tests/integration/test_visual_desktop.py) — `test_text_and_primary_action_contrast`; `test_original_icons_have_transparency_and_disabled_state`
- [tests/integration/test_workflow_desktop.py](../../tests/integration/test_workflow_desktop.py) — `test_combo_popup_readable_palette`

- **Модель:** Не требуется.
- **Сервисы:** Только existing preferences theme persistence.
- **UI:** Довести общие tokens/styles для requested Qt widgets и hover/focus/disabled/selected; устранять root cause, не стили каждого окна.
- **Миграции:** Не нужна.
- **Зависимости:** Общая основа 004/007/015/018/026; поздняя QA-D не блокирует business QA-B.
- **Риски сохранности:** QProxyStyle/QSS subcontrols могут менять размеры и focus; не терять клавиатуру/contrast и DPI sizing.
- **Критерии приёмки:** Компонентная visual matrix в Light/Dark на 100/125/150%, keyboard, menus/spinbox arrows; screenshots только synthetic и exact build.

**Ручная приёмка:** NOT RUN. **Закрывающий implementation PR:** отсутствует в этом аудите.

<a id="st-qa-007"></a>

#### ST-QA-007 — Кнопка «Добавить студента»

**P3 · Частично.** QToolButton InstantPopup имеет два полезных действия: новый и существующий студент. Native menu indicator остаётся; отдельная приемлемая геометрия стрелки не подтверждена.

**Production evidence:**

- [src/studium/presentation/desktop/pages.py](../../src/studium/presentation/desktop/pages.py) — `GroupsPage.__init__`; `create_student`; `add_existing`

**Существующие тесты основы (NOT RUN; новый полный сценарий ими не доказан):**

- [tests/integration/test_phase65_desktop.py](../../tests/integration/test_phase65_desktop.py) — `test_group_workspace_context_survives_navigation_and_refresh`

- **Модель:** Не требуется.
- **Сервисы:** Прежние create/enroll commands.
- **UI:** Явная menu button/chevron по общему стилю; keyboard accessibility и оба пути добавления.
- **Миграции:** Не нужна.
- **Зависимости:** 005.
- **Риски сохранности:** Не удалять InstantPopup вместе с действием add_existing и не создавать повторный Enrollment.
- **Критерии приёмки:** Нет маленького артефакта справа снизу; оба действия доступны мышью/клавиатурой, stale/duplicate enrollment обрабатывается.

**Ручная приёмка:** NOT RUN. **Закрывающий implementation PR:** отсутствует в этом аудите.

<a id="st-qa-016"></a>

#### ST-QA-016 — Изменяемая высота области аналитики

**P2 · Отсутствует.** GroupAnalyticsWidget/StudentProgressWidget и AnalyticsComparison используют QVBoxLayout/tabs. Splitter показателей и таблицы, expanded table и сохранение высоты отсутствуют; splitters других карточек не выполняют это требование.

**Production evidence:**

- [src/studium/presentation/desktop/analytics.py](../../src/studium/presentation/desktop/analytics.py) — `GroupAnalyticsWidget`; `StudentProgressWidget`; `AnalyticsComparison`
- [src/studium/infrastructure/user_data.py](../../src/studium/infrastructure/user_data.py) — `JsonPreferences`

**Существующие тесты основы (NOT RUN; новый полный сценарий ими не доказан):**

- [tests/integration/test_analytics_desktop.py](../../tests/integration/test_analytics_desktop.py) — `test_student_progress_tab_readonly_metrics_and_evidence`

- **Модель:** Только preference splitter sizes, без учебной модели.
- **Сервисы:** Расширить preferences port с сохранением неизвестных ключей, clamp на восстановлении.
- **UI:** Vertical QSplitter summary/table, expanded view и минимум controls; сохранение после resize/restart.
- **Миграции:** Не нужна.
- **Зависимости:** 029 composition; 005 стиль handle.
- **Риски сохранности:** Старые размеры другого DPI/монитора могут спрятать controls: clamp available geometry, fallback.
- **Критерии приёмки:** Drag границы, расширить/вернуть таблицу, restart, 960×620/HD/three DPI; controls остаются доступны и чтение данных не пишет факты.

**Ручная приёмка:** NOT RUN. **Закрывающий implementation PR:** отсутствует в этом аудите.

<a id="st-qa-018"></a>

#### ST-QA-018 — Полностью кликабельные карточки

**P2 · Частично.** HomeTile уже whole QPushButton с mouse-transparent labels; пять карточек DisciplinePage используют action_card: QFrame + кликабельная только стрелка.

**Production evidence:**

- [src/studium/presentation/desktop/visuals.py](../../src/studium/presentation/desktop/visuals.py) — `HomeTile`; `action_card`
- [src/studium/presentation/desktop/programs.py](../../src/studium/presentation/desktop/programs.py) — `DisciplinePage`; `WorkProgramPage`

**Существующие тесты основы (NOT RUN; новый полный сценарий ими не доказан):**

- [tests/integration/test_iteration3_desktop.py](../../tests/integration/test_iteration3_desktop.py) — `test_home_single_card_and_recent_row_open`
- [tests/integration/test_visual_desktop.py](../../tests/integration/test_visual_desktop.py) — `test_home_tiles_have_room_and_keyboard_navigation`

- **Модель:** Не требуется.
- **Сервисы:** Прежние routes.
- **UI:** Общий whole-card button с transparent child labels, hover/focus и одной активацией Enter/Space; применить всем action_card.
- **Миграции:** Не нужна.
- **Зависимости:** 005.
- **Риски сохранности:** Event filter не должен вызывать двойной transition; не поглощать input интерактивных descendants.
- **Критерии приёмки:** Клик title/body/padding/arrow каждой из пяти cards открывает один нужный tab; Tab/Enter/Space и hover работают.

**Ручная приёмка:** NOT RUN. **Закрывающий implementation PR:** отсутствует в этом аудите.

<a id="st-qa-019"></a>

#### ST-QA-019 — Убрать непонятную дублирующую кнопку «Навыки»

**P3 · Частично.** Кнопка Навыки не дубль вкладки: topic_skills открывает TopicSkillsDialog и редактирует TopicSkill. Название/местоположение всё ещё вводят в заблуждение.

**Production evidence:**

- [src/studium/presentation/desktop/learning.py](../../src/studium/presentation/desktop/learning.py) — `LearningCatalogueDialog.topic_skills`; `TopicSkillsDialog`
- [src/studium/domain/entities/__init__.py](../../src/studium/domain/entities/__init__.py) — `TopicSkill`

**Существующие тесты основы (NOT RUN; новый полный сценарий ими не доказан):**

- [tests/integration/test_learning_desktop.py](../../tests/integration/test_learning_desktop.py) — `test_learning_catalogue_forms_tree_and_skills`
- [tests/integration/test_iteration4_workflows.py](../../tests/integration/test_iteration4_workflows.py) — `test_topic_hierarchy_module_subtopic_and_skill`

- **Модель:** TopicSkill сохраняется.
- **Сервисы:** Прежний links service/revision checks.
- **UI:** Перенести в карточку темы как Связанные навыки; убрать двусмысленную toolbar кнопку.
- **Миграции:** Не нужна.
- **Зависимости:** 020 context route, 005.
- **Риски сохранности:** Не удалять links как будто кнопка дублирует справочник; оба сценария нужны.
- **Критерии приёмки:** Создание Skill через вкладку и редактирование TopicSkill через тему различимы; прежние связи/UUID/revisions сохранены.

**Ручная приёмка:** NOT RUN. **Закрывающий implementation PR:** отсутствует в этом аудите.

<a id="st-qa-020"></a>

#### ST-QA-020 — Контекстное меню дерева тем

**P2 · Частично.** В LearningCatalogueDialog есть itemDoubleClicked→edit_topic и toolbar Add subtopic/edit/archive; CustomContextMenu для дерева и empty-space action отсутствуют.

**Production evidence:**

- [src/studium/presentation/desktop/learning.py](../../src/studium/presentation/desktop/learning.py) — `LearningCatalogueDialog.__init__`; `edit_topic`; `archive_topic`

**Существующие тесты основы (NOT RUN; новый полный сценарий ими не доказан):**

- [tests/integration/test_learning_desktop.py](../../tests/integration/test_learning_desktop.py) — `test_learning_catalogue_forms_tree_and_skills`
- [tests/integration/test_iteration4_workflows.py](../../tests/integration/test_iteration4_workflows.py) — `test_topic_hierarchy_module_subtopic_and_skill`

- **Модель:** Не требуется, parent_topic_id/cycle guards прежние.
- **Сервисы:** Прежние edit/archive commands с semantic lock и consequences.
- **UI:** Right click single context menu target item, пустое место→root create, Menu/Shift+F10, left double click edit, right double click не edit.
- **Миграции:** Не нужна.
- **Зависимости:** 019; совместная приёмка taxonomy 023.
- **Риски сохранности:** Меню должно выбрать узел под курсором, не прежний selected; module/Skill декоративные nodes не Topic. Удаление = безопасный archive, история прежняя.
- **Критерии приёмки:** Все mouse/keyboard маршруты на Topic/module/Skill/empty, nested parent верен, archive подтверждён; right double click не открывает editor.

**Ручная приёмка:** NOT RUN. **Закрывающий implementation PR:** отсутствует в этом аудите.

<a id="st-qa-024"></a>

#### ST-QA-024 — Убрать пустые пространства и лишнюю прокрутку

**P2 · Частично.** ContentEditor использует scrollable shell/Disclosure, однако tabs minimumHeight=380, CheckList minimumHeight=100 и FileDropZone minimumHeight=136 могут заставлять пустую Коллекции прокручиваться. Native причина/extent требуют измерения.

**Production evidence:**

- [src/studium/presentation/desktop/library.py](../../src/studium/presentation/desktop/library.py) — `ContentEditor.__init__`; `ContentEditor.text_tab`
- [src/studium/presentation/desktop/learning.py](../../src/studium/presentation/desktop/learning.py) — `CheckList`
- [src/studium/presentation/desktop/workflow_widgets.py](../../src/studium/presentation/desktop/workflow_widgets.py) — `FileDropZone`

**Существующие тесты основы (NOT RUN; новый полный сценарий ими не доказан):**

- [tests/integration/test_iteration3_desktop.py](../../tests/integration/test_iteration3_desktop.py) — `test_material_advanced_scroll_and_save_at_small_window`; `test_order_is_internal_and_forms_remain_scrollable`

- **Модель:** Не требуется.
- **Сервисы:** Не требуется.
- **UI:** Измерить sizeHint/stretch/scroll nesting, убрать artificial minimums где необходимо; compact empty states и видимые save/cancel.
- **Миграции:** Не нужна.
- **Зависимости:** 021 влияет на вкладки файлов; 005 общие spacing.
- **Риски сохранности:** Простое снятие минимумов может спрятать editor/control на большом содержимом; проверить малый и большой объём.
- **Критерии приёмки:** Коллекции 0/1/100 и другие editor tabs, 960×620/HD/three DPI: scroll только при необходимости, нижние кнопки доступны.

**Ручная приёмка:** NOT RUN. **Закрывающий implementation PR:** отсутствует в этом аудите.

<a id="st-qa-025"></a>

#### ST-QA-025 — Перестроить компоновку «Базы знаний»

**P2 · Реализовано.** KnowledgeWidget уже строит heading→description→search→split/list, EmptyState; refresh переключает split и empty. Нет лишнего fixed-height в этой композиции. Визуальная Windows-приёмка не проведена.

**Production evidence:**

- [src/studium/presentation/desktop/programs.py](../../src/studium/presentation/desktop/programs.py) — `KnowledgeWidget.__init__`; `KnowledgeWidget.refresh`
- [src/studium/application/program_services.py](../../src/studium/application/program_services.py) — `list_knowledge_entries`; `knowledge_occurrences`

**Существующие тесты основы (NOT RUN; новый полный сценарий ими не доказан):**

- [tests/integration/test_program_regressions.py](../../tests/integration/test_program_regressions.py) — `test_knowledge_manual_generalization_many_sources_and_scope`

- **Модель:** Не требуется.
- **Сервисы:** Business KnowledgeEntry/source links не менять.
- **UI:** Зафиксировать существующую последовательность и переключение empty/list регрессией; корректировать spacing только по воспроизведению.
- **Миграции:** Не нужна.
- **Зависимости:** 005/024 visual acceptance.
- **Риски сохранности:** Не переписывать QuestionCase/Message или source links ради layout; пустой search result не означает удалить записи.
- **Критерии приёмки:** 0/1/many и no-match search дают нужный list/empty без пустых промежутков, keyboard/search/selection доступны; domain writes отсутствуют.

**Ручная приёмка:** NOT RUN. **Закрывающий implementation PR:** отсутствует в этом аудите.

<a id="st-qa-026"></a>

#### ST-QA-026 — Визуальные артефакты тёмной темы

**P2 · Частично.** Central Light/Dark и Sidebar работают; QSS navigation items имеют margin/radius и branch:selected rules. Это возможная область диагностики, не доказанная причина reported засечек; полный pixel/DPI audit отсутствует.

**Production evidence:**

- [src/studium/presentation/desktop/navigation.py](../../src/studium/presentation/desktop/navigation.py) — `Sidebar`
- [src/studium/presentation/desktop/theme.py](../../src/studium/presentation/desktop/theme.py) — `theme_stylesheet`; `apply_theme`

**Существующие тесты основы (NOT RUN; новый полный сценарий ими не доказан):**

- [tests/integration/test_iteration3_desktop.py](../../tests/integration/test_iteration3_desktop.py) — `test_sidebar_one_level_shortcuts_and_persistence`; `test_frozen_journal_pixel_alignment_after_scroll`
- [tests/integration/test_visual_desktop.py](../../tests/integration/test_visual_desktop.py) — `test_text_and_primary_action_contrast`

- **Модель:** Не требуется.
- **Сервисы:** Прежние navigation/preferences.
- **UI:** Воспроизвести hover с branch/item geometry и style ownership, исправить central root cause, затем полный visual pass.
- **Миграции:** Не нужна.
- **Зависимости:** 005 и завершённые остальные UI сценарии QA-D.
- **Риски сохранности:** Screenshot одного Linux масштаба не подтверждает native Windows defect fix; не вводить local padding workaround без причины.
- **Критерии приёмки:** Sidebar hover/selected/expanded и все типовые screens Light/Dark на 100/125/150%, menus/dialog edges, no overlap/extra scrollbars; synthetic exact-build evidence.

**Ручная приёмка:** NOT RUN. **Закрывающий implementation PR:** отсутствует в этом аудите.

<a id="blocking-contracts"></a>

## Блокирующие контракты

Это вопросы перед зависимыми implementation PR, не blockers документационного PR.
Смысл min закрыт; повторное решение о пороге зачёта не требуется.

| ID | Конкретный вопрос | Рекомендуемый вариант | Что блокирует |
|---|---|---|---|
| B1 | Можно ли редактировать содержание версии программы, когда она уже используется несколькими планами, и как нумеровать семестры курса? | После назначения freeze content version, новое содержание — новая explicit version; курс имеет ordinal semester placement, календарь только у offering. Legacy программы автоматически не сливать. | 003, QA-A-PR-03/04/05 |
| B2 | Можно ли перенести срок отдельного ДЗ/РК за границу своего модуля, сохранив связь с модулем? | Предупреждение и явное подтверждение или явный выбор другого модуля; никогда автоматический перенос соседей. Текущий SQL требует due week внутри module. | 011, QA-A-PR-07 |
| B3 | В QA-A сроки — date-only конец учебного дня или date+time; какой calendar offset и что считать actual issuance для legacy? | Сохранить exact due precedence; date-only новый срок = конец дня в explicit fixed offset плана; legacy issued_at сохраняется с unknown provenance, actual подтверждается преподавателем. | 013/011, QA-A-PR-04/08; остаток OPEN-009 |
| B4 | Какая допустимая decimal precision/scale и верхний диапазон числового результата? | Decimal + scaled INTEGER при согласованной scale/range; legacy REAL не округлять и не объявлять восстановленной точностью. Нет общего max всех работ. | 030, QA-A-PR-09 |
| B5 | Как прикрепить проверку/Grade к уже сохранённой immutable PRESENTED Attempt, не создавая новую сдачу и attempt_no? | Отдельный immutable review связанный с submission; сохранить legacy Attempt projection через явный compatibility resolver, review не увеличивает submission count. Таблицу переходов/Grade binding согласовать до реализации. | 030 acceptance, QA-A-PR-01/09; затем 027/028/017 |
| B6 | Новые границы применяются к следующей проверке либо сохраняется rule выдачи для всех пересдач этой работы? | Каждая новая проверка фиксирует явно выбранную current rule; прошлый result/rule snapshot неизменен. Для pending сдачи правило видно до save. | 030, QA-A-PR-09/10 |
| B7 | Что означает 7 календарных дней: та же локальная часы/минута на 7-й день или конец 7-го дня; когда предупреждать near-due? | Explicit calendar offset, SLA default 7, near-due window configurable. Зафиксировать boundary/equal timestamp examples. | QA-B 017, остаток OPEN-009 |
| B8 | В summary РК что различает выполнено и зачтено и как считать ещё не выданные/отменённые работы? | выполнено = есть содержательная сдача, зачтено = explicit accepted; scope план/выдача показать отдельно, отмены исключать из active denominator; сохранять текущие attendance denominators. | QA-B 029, локальный остаток OPEN-002 |
| B9 | Шаблон structured answer копируется в задачу или остаётся live link; какие value types и обязательные units? | Snapshot schema в задаче/варианте, numeric/symbolic typed, unit optional; не выполнять формулы. | QA-C 022 |

OPEN-002/009/011 не закрываются целиком: предлагаются только локальные review,
schedule-history и date contracts. Sync/ownership, purge/retention, общий audit
и integration остаются прежними отдельными задачами. Native/manual acceptance
действующих reporting/backup/installer также не объявляется завершённой.

<a id="qa-a-pr-plan"></a>

## Последовательные небольшие PR QA-A

Все перечисленные PR будущие, не созданы и не разрешены этим аудитом.
Последовательность **01 → 02 → 03 → 04 → 05 → 06 → 07 → 08 → 09 → 10**.
Каждый следующий начинается от актуального main после review и отдельного merge
предыдущего; текущий documentation PR не считается первым implementation PR.
Приоритеты и требования остаются исходными, 030=P1 не превращается в P2.

| PR | Требования и точный scope | Зависит / prerequisite | Проверка и критерий выхода |
|---|---|---|---|
| QA-A-PR-01 — Контракты и migration mapping | Только технические ADR/model docs: content version vs plan, legacy mapping, B1–B6, Decimal/rule/Grade truth table, date examples, deletion/backup compatibility; scope следующих PR. Код ещё не меняется. | Этот аудит; ответы B1–B6 до зависимых решений. | Review примеров current/legacy; min закрыт, нет молчаливых изменений ADR-009/010/030/037. Все schema decisions конкретны; нерешённый вопрос блокирует зависимый PR. |
| QA-A-PR-02 — Направления | 002: Direction/ProgramDirection, ports/repositories, additive revision и explicit code import; legacy raw direction сохранён. Пока без новой большой формы. | 01; code normalization/uniqueness contract. | Multi-code/duplicates/unknown text; populated v9→new, UUID/FK/history/reopen/rollback и existing frozen migration hashes. |
| QA-A-PR-03 — Содержание программы и версии | 003: independent content/version, version-module/definition links, explicit legacy map и compatibility read facade. Не объединять одноимённые legacy records. | 02; B1, mapping из 01. | Два content versions без обязательного term; сохранены old programs/modules/topics/definitions IDs и source snapshots, no automatic clones. |
| QA-A-PR-04 — Отдельный календарь реализации | 003/010 foundation: SemesterPlan/PlanModule/PlannedAssessment на offering, deterministic backfill каждой группы, calendar/analytics readers через план. До UI сохраняется совместимый legacy route. | 03; B3 и calendar-lock decision. | Две группы/два периода с общей версией и разными calendars; старые dates/weeks/offset/lessons/assessments unchanged; fresh/populated/reopen и query budgets. |
| QA-A-PR-05 — Формы программы и display name | Закрытие пользовательских 002/003/006: multi-code selection, content version и переиспользование между периодами; единый display name во всех tables/selectors, full tooltip. | 04. | Одноимённые программы различимы, source title сохранён; существующая программа назначается новому семестру без копий; keyboard/long names; Help programs обновлён. |
| QA-A-PR-06 — План семестра группы | 010: отдельный editor, draft/setup-later, 17/18 weeks, произвольные модули/работы, idempotent save/reopen, protected removal с history; журнал читает план. | 05. | No fake attempts/grades; cancel/reopen без новых records; existing work facts не теряются; group→plan→journal synthetic UI. |
| QA-A-PR-07 — История и подтверждённые переносы | 011: original/current snapshot, immutable changes/reason, impact preview и confirmed atomic batch, самостоятельные deadlines, sync current schedule к выданной работе через adapter. | 06; B2/B3. | 6→7 с конфликтом: preview/cancel no writes, apply final 17-week bounds; stale revision/late error full rollback; Attempt/Grade timestamps/values unchanged. |
| QA-A-PR-08 — Плановая/фактическая выдача | 013: issuance event/provenance, Planned/Issued, original/current due display, early issue, Journal homework current-due week; stable IDs при переносе, без полной переработки занятий 012. | 07; B3. | Issue before module start, deadline 6→7 without changing actual issue; legacy ambiguous issuance explicitly unknown; one idempotent issuance; Help homework/journal обновлён. |
| QA-A-PR-09 — Индивидуальные точные баллы | 030 domain/persistence/application: exact ScoreValue, versioned min/max и result/rule snapshot, legacy compatibility, validation и Grade truth table. Текущий legacy semantic lock сохраняется. | 08; B4/B5/B6 окончательно решены. | Inclusive 18–30, precise roundtrip, pending/revision null, real 0 only in allowed interval; numeric/pass-fail/traditional contracts; new rule не меняет старое 24/30. |
| QA-A-PR-10 — Ввод/отображение и сквозная приёмка QA-A | 030 UI/DTO: min/max in plan, exact score entry, historical score/max во всех journal/student/history/analytics/reporting views; исправления только по QA-A regression, Help и management statuses. | 09. | Full QA-A synthetic workflow, populated→new/reopen/backup/restore сравнение всех facts/bytes, multi-group performance, Light/Dark/DPI and native Windows acceptance. Ни одного нового QA-B/C/D business workflow. |

### Проверки каждого будущего implementation PR

- Relevant pytest и полный regression; Ruff check/format, pip check, repository
  safety worktree/index/history/identity и git diff --check. Historical migration
  hashes, layer boundaries, нет Bender diff/dependency/import.
- Для schema PR: populated synthetic предыдущая head → новая, fresh install,
  повторный upgrade/reopen, все прежние row values/UUID/revisions и SQL objects,
  FK/integrity, rollback позднего сбоя, archived facts и immutable file hashes.
- Backup/restore на каждом новом schema head: новые таблицы/FK/snapshots должны
  участвовать в полном roundtrip. Restore в отдельный пустой synthetic root,
  без downgrade/schema spoof/перезаписи источника. Existing tests
  `test_complete_backup_verify_restore_preserves_every_fact_schema_and_byte`
  и `test_schema_spoof_with_supported_revision_is_rejected` расширяются по фактам,
  [источник](../../tests/integration/test_backup_recovery.py).
- Приёмочный профиль QA-A: несколько дисциплин/групп ×30 студентов, 17/18 недель,
  десятки работ, несколько Attempts/Grades и сотни immutable attachments; query
  budget не растёт по ячейкам, file workers не блокируют Qt.
- Native Windows checks и packaged workflow отделены от Linux pytest; Actions
  для implementation запускать только по отдельному разрешению, CI не ослаблять.
  Полный Windows regression из требований нельзя заменить одним Linux PASS:
  согласовать actual Windows evidence до закрытия QA-A; NOT RUN остаётся открытым.

### Границы QA-A и дальнейшие этапы

QA-A даёт новый план/выдачу/точные баллы, сохраняет существующие history/DTO.
QA-B затем 009→008, 012→015, 027→028→017→029. Перед QA-B review model QA-A уже
должен допускать проверку одной сдачи; minimal pending preview/cancel обязателен
в 027/028. QA-C унифицирует 021 и завершает 014/022/023, не оправдывая отсутствующий
preview в QA-B. QA-D доводит общие стили/interaction и native visual audit.

## История результата

2026-10-10: первый архитектурный аудит 30 требований и план QA-A на указанной
public main базе. Статические evidence/риски/предложения зафиксированы;
implementation acceptance и ручные проверки открыты. При следующих аудитах
добавлять датированные изменения/PR/actual checks, не удалять этот baseline.
