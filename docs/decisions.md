# Решения и открытые вопросы

<a id="adr-053"></a>

## ADR-053 — Принятие рабочей базы и дальнейшая работа по модулям

**Дата решения владельца:** 2026-10-12, Europe/Moscow. **Статус:** ACCEPTED.

Пакет ST-QA-001–ST-QA-030 принят как рабочая база с остаточными замечаниями.
Следующие доработки выполняются отдельно по функциональным модулям.
Принятая версия: [PR #3](https://github.com/COLOSSAL-maksik/Studium-public/pull/3),
проверенный HEAD `3eff0293f8540fa848a3175dd15ad34994268235`, включая четыре
ST-PR3-001–004 и дополнение frozen Topic/Skill. Документационное дополнение
не меняет её код, tests, dependencies, CI, installer, ресурсы или v1–v12.

Принятие этапа владельцем отделено от реализации, автоматических checks и
ручного evidence отдельного сценария. Полная ручная проверка всех 30 не заявлена;
индивидуальные Manual PENDING/NOT RUN сохраняются в [матрице](management/QA_ALL_30_IMPLEMENTATION.md)
и [checklist](qa-all-30-manual.md). Они не блокируют уже принятое решение о базе.
Приёмка с остатками не означает отсутствие дефектов. Исходные ID, требования,
приоритеты и история сохраняются; исправленные review cases не переоткрываются
без нового воспроизведения.

[BACKLOG](management/BACKLOG.md) — действующий список остаточных ограничений,
непроведённых проверок и последующих конкретных замечаний. Неописанные владельцем
недоработки требуют описания при проверке выбранного модуля; ошибки не угадываются.
QA-A→QA-B→QA-C→QA-D и прежний 10-PR plan — история завершённого пакета, не очередь.
Правило ограниченных итераций записано в [ROADMAP](management/ROADMAP.md).
Первый модуль не выбран; новый общий пакет, реализация и задачи агентам не начинаются.
Неутверждённые UX-концепции не становятся требованиями. Bender и его интеграция
остаются отдельным проектом Jules.

Владелец разрешил Markdown-only commit в PR #3, обычный push и после успеха
required checks итогового HEAD — squash merge с expected HEAD без обхода защиты
main. Это заменяет прежний запрет merge данного пакета. Фактический merge commit
фиксируется GitHub в PR. Force-push, release, новый installer и дополнительные
full_windows/workflow_dispatch не разрешены; локальные полные regression/package
для этого документационного дополнения не повторяются.

<a id="adr-052"></a>

## ADR-052 — Запрет archive frozen классификации

**Дата:** 2026-10-11. **Статус:** IMPLEMENTED; manual acceptance PENDING.
Основание: дополнительный ST-PR3-002 на `67986fd`.

Два synthetic сценария подтвердили успешный archive и последующий SQL отказ
выдачи V1. Сохраняем общие endpoint guards и заранее отклоняем несовместимое
архивирование. Проверяются **записанные** taxonomy UUID в версиях, конкретных
plan sources и индивидуальных snapshots; mutable библиотека не источник истории.
Preflight всего subtree атомарен. Error DTO перечисляет зависимые версии/работы/
назначения с context и UUID; desktop показывает его через прежний error boundary.
Новые индивидуальные snapshots сохраняют topic_ids и skill_ids. Никакой teacher
information не добавляется в public whitelist.

Additive v12 содержит только два BEFORE archive guards. Общие SQL triggers и
22 v1–v11 payloads побайтово прежние, tables/rows/snapshots не переписываются.
Защита действует и для raw writes; persisted saved version удерживает endpoint
независимо от live links, назначения группе, отмены/архивирования плана и V2.
Это намеренная lifetime зависимость immutable содержания. Свободная taxonomy
архивируется. Уже невалидная pre-v12 классификация не восстанавливается: новая
freeze/выдача отказывает явно, прежние неизвестные связи не реконструируются.
Populated upgrade/late DDL rollback, facts/UUID/file hashes, reopen/backup и actual
GUI проверяются в test_pr3_frozen_taxonomy. Manual всех 30 остаётся PENDING.

<a id="adr-051"></a>

## ADR-051 — Исправления четырёх замечаний PR #3

**Дата:** 2026-10-11. **Статус:** IMPLEMENTED; manual acceptance PENDING.
Основание: ST-PR3-001–004; прежние B1–B9/ADR-050 сохраняются.

Первая поздняя сдача не требует заранее созданного StudentWork. Внутри атомарной
команды вставляется LateWorkAuthorization для concrete ended enrollment и
исходной Assessment, затем StudentWork/Attempt/Submission/files. Deferred FK
не позволяет оставить authorization без работы. Только WITHDRAWN/COMPLETED,
не deleted, исходная фактическая выдача до окончания участия; поздняя дата записи
выдачи не подменяет её event time. Чужой offering
отвергается. Term.archived не равен deleted. Отдельное подтверждённое восстановление
с причиной и DebtRestoration audit допускается до первой сдачи, без fake ACTIVE.

В версии фиксируются effective problem text/title, source/family revisions,
variant parameters, exact topic/skill links, teacher schema/answer и file IDs.
Общие файлы definition/packs и выбранных материалов также сохраняются; bytes
не копируются по группе. PlanContentSource связывает конкретный module/work
с исходной immutable version/ordinal. AssessmentItem и StudentProblemAssignment
получают frozen content, включая архивированный source. Student output использует
whitelist statement-only DTO; teacher files/answers не публикуются.

Pure preview переназначения перечисляет retained/retired/incoming modules/works
и counts выдач/попыток/сдач/reviews/required sets. Apply требует подтверждения,
expected plan revision и неизменённого fingerprint assignments/facts. Можно
сохранить все назначения и добавить новое содержание либо явно архивировать
невыданные работы и заменить их. Выданные работы и required modules сохраняются
с прежними bindings. Пересечение retained/new modules — отказ: преподаватель
должен явно согласовать календарь. Изменить ordinal можно у пустого/заменяемого
невыданного плана; retained assignments прежнего семестра требуют отдельного
плана исходного периода. Facts не перемещаются между семестрами.

Сводка показывает все исходные периоды. Active total — issued без cancelled;
not-issued/cancelled отдельно. Выполнено — distinct work с substantive attempt;
зачтено — current explicit ACCEPTED. Awaiting — последняя substantive сдача без
substantive review; COMMENT_ONLY не завершает ожидание, SCORED завершает проверку
без автоматического зачёта. «Не сдано в срок» включает отсутствие своевременного
предъявления и позднее первое предъявление по current typed deadline: DATE/WEEK
exclusive, EXACT inclusive. Unknown deadline не становится просрочкой. Exact
cents и legacy REAL отображаются раздельно без округления. Attendance сохраняет
(PRESENT+LATE)/(PRESENT+LATE+ABSENT); EXCUSED/UNKNOWN/missing отдельно, cancelled
lessons исключены. Доступны ДЗ/РК/экзамены, evidence, charts и исходные долги.

Additive `0011_qa_review_fixes`: две новые таблицы, прежняя v10 неизменна.
Earliest saved binding backfill не восстанавливает отсутствовавшие problem
snapshots. Выдача такого unissued legacy назначения требует новой явной версии;
mutable library не подставляется. Backup head/fingerprint guards остаются строгими.
ZIP v10 восстанавливается прежним compatible v10 candidate, затем standalone
synthetic профиль обновляется до v11; ZIP не переписывается. Fresh/populated
upgrade, late rollback, reopen и v11 round-trip проверяются реальной БД/файлами.
Pre-v11 shared files без исторического snapshot сохраняют прежний compatibility view;
его current links не объявляются историческим содержимым версии. Новая выдача
явно закреплённой версии использует сохранённые snapshots/files.
[Отчёт review](management/PR3_REVIEW_FIXES.md),
[единый checklist](qa-all-30-manual.md).

<a id="adr-050--qa-all-30-implementation"></a>

## ADR-050 — Единый пакет 30 требований: календарь и факты проверки

**Дата исполнения:** 2026-10-10. **Статус:** IMPLEMENTED; manual acceptance PENDING.
Прямое пакетное задание заменяет предложенные 10 PR и промежуточные manual gates
ADR-049. B1–B6, QA-A-REV-01/02 сохранены. Задание датировано 2026-10-11;
execution environment — 2026-10-10. Записи ниже сохраняют прежнюю историю.

`0010_qa_package` добавляет 21 таблицу: 100 user tables / 101 с Alembic.
CourseProgram → immutable ProgramVersion/ProgramDirection/VersionReference
отделены от SemesterPlan/PlanModule/PlannedWork конкретного offering. Ordinal
задаётся явно, AUTUMN/SPRING его не определяют. Legacy mapping по UUID, не title;
raw WorkProgram, связи, NULL, REAL и snapshots сохраняются. Только полный XX.XX.XX
связывается автоматически после NFC/trim; identity casefold + normalized UNIQUE.

Preview чистый; commit атомарный с revision checks/PlanHistory. Соседи не сдвигаются
автоматически. Deadline за модуль/семестр требует предупреждения/подтверждения,
модули внутри семестра. EXACT_INCLUSIVE сохраняет legacy UTC/operator,
DATE_EXCLUSIVE — next-day-start в explicit offset, WEEK_ONLY — current calendar.
Default нового плана +03. IssuedWork actual отдельный, ambiguous legacy unknown.

Новая сдача создаёт одну Attempt + Submission; re-review только immutable Review.
ReviewGrade/ReviewFile/ReviewReturn имеют concrete FK и independent timestamps.
SCORED после NEEDS_REVISION этой сдачи запрещён application/SQL без записи,
доработка завершается explicit ACCEPTED. Resolver сохраняет legacy fold и порядок
Attempt number/review_seq: re-review S1 не вытесняет S2. Grade/result/rule
проверяются вместе. Min — нижняя граница начисления; pending/revision без 0.
Decimal input → int64 cents без rounding, максимум 92233720368547758.07;
legacy REAL lossless. Fractional default OFF, ON до двух знаков; saved bounds
копируются при OFF. Для прежней сдачи после изменения rule явный old/current.

B7–B9 приняты именно пакетным заданием, не ретроспективно. SLA default 7 calendar
days от received_at в explicit fixed offset; equality не overdue, near default
24 часа; оба settings persisted. Recording time отдельно. B8 выполнено =
substantive submission, зачтено = ACCEPTED, cancelled вне active denominator,
attendance denominator прежний. RequiredWorkSet versioned student/module,
unknown не закрывает модуль; все concrete bindings должны быть ACCEPTED.
DebtRestoration с confirmed reason сохраняет ended enrollment/immutable историю.
B9 numeric/symbolic допускают arbitrary physical Decimal precision; units
optional, formula/comments plain text. Template copied snapshot, teacher-only.

StagedAttachmentPicker не пишет до save; metadata/links/file batch атомарны.
Late failure откатывает DB и опубликованные файлы; post-commit finalize failure
сохраняет bytes/recovery journal. JPEG/PNG/WebP/PDF previews bounded, DOC/DOCX icon.
Внешний редактор получает рабочую copy в cache. IO — Qt workers; cyclic Qt wrappers
собираются application-owned GUI timer, исключая их разрушение worker GC.

v1–v9 Python/SQL raw bytes неизменны; static DDL/backfill transactional,
deterministic UUIDv5. Fresh/populated/late rollback/reopen/new-head restore тестируются.
ZIP v1 без preferences: новый restore OFF, saved fractions видимы. Archive 0.1.0
восстановить прежним совместимым release в отдельный профиль, затем upgrade;
unknown schema/fingerprint/version guards не ослабляются. Candidate 0.2.0 честно
отличает новую schema; релиз не опубликован. [Карта](management/QA_ALL_30_IMPLEMENTATION.md),
[общая manual проверка и Windows candidate](qa-all-30-manual.md).

<a id="adr-049--qa-a-product-contracts"></a>

## ADR-049 — QA-A: продуктовые контракты и безопасная совместимость

**Дата:** 2026-10-11. **Статус:** ACCEPTED для B1–B6 продуктового поведения;
**PROPOSED** для технического хранения/таблиц/алгоритмов до review.
**Implementation/manual acceptance:** не выполнены, соответствующие tests NOT RUN.
Проверенная база actual main: `b620ef3635c2965ad3630bae15d00d1b7bd9a82d`.
[QA_A_CONTRACTS](management/QA_A_CONTRACTS.md) — конкретные таблицы переходов,
Grade binding, примеры дат/правил/preferences, actual-source migration mapping.

Одна программа описывает целый курс; назначенная версия frozen, новое содержание
создаёт новую версию без automatic group switch. Ordinal курса явно сопоставляется
с периодом группы, календарь offering отдельно. Старые программы по имени не сливать.
Deadline работы можно переносить за module и, по дополнительному согласованию,
после семестра с предупреждением и подтверждением; modules остаются внутри
семестра. Preview/cancel без записи, подтверждённые changes atomic с историей,
не меняют сдачи/Grade/actual issuance и их historical dates.

Обычный deadline — date-only конец учебного дня в explicit plan offset,
новый default Москва +03. Предлагается excluded next-day-start граница; exact
deadline имеет priority и сохраняет legacy inclusive semantics/timestamps.
Actual issuance отдельным фактом; legacy issued_at raw и ambiguous provenance,
не доказанный actual факт. Раннее ДЗ разрешено, journal — по current due.

Актуальная B4 заменяет предложение дробного ввода по умолчанию: новые score и
numeric min/max целые; сохраняемый Settings «Дробные баллы (2 знака после запятой)»
default OFF. ON допускает до двух знаков, OFF отклоняет новые fractional values,
никаких hidden rounding/truncate/unsaved loss. Toggle не меняет saved fractions,
rules/snapshots/statistics; пустой integer interval объясняется, bounds не меняются.
Min — минимальный начисляемый балл inclusive, pending/revision/absence без 0.
Technical proposal: Decimal/int64 cents 0..92233720368547758.07, explicit overflow
guards, lossless tagged REAL compatibility; предел не единый педагогический max.
Исходная decimal accuracy legacy REAL не восстановлена, >2 digits не округлять.

Проверка привязана к saved submission; re-review создаёт только immutable review,
не новую Attempt/no. Предлагаются concrete Review/ReviewGrade и evidence-aware
resolver с прежним legacy Attempt fold; Grade numeric совпадает с result snapshot,
PASS_FAIL/Traditional semantics сохраняются. Legacy events не делятся на две
выдуманные даты/сдачи. Каждая новая review фиксирует выбранный rule UUID/snapshot;
для pre-change submission преподаватель явно выбирает old/new, новые submission
получают current rule. Старые result/min/max неизменны.

ADR-009/010/018/030/037/039 остаются описанием действующего legacy кода; их SQL
guards и historical v1–v9 не снимаются этим документом. Новые exact storage/rules
реализуются отдельно, backup требует new-head/legacy compatibility review.
OPEN-002/009/011 не закрываются целиком. B7–B9 остаются QA-B/C. Разбиение на 10 PR
PROPOSED, не утверждено владельцем; следующий небольшой implementation scope
предложен как directions foundation PR-02 после review и отдельного задания.
30 исходных ST-QA/приоритеты/этапы и baseline ADR-048/аудита сохранены.

**Последующее уточнение 2026-10-11 после review HEAD
`3649afaee48be28d27f81ac41aff86087d594636`:** [B2 — индивидуальный долг](management/QA_A_CONTRACTS.md#b2-student-debt)
связывает ST-QA-011/029. H1 из T1 остаётся долгом в T2 до explicit ACCEPTED;
модуль студента закрывается по ACCEPTED всех обязательных работ, отдельно от
calendar группы. Поздняя сдача не переносит срок/UUID/offering автоматически.
Обязательность/individual closure schema и ended-enrollment/archive write policy
ещё PROPOSED; полный UI сводки/queue — QA-B. Это дополнение ранее не утверждалось
как часть исходного B2 и не закрывает implementation/manual acceptance.

QA-A-REV-01: новый REVISION_REQUIRED→SCORED запрещён без записи; завершение
доработки требует явного ACCEPTED, re-review не меняет attempt_no. Допустимый
SCORED сам не создаёт зачёт, legacy fold не изменяется. QA-A-REV-02: mode
ограничивает новый/изменённый teacher input; unchanged сохранённые rule bounds
можно копировать в Review snapshot при OFF с новой целой оценкой. Создание/
редактирование fractional bounds и новая fractional оценка требуют ON;
legacy incomplete rule не дополняется выдуманным min. Примеры/таблицы в contracts.

<a id="adr-048--qa-register-и-семантика-min"></a>

## ADR-048 — QA Register и семантика min

**Дата:** 2026-10-10. **Статус:** ACCEPTED для требований и смысла min;
implementation schema/Grade lifecycle остаются предметом последующих решений.
**Актуализация 2026-10-11:** product B1–B6 согласованы в ADR-049; техническая
schema остаётся proposal, код и acceptance прежние. Нижеследующая запись
сохраняет исходное состояние до согласования.
Разбиение QA-A на 10 PR — PROPOSED, ещё требует утверждения владельца;
статус ACCEPTED выше на разбиение не распространяется.

[QA Register](management/QA_REGISTER.md) содержит 30 исходных ST-QA,
[QA Audit](management/QA_AUDIT.md) — evidence и предлагаемый последовательный план.
Порядок QA-A → QA-B → QA-C → QA-D, исходные ID/приоритеты неизменны.
Аудит документационный: не начинает QA-A и не закрывает manual acceptance.

ST-QA-030: min — минимальный начисляемый балл, не порог зачёта. Для min=18,
max=30 начисление допускает только 18–30 включительно; отсутствие оценки и
доработка — отдельные состояния без автоматического нуля. Exact decimal values
и immutable история отдельных попыток обязательны. Ноль может быть реальным
баллом лишь в допустимом индивидуальном диапазоне, а не заменой отсутствия.

ADR-009/010/018/030 описывают действующие legacy Grade/projection/semantic lock;
этим решением их реализация не меняется. Для новых scoring rules требуются
explicit version/snapshot и compatibility resolver, сохранение old REAL facts
и historical max. Precision, review→submission/Grade binding и применение
новых критериев к будущим проверкам — B4–B6 аудита, смысл min уже закрыт.
ADR-039 остаётся описанием текущей семестровой модели до implementation 003;
proposed независимые content/version и offering plan не объявлены реализованными.
OPEN-002/009/011 сохраняют прежнюю историю и открытые остатки.

**Уточнение review 2026-10-10:** предлагаемый план из 10 PR QA-A ещё не утверждён
владельцем. ST-QA-019/020 дорабатываются и принимаются совместно;
эта связь отделена от обязательных предварительных зависимостей и не задаёт цикл.
Исходные ID/приоритеты и порядок QA-A → QA-B → QA-C → QA-D сохраняются.

> Документ относится к Studium как независимому локальному приложению.
> Bender — отдельный проект; будущая интеграция использует локальный JSON-RPC
> 2.0 over stdio. Прямые импорты Bender, API/client, облачный сервер и новые
> возможности этим переносом не реализованы. Описания прежних фаз сохраняют
> технические требования; их проверки и acceptance не подтверждены этим текстом.

Это полный журнал ADR и OPEN. Актуальный индекс применимости —
[management/DECISIONS.md](management/DECISIONS.md), остатки задач —
[management/BACKLOG.md](management/BACKLOG.md).
Датированные фазовые записи сохраняют первоначальный scope; отсутствие
возможности «в этой фазе» не означает её отсутствия после последующего merge.
Частичный Dart stack заменён ADR-014. Старые security/history blockers
и запреты remote относятся к своим этапам. Текущий целевой source repository:
COLOSSAL-maksik/Studium-public; его публикацию выполняет владелец.

## ADR-047 — Repository isolation и локальная проверка границы данных

**Уточнение актуальности 2026-10-10:** независимая чистая source history
проверена локально; workflows сохранены как конфигурация, Actions
в новом repository не запускались. Описание PENDING/BLOCKED ниже
сохранено как исходный security-stage record. Граница runtime/private данных
[текущее состояние](management/PROJECT_STATUS.md).

**Дата:** 2026-10-05. **Статус:** ACCEPTED для локального security stage;
history cleanup отдельно PENDING по выбору пользователя.

AppPaths централизует один Windows application-data root; production default,
явный --data-dir, database engine и FileStorage отвергают resolved path внутри
Git, включая worktree marker. Relative FileAsset keys, import compensation,
schema и исторические migrations сохраняются. SQL exception messages скрывают
bound parameters. Pytest перенаправляет LOCALAPPDATA до collection и блокирует
прямой доступ к production root. Domain и dependency contracts не меняются.

Stdlib safety checker проверяет staged **index bytes**, working source tree и
все reachable history roots, включая Codex tree refs. Изображения/документы
допускаются по reviewed path+SHA-256; изменение требует нового content review.
Gitleaks отсутствует: fallback честно ограничен robust secret formats и privacy
signals, без догадок о ФИО. Local hook установлен; минимальный pinned CI только
подготовлен. Новый demo generator никогда не открывает существующую DB или
production root, создаёт явно искусственные записи вне checkout.

Текущие technical username paths и семь PNG обезличены локально. В истории
найдены старые версии; пользователь выбрал отдельный план очистки, поэтому
refs не переписываются в этом шаге. История и пользовательские данные не удалены;
remote/push/сеть/внешние agents/Iteration 5 не начаты.

## ADR-045 — Data safety и явное удаление из активной работы

**Дата:** 2026-10-05. **Статус:** ACCEPTED для Iteration 4.
**Основание:** [Iteration 4](iteration4-request.md), §§2–6; прямое разрешение
пользователя на проверяемое пересоздание FileAsset для старого DOC.

UI «Удалить» использует существующие UUID/revision/soft-delete, сохраняет
Attempt/Attendance/Message/назначения и immutable file bytes. Course, Group,
AcademicTerm и WorkProgram не каскадируют удаление в reusable Library. Counts
зависимостей показываются до удаления; ранее связанные материалы сохраняют
дисциплину с исторической пометкой. Student отдельно завершает Enrollment или
удаляется из активной работы. Physical DELETE новых связей запрещён triggers.

Managed storage прежний: FileAsset metadata в SQLite, bytes вне БД, path relative
к data root, SHA-256/размер и компенсационный import journal. При открытии
используется internal absolute path, не путь источника. Source removal/reopen,
missing file и immutable snapshots проверяются синтетическими сценариями.

`0009_daily_workflow` добавляет конкретные `seminar_problems` и `module_topics`
(unique endpoints, matching Course, FK RESTRICT, identity/revision guards).
Отдельные сущности SeminarPlan/ProblemFamily/StudentWorkCategory не вводятся.
Для DOC пользователь разрешил исключение из additive-only: внутри транзакции
FileAsset пересоздаётся из прежнего DDL с единственным расширением CHECK,
все строки/indexes/triggers восстанавливаются, FK остаются включены и
проверяются до commit. Тест позднего сбоя доказывает полный rollback. Bytes
и attachment links не переносятся/не переписываются. 0001–0008 неизменны.

## ADR-046 — Модульная offline справка и factual daily views

**Дата:** 2026-10-05. **Статус:** ACCEPTED для Iteration 4.
**Основание:** [Iteration 4](iteration4-request.md), §§7–18/24.

Категории Works/Progress — presentation над прежним AssessmentType и историей
Attempt. Даты/состояния вычисляются из прежних фактов; чтение не создаёт Work,
Attempt или оценку. Массовая посещаемость использует существующую atomic
mark_attendance_many только для выделенных enrollment в одном столбце недели.
Preview использует прежний bounded image/PDF pipeline, выбранный файл и
generation guard; весь банк заранее не декодируется. SeminarProblems и
ModuleTopics переиспользуют реальные Problem/Topic, без копий содержания.

Help Center внутри MainWindow: 20 отдельных Markdown resources и JSON index,
локальный поиск, навигация и open_help(article_id), graceful missing article.
Resources включаются в wheel/onedir, сетевых обращений и зависимостей нет.
Обновление только затронутых статей входит в DoD; [правило сопровождения](help-maintenance.md).
Ширины таблиц сохраняются в локальных JsonPreferences, учебная БД не меняется.

## ADR-044 — Problem как общее условие с дочерними вариантами

**Дата:** 2026-10-04. **Статус:** ACCEPTED для Iteration 3, ручная приёмка ожидается.
**Основание:** [Iteration 3](iteration3-request.md), §§12–13/23.

Существующая `Problem` остаётся канонической записью банка. `is_family` отличает
общее условие; дочерняя `Problem.family_id` с кодом варианта хранит только схему,
параметры, ответ и файлы решения. Отдельные ProblemFamily/ProblemTemplate tables
не создаются. Standalone по умолчанию сохраняет прежнее поведение. Семья задаёт
общий текст, discipline, identifier, Topics/Skills, tags/collections и типизированный
multi-select `ProblemPurpose` (SEMINAR/CONTROL/EXAM/CONSULTATION), отдельный от tags.
Пустое назначение старых задач означает «не задано»; миграция не угадывает его.

Additive `0008_problem_variants` добавляет пять columns и constraints/indexes/guards
к `problems`; 0001–0007 неизменны. Новых таблиц и dependencies нет. Family ownership
не меняется после создания; variant code уникален внутри семьи; DB и application
защищают scope и запрещают повторное хранение shared statement/classification.
Inline self FK использует SQLite default NO ACTION (как предыдущие additive FK
v7): удаление parent с дочерними ссылками запрещено, CASCADE нет. Metadata и
реальный PRAGMA проверяются вместе; family/code invariant выражен triggers,
без фиктивного table CHECK и без batch-пересоздания `problems`.
Generator получает resolved variants, сохраняя прежний алгоритм. Review включает
current parent revision; изменение семьи после review отменяет save целиком.
Ticket/assignment snapshots фиксируют условие с параметрами, skill IDs, ответы
и прежние immutable FileAsset FK. Редактирование банка не изменяет выданные факты.

Library разделяет raw Problem Bank и сохранённые TicketSets. TicketSet по прежней
модели принадлежит CourseOffering: группу выбирают перед генерацией. Универсальные
независимые от группы RK templates не вводятся. Варианты одной семьи могут попасть
в один билет при нескольких задачах: новый запрет/формула без задания не добавлены.

## ADR-043 — SQLAlchemy Python implementation в portable bundle

- **Дата:** 2026-10-04. **Статус:** принято для Iteration 2.5 packaging; native smoke и regression обязательны.
- **Основание:** frozen SQLAlchemy 2.1.1 блокируется при импорте `_processors_cy`; source Python загружает тот же pyd (SHA256 совпадает). Изменение порядка Qt/SQLAlchemy проблему не решает. Изолированная frozen-сборка с официальными `.py` implementations той же версии выполняет `--help` с exit 0.
- **Решение:** `Studium.spec` копирует locked SQLAlchemy из `.venv` в новый игнорируемый build staging directory без optional `.pyd`, сохраняя исходные `.py` без правок. Analysis использует staging; assertion запрещает SQLAlchemy binaries в bundle. Остальные dependencies, production Python и schema прежние.
- **Последствия:** portable использует штатный Python backend SQLAlchemy; dev `.venv` не меняется. Проверяются полный regression на том же Python backend, свежий exe, migration/v7 preservation/workflow/reopen и performance budgets. Это packaging workaround, а не установленная native root cause. Вернуться к Cython можно только после отдельной воспроизводимой проверки frozen startup.

## ADR-042 — Linear Academic, только presentation composition

**Статус:** ACCEPTED. **Дата:** 2026-10-04. **Основание:** явное задание

UI использует общие logical-pixel tokens, две явные нейтральные палитры,
системный Segoe UI, собственные Qt-painted line icons без dependency/assets
и стандартные Qt layouts/widgets. Home/course/program имеют воздух; Journal
остаётся плотной таблицей с frozen колонкой и прежней моделью. Редкие поля и
файлы раскрываются без изменения save contracts и учебных фактов.

Последствия: presentation files и synthetic QA расширяются; domain,
application formulas, persistence, migration 0007 и historical 0001–0006
не меняются. Внешние design libraries, fonts, animations и новые workflows
не вводятся. Checkpoint не означает acceptance; финальный commit 2.5 только
после ручной совместной приёмки и отдельного разрешения.

## ADR-039 — Iteration 2: Course, WorkProgram и исторические факты

**Статус:** ACCEPTED для реализации. **Дата:** 2026-10-03.
**Основание:** [задание Iteration 2](iteration2-request.md), §§0–2/30–32.

Course остаётся канонической дисциплиной; отдельный дубликат Discipline не
вводится. WorkProgram содержит направление, версию, тип семестра, начало первой
недели, явную длительность (новая программа по умолчанию 17 недель), offset и
AcademicTerm. CourseOffering выбирает конкретную программу той же дисциплины
и периода. ProgramModule задаёт непересекающийся диапазон; ProgramWork отделяет
применимость reusable определения от фактически выданной Assessment.

Существующая HomeworkDefinition расширяется типом работы. WorkDefinition —
совместимый alias того же канонического record/table, не второй каталог ДЗ.
ProgramWork → definition_id ссылается на исторически названную таблицу
homework_definitions. Schedule/date/module живут на связи с программой.
Выдача создаёт самостоятельную Assessment с содержанием и source links;
последующая правка reusable определения не меняет Attempts/выданное содержание.
Плановые ячейки не создают StudentWork или Attempt до явного действия.

Миграция 0007 создаёт отдельную backward-compatible программу на каждый старый
offering и переносит его план без смешения групп. Новые nullable FK добавляются
к существующим таблицам; все прежние column values/revisions остаются прежними.
В единственной DDL-транзакции metadata triggers двух таблиц временно снимаются
для заполнения **только новых колонок**, затем восстанавливаются с точным прежним
SQL до commit. Ошибка откатывает весь upgrade. Новые определения сохраняют
старые названия/описания/типы, исходные source/file links Assessment остаются.
Старые py/SQL migrations 0001–0006 не редактируются. Длительность legacy
программы расширяется только до уже явно записанной плановой недели; календарный
учебный год не генерирует 50+ недель автоматически. Legacy >104 — явный отказ
с сохранением исходной БД, а не отсечение данных.

NULL program FK сохраняется только для обратной совместимости прямого
repository API; новые application команды и UI всегда выбирают/создают
конкретную программу. Смена программы offering после работ/занятий запрещена,
чтобы не подменить исторический контекст. Приёмка и финальный commit Iteration 2

## ADR-040 — Общие файлы, ручная база знаний и factual skills

**Статус:** ACCEPTED для реализации. **Дата:** 2026-10-03.
**Основание:** Iteration 2 §§12/14–19/23–25/28–29.

HomeworkPack связывает несколько определений ДЗ с одним набором FileAsset;
bytes не копируются при привязке. ProgramAttachment хранит версии официального
документа; новая версия — новый immutable asset, прежние links сохраняются.
MethodicalMaterial отделён от SeminarMaterial; lecture/seminar различаются
типом reusable материала. Конкретные FK/link tables сохраняют scope discipline.

KnowledgeEntry — вручную обобщённый draft с отдельной canonical формулировкой;
many-to-many KnowledgeSource сохраняет исходные QuestionCase/Message без
перезаписи. Occurrence count/first/last вычисляются из distinct source cases.
База знаний по умолчанию не выводит ФИО. Matching/manual grouping только вручную.

РК использует Problem Bank через DefinitionProblem/AssessmentProblem и
исторический task snapshot; StudentProblemAssignment фиксирует выданный
студенту состав. AttemptItemResult остаётся каноническим результатом задачи;
StudentProblemFile фиксирует FileAsset/role/name на момент назначения,
переиспользует те же immutable bytes и защищён от физического удаления/подмены.
AttemptSkillResult уточняет factual outcome выбранного сквозного Skill внутри
этой задачи. Общий результат задачи не размножается на навыки автоматически.
Новые skill facts immutable; новая попытка хранит новый набор outcomes.
Для новых Homework REJECTED запрещён application/DB guards; прежние факты не
мигрируются и не удаляются. Cancelled Lesson исключён из attendance analytics;
перенос сохраняет planned date/week и отдельно меняет actual lesson_date.
Новых зависимостей, AI, mastery, ranking или внешних интеграций нет.

## ADR-041 — Контекстная навигация и visual system

**Статус:** ACCEPTED для реализации, UX-приёмка ожидается. **Дата:** 2026-10-03.
**Основание:** Iteration 2 §§3–7/9/17–18/21–22/26–27/34–37.

Глобальные режимы: Главная / Работа / Дисциплины / Библиотека / Добавить /
Настройки. Конкретный объект и его tabs находятся внутри страницы. Home
содержит три крупные tiles и продолжение последнего offering. Программы,
дисциплины, библиотечные editor/file/catalogue widgets используют один shell.
Light/Dark и last offering сохраняются в прежнем preferences.json с сохранением
active term/неизвестных полей. Qt Fusion/QSS сохраняются. Journal плотный,
frozen FIO/scroll/header; графики остаются в Analytics. as_of использует
работающий datetime cutoff текущих сохранённых фактов, без обещания полного
audit snapshot прошлых редакций. Ручная Explorer→exe проверка остаётся отдельной
приёмкой, пока нет фактического native подтверждения.

## ADR-035 — Phase 6.6, offline-first и внутренние страницы

**Статус:** ACCEPTED для реализации. **Дата:** 2026-10-03.
**Основание:** [задание Iteration 1](phase66-request.md), §§0–7/22/25/39–40.
Ruff PASS и 475 PASS (99.23 s). Phase 6.6 разрешена отдельно; final commit
не разрешён. Windows/local/offline-first сохраняются. Server, sync, mobile,
AI/LLM/OCR, live Telegram/email отложены без даты начала. EMAIL/TELEGRAM остаются
каналами происхождения manual messages. Phase 7/Iteration 2 не начинать.

NavigationStack сохраняет страницы и Back/breadcrumb внутри MainWindow.
Sidebar: Обзор, раскрываемые Группы (CourseOffering активного периода),
Материалы, Добавить; Настройки снизу. Вопросы — внутри группы/студента/работы/
попытки. Маленькие quick-input/confirm/pickers остаются dialogs. Existing
details QDialog в shell получают Qt.Widget parent/flags; standalone component
tests сохраняются. Domain/application boundary не меняется.

## ADR-036 — Библиотеки, общий tagging/file contract и migration v6

**Статус:** ACCEPTED. **Дата:** 2026-10-03. **Основание:** задание §§12–15/20–23/26–31.
HomeworkDefinition, Problem, SeminarMaterial, LiteratureItem отделены от
StudentWork/Attempt/Lesson. Plain text/Markdown, UUID/EntityMetadata прежние.
Общий tags_json — JSON array строк с одним casefold-контрактом. Наборы
ProblemCollection + Member имеют отдельную many-to-many семантику.
Concrete attachments/Topic links сохраняют FK, без universal owner framework.
File roles отделяют STATEMENT/REFERENCE/SOLUTION; pipeline/journal/SHA-256/
integrity/image/QtPDF/default-app preview Phase 4 переиспользуется.

Additive `0006_content_workflow`: 16 новых tables, nullable Assessment weeks и
source homework FK, Lesson.type default SEMINAR и calendar offset периода.
Всего 47 user tables. v1–v5 не редактируются. Новые tables — FK RESTRICT;
inline Assessment.homework_definition_id — immediate NO ACTION без cascade
для SQLite ADD COLUMN/reflection. Прямой PRAGMA/invalid-reference tests
проверяют действие FK, metadata/checks проверяются отдельно.
Assessment при выдаче копирует title/description и source UUID; остаётся
самостоятельным фактом. Semantic lock защищает также source link.
FAQ отложен: FAQDraftContract содержит reviewed question/answer, source case,
Course/Topic IDs, inactive default. Portal/публикация/AI отсутствуют.

## ADR-037 — Учебные недели, legacy deadlines и лекции

**Статус:** ACCEPTED. **Дата:** 2026-10-03. **Основание:** задание §§8–11.
AcademicWeekNumber — int >=1; odd числитель / even знаменатель вычисляются.
Неделя 1 — семь календарных дней от starts_on; далее интервалы по семь дней,
без ISO week/понедельника. planned_issue_week/planned_due_week nullable;
exact issued_at/due_at сохранены. issued_at — время выдачи/создания;
planned_issue_week дополнительно ограничивает analytics будущих плановых работ.

Приоритет **exact due_at > planned_due_week**. Без exact deadline первое
содержательное предъявление в due week/раньше — вовремя, позже — поздно.
Без предъявления overdue только со следующей недели. COMMENT_ONLY не сдача.
Legacy сохраняет прежние формулы и N/A без срока.
Attempt UTC переводится в calendar offset периода week_utc_offset_minutes;
default +180 соответствует Moscow контексту задания. Пользователь выбирает
offset периода явно; Windows timezone не меняет классификацию. Fixed offset,
без DST. Начало/offset блокируются после Attempt работ с неделями.
Перенос срока пересчитывает timely без заявленного audit (OPEN-011).
Остаток OPEN-009 о membership дня/DST сохраняется.
Старые Lessons получают SEMINAR; Lecture использует тот же Attendance.

## ADR-038 — Детерминированные варианты, снимки и factual charts

**Статус:** ACCEPTED. **Дата:** 2026-10-03. **Основание:** задание §§16–19/24/34–35.
Pool: Course + все tags + collection + active. Seed и сортировка UUID дают
повторяемость на том же pool. Уникальные unordered комбинации, без повторов
внутри варианта. C(pool,size) < variants — явная ошибка; задачи между
вариантами могут повторяться, одинаковые комбинации не выдаются.
Draft допускает regenerate/eligible replacement. Save проверяет original
revisions, criteria и unique composition, атомарно сохраняет TicketSet/Ticket/
TicketProblem/TicketProblemFile. Снимки копируют title/statement/teacher answer/
solution, source revision и FileAsset FK; bytes immutable, archive asset
при snapshot link запрещён. Правки исходного Problem не меняют старый набор.
Новый состав — новый набор. Enrollment assignment revisioned/explicit;
auto assignment — текущий roster по ФИО, число вариантов должно совпасть.
Ручное N/не назначать разрешены; предпочтений по способностям нет.
StudentTicketProblem — whitelist условия/STATEMENT files, без answers/REFERENCE/
SOLUTION. PDF export/student portal не заявляются.
QtCharts уже доступен в PySide6 Addons; новой зависимости нет. Charts используют
прежние metrics DTO + typed WeekFacts/AttendanceSummary, не сохраняют агрегаты
и не делают педагогических интерпретаций.

Ниже сохранены ADR предыдущих фаз; текущую границу задают ADR-035–038.


## ADR-033 — Workspace преподавателя без изменения учебных фактов

**Статус:** ACCEPTED для реализации; пользовательская UX-приёмка ожидается. **Дата:** 2026-10-03. **Основание:** отдельное задание Phase 6.5 §§1–23, ТЗ §§9/18, существующие application/domain contracts Phase 2–6.

Рабочая единица UI — CourseOffering: sidebar Обзор/Группы/Вопросы, группа содержит Журнал/Студенты/Работы/Занятия/Аналитика; header общий, контекст сохраняется в сессии. Карточка студента — крупный details dialog с пятью вкладками. Enter/double-click ячейки создаёт новую Attempt через компактную форму; история в context menu. Application определяет номер и прежние progress/Grade guards; отмена не создаёт Work. `✓²/✓³` сохраняют прежний count записей, а не вводят новое правило first-pass. Domain/schema/analytics formulas не меняются.

Закреплённая колонка — два стандартных QTableView, общий model/selection, синхронные scroll/resize по [официальному Qt Frozen Column Example](https://doc.qt.io/qt-6/qtwidgets-itemviews-frozencolumn-example.html). QSS/fonts/spacing централизованы без стороннего UI framework. File IO передано QRunnable/QThreadPool; результаты queued в GUI, stale selections/generations игнорируются, pool ожидается до runtime.close. Attendance batch атомарный и сохраняет комментарии; historical reads доступны после archive. Аналитика lazy, текущие измерения не требуют отдельного worker/cache.

**Последствия:** глобальный раздел работ заменён вкладкой группы; numeric indices в старых helpers обновлены. Контекст пока не сохраняется через restart, кроме существующего active term. Новых domain entities или миграции 0006 нет. Ручной выбор preferred tab/width/Grade раскрытия остаётся предметом UX-приёмки, не причиной начинать следующую фазу.

## ADR-034 — Portable Windows GUI build

**Статус:** ACCEPTED для реализации. **Дата:** 2026-10-03. **Основание:** отдельное задание Phase 6.5 §§24–26/29, системный Python 3.12.10 x64, существующие pins Qt/SQLAlchemy/Alembic, [PyInstaller 6.22.3](https://pypi.org/project/pyinstaller/), [spec documentation](https://pyinstaller.org/en/stable/spec-files.html).

Выбран PyInstaller GUI onedir (`dist/Studium/Studium.exe` + `_internal`), `console=False`, `upx=False`, traceback bootloader window отключён. Это сохраняет явную portable папку и физические Alembic Python/SQL resources, не требует runtime установки Python и не добавляет новый UI framework. PyInstaller и build transitive pins отделены в `requirements-build.lock` и optional `[build]`; production runtime pins и dev lock не изменены. Windows/PySide6/QtPDF resources включаются штатными hooks и explicit hidden imports. User data по прежней policy находится в `%LOCALAPPDATA%\Studium`.

Первый smoke выявил чужую ICU DLL из PATH окружения сборщика. Build script ограничивает PATH Python/System32/Windows и использует `--clean`; исправленный комплект проверен реальным запуском exe. Путь временного normal profile должен быть вне Git checkout: существующая защита unsafe_data_directory продолжает действовать. Test roots синтетические; миграции применяет сам exe.

**Последствия:** переносить весь onedir комплект; build/dist остаются игнорируемыми, sources/spec/lock отслеживаются. Installer, automatic updates и code signing не входят в задание. Изменение системного Python или runtime версии Qt для сборки не потребовалось.

Дата исходного обзора: 29 сентября 2026. Источники: ТЗ v0.1, `README_START_HERE.md`, `CODEX_FIRST_PROMPT.md` и четыре схемы. `ACCEPTED` означает принятое правило для текущей основы, `OPEN` — вопрос без полностью утверждённого контракта, `RESOLVED` — вопрос с принятым решением, `SUPERSEDED` — решение, заменённое новым с указанием ID. Новые решения получают устойчивый ID, дату, основания и последствия; исходники не переписываются молча.

## ADR-001 — Узкая граница Phase 0

**Статус:** ACCEPTED. **Дата:** 2026-09-29.

§16 ТЗ включает shell, SQLite, модели и тестовую инфраструктуру в Phase 0. Текущее задание запрещает начинать функционал до её завершения, а первый промпт прямо исключает приложение, backend и доменную реализацию. Применяем первый промпт как уточнение Phase 0: только чтение, документация, структура и Git. Код/миграции начинаются в Phase 1 или позже по отдельному заданию; само завершение Phase 0 их не разрешает.

## ADR-002 — Последовательность Phase 0–10

**Статус:** SUPERSEDED в части стека/структуры/фаз, ADR-014. Ниже — историческое решение.  **Дата:** 2026-09-29.

Первый промпт явно задаёт фазы и запрещает переход без задания; §20 ТЗ располагает Android workflow после sync, §16 — раньше. Рабочий roadmap следует точному списку первого промпта: Phase 6 Android UX, Phase 7 server, Phase 8 sync, Phase 9 analytics, Phase 10 AI. Android до sync работает локально. Продуктовые версии ТЗ сохраняются как ориентиры, не заменяют фазовые ограничения.

## ADR-003 — Структура без реализации

**Статус:** SUPERSEDED в части стека/структуры/фаз, ADR-014. Ниже — историческое решение.  **Дата:** 2026-09-29.

По §17 ТЗ и первому промпту резервируем `apps/studium_app`, `services/api`, `packages/domain`, `packages/database`, `packages/sync`, `infra`, `scripts`, `tests`. README в каждом каталоге сохраняет структуру в Git и объясняет границу. Не создаём фиктивные пакеты, CI, зависимости или пустую production-иерархию. Сервер расположен в `services/api`; `backend/app` в §10.2 описывает будущие модули, а не второй backend. Репозиторий инициализируется локально с веткой `main`; remote/публикация не настраиваются.

## ADR-004 — Стек и независимый локальный MVP

**Статус:** SUPERSEDED в части стека/структуры/фаз, ADR-014. Ниже — историческое решение.  **Дата:** 2026-09-29.

По §§10–12 и первому промпту: Flutter/Dart, Windows и Android, offline-first SQLite; позднее FastAPI/PostgreSQL и отдельный sync-слой. Локальная БД хранит рабочие данные. ORM/версии открыты. Локальные сценарии не требуют сервера и AI; файлы читаются через AttachmentService, содержимое вне БД. Границы пакетов документированы до реализации.

## ADR-005 — История, терминология и выводы

**Статус:** ACCEPTED. **Дата:** 2026-09-29.

По §§3–7, 13 и первому промпту сохраняем Assessment/CourseOffering и весь минимальный домен; не вводим Assignment/TeachingGroup. Новая попытка — новая Attempt; StudentWork не заменяет её историю. Переписка хранится отдельно от StudentNote. AIInsight — отдельный производный объект с evidence и версиями; автоматическая перезапись фактов/оценок запрещена. Детали Grade и коррекций остаются OPEN.

## ADR-006 — Исходники и рабочая документация

**Статус:** ACCEPTED. **Дата:** 2026-09-29.

Исходные материалы сохранены побайтно; контрольные суммы внесены в done.md. `docs/` развивает их с указанием разделов-источников, требований и решений. Изображения внутри DOCX совпадают с четырьмя файлами assets по SHA-256, поэтому изучены оригиналы схем. Для enum используем приложение A, для полей — подробную таблицу §7, отмечая сокращения рисунков. Пользовательские данные/секреты/БД/сборки исключаются из Git; assets и ТЗ остаются доступны для отслеживания.

## OPEN-001 — Контракт Grade

**Статус:** RESOLVED, 2026-09-30. **Решение:** ADR-009. Контракт Grade перенесён и проверен Python unit/database/repository tests в Phase 1R (ADR-015).

Grade обязателен в минимальном домене первого промпта и упомянут в §§7.1/9.2, но его нет в таблице §7 и ER. Что хранит самостоятельная Grade, к чему относится и как отличается от Attempt.score/StudentWork.final_score? Консервативно сохраняем термин и место в модели, не придумываем поля и не удаляем сущность.

## OPEN-002 — Агрегация StudentWork и показателей Attempt

**Статус:** OPEN только в остаточной части manual overrides/correction audit. Локальная проекция решена ADR-010/ADR-015; first-pass/attempts/score/deadline/evidence aggregation — ADR-031/ADR-032, 2026-10-02. Согласованные формулы опубликованы в [analytics.md](analytics.md). Остаток требует отдельного задания, не блокирует Phase 6.

§§4.5–4.6, 6 определяют результаты/показатели, но не полную таблицу переходов: SCORED, COMMENT_ONLY, REJECTED после ACCEPTED, manual override, исправления и порядок occurred_at против attempt_no. Не задано, какие события считаются содержательными для first_try_success/attempt_count, как выбирать final_score, считать days_late и последнюю переделку. Сохраняем исходные enum и определения первой ACCEPTED/числа NEEDS_REVISION; не предполагаем «последняя запись всегда побеждает».

## OPEN-003 — Полный контракт QuestionCase и сообщений

**Статус:** RESOLVED, 2026-10-01. **Решение:** ADR-027/ADR-029; полный контракт student-owned QuestionCase отдельного задания Phase 5. Ниже сохранена исходная постановка. Внешние неизвестные участники/transport adapters не объявляются реализованными.

§5 допускает кейс из нескольких сообщений; первый промпт требует связи с CourseOffering/Attempt. §7/ER содержат лишь question_message_id/answer_message_id, Student и таблицы Topic/Skill/Assessment. Как связать все сообщения, поток и попытку, автора с ThreadParticipant, reply-to и подтверждение ответа? Каковы условия ANSWERED/RESOLVED/NEEDS_FOLLOWUP и OPEN-фильтра? Сохраняем полный набор требуемых связей как контракт, не вводим новые именованные таблицы молча.

## OPEN-004 — Тематические связи работы и занятия

**Статус:** OPEN в остаточной части. Тематические связи Phase 3 решены ADR-019/021 (2026-10-01). **Решить остаток:** отдельное задание на прямые Lesson → Skill / выданную Assessment. Phase 6 использует только существующие явные связи; LessonSkill не выводится из TopicSkill, соответствующий показатель неприменим.

§4.5 делает AssessmentItem опциональным, но §7/ER связывают AssessmentTopicSkill только с item_id; §18 требует связи самой ДЗ с Topic/Skill. §4.4 требует Lesson → выданные работы, §4.3 — навыки у занятий, явных связей в модели нет. Как выражать работу без items и её темы, Lesson/Assessment/Skill? Пока фиксируем требования, не создаём фиктивный item и не вводим дублирующий Assignment.

Phase 3 реализует AssessmentTopic/Skill, AssessmentItemTopic/Skill, LessonTopic и TopicSkill. Новое задание определяет фактическое занятие и его темы, но не просит прямые LessonSkill/LessonAssessment. TopicSkill не подменяет факт отработки навыка на занятии. Консервативно не вводим эти дополнительные факты и не объявляем весь OPEN-004 RESOLVED. Принятые контракты Phase 3 не заблокированы этим остатком.

## OPEN-005 — Версии будущего server/mobile stack

**Статус:** OPEN в части будущих платформ. **Решить:** Phase 7 — FastAPI/PostgreSQL, Phase 9 — mobile stack.

Локальный toolchain/ORM/migrations/test stack решён ADR-014/ADR-015: системный Python 3.12.10, PySide6/SQLAlchemy/Alembic и совместимые stable versions установлены, pyproject/lock проверены. Исторический SDK/codegen blocker partial Phase 1 больше не относится к текущей архитектуре. Версии серверных и мобильных зависимостей из исходного вопроса выбираются в их фазах; они сейчас не устанавливаются.

## OPEN-006 — Лицензия и удалённый репозиторий

**Статус:** RESOLVED решением владельца для независимого Studium-public:
COLOSSAL-maksik/Studium-public, main; All rights reserved без открытой лицензии,
с сохранением third-party licenses. Права на все 310 проектных материалов
подтверждены владельцем. Публикацию source bundle выполняет владелец;
Windows release/manual acceptance остаётся отдельно. Ниже исходная постановка.

§20 требует определить license/private repo; тип лицензии, remote, владелец и разрешение публикации не заданы. Локальная инициализация не определяет видимость будущего remote. Не добавляем произвольную лицензию и не публикуем материалы.

## OPEN-007 — Ссылки Attachment и восстановление файлов

**Статус:** OPEN в остаточной части. Локальные storage/Attempt ownership/integrity/missing-file/import recovery решены ADR-023–ADR-025 (2026-10-01). **Решить остаток:** дополнительные владельцы в своих фазах, серверный storage/sync в Phase 7–8. Local ZIP backup/verify/restore реализованы в merged , контракт — [Iteration 5B](iteration5b-backup-recovery.md). Purge/retention/protection, audit и будущий remote storage остаются открытыми; manual recovery acceptance не закрыта.

§§7/12 предлагают owner_type/owner_id либо отдельную таблицу связей для нескольких владельцев. Как обеспечить целостность полиморфной ссылки, допустимые владельцы, дедупликацию без потери связей и согласованность записи файла/БД после сбоя? Каковы сроки восстановления/garbage collection, backup содержимого и кэшей? Прежнее ограничение до Phase 4: один Attachment описывает файл со стабильным ID и хэшем; bytes вне БД/репозитория, automatic physical delete отсутствует. Теперь локальный контракт разделён на FileAsset/AttemptAttachment; local backup реализован в Iteration 5B, GC/purge и дальнейшие owners/remote storage остаются отдельными вопросами.

## OPEN-008 — История Enrollment и состав назначения

**Статус:** RESOLVED, 2026-09-30. **Решение:** ADR-012. Контекст, интервалы membership и уникальность StudentWork определены и проверены SQLite-тестами.

§4.2 обещает историю, §7 указывает enrolled_at/status без списка статусов и конца интервала. Как представить выход/повторное зачисление, несколько активных Enrollment и назначение Assessment при изменении состава? Уникальна ли тройка term/course/group для CourseOffering, если несколько преподавателей? Не сводим историю к полю группы Student и не вводим жёсткую уникальность без решения.

## OPEN-009 — Календарные даты и учебный часовой пояс

**Статус:** OPEN в остаточной части учебного timezone/date-only deadline и сопоставления UTC Enrollment с днём Lesson. UTC/LocalDate решены ADR-008/ADR-015, desktop-ввод — ADR-017, сравнение точных сроков/сдач и calendar_days_late с явно переданным reporting timezone — ADR-032 (2026-10-02). Часы задержки не выдаются за учебные календарные дни; переносы сроков без audit не реконструируются.

§7 задаёт UTC временных полей, но Lesson.date и starts_at/ends_at периода могут обозначать календарные даты. Как хранить date-only, время срока, пояс учебного контекста и показывать их при смене устройства/пояса? Для событий используем правило UTC из ТЗ; календарные значения и округление days_late не преобразуем произвольно.

## OPEN-010 — Ownership, ревизии и номера попыток при sync

**Статус:** OPEN. **Решить:** Phase 1R — локальные UUID/revisions готовы; Phase 2 — локальная конкуренция attempt_no (ADR-018); Phase 7 — identity; Phase 8 — конфликты устройств.

§7 называет version/revision, teacher_owner_id/owner_user_id; §10 — single-user token/local account; §11 — server_revision. Не определены область и тип ревизий, локальный владелец, границы нескольких аккаунтов. Два устройства могут создать одинаковый attempt_no при уникальных UUID. Нужно сохранить обе Attempt и согласовать порядок/перенумерацию без потери истории. Пока не выбираем алгоритм sync; UUID и отдельный слой сохранены.

## OPEN-011 — Исправления, audit, удаление и backup

**Статус:** OPEN в остаточной части. **Уточнено:** 2026-10-10. Immutable facts/soft delete и local ZIP backup/verify/restore реализованы; backup часть подтверждена merged  и [контрактом 5B](iteration5b-backup-recovery.md). Corrections/audit, purge/retention/protection и прежние content/deadline revisions остаются открытыми. ZIP не зашифрован, restore требует matching app/schema и отдельного пустого root; manual recovery acceptance открыта.

§3 говорит об истории попыток/ответов/заметок/результатов, §4.6 допускает новую запись или audit trail, §14 требует удаления данных студента и AuditEvent. Как исправлять неверный факт, различать cancel/archive/soft delete и окончательное удаление, учитывать копии/вложения и защищать локальное хранилище/backup? Консервативно не теряем историю и не каскадно удаляем попытки; этот подход не заменяет будущую согласованную процедуру удаления данных.

## OPEN-012 — Минимальная аналитика для локального MVP

**Статус:** RESOLVED, 2026-10-02. **Решение:** отдельное задание Phase 6, ADR-031/ADR-032 и [analytics.md](analytics.md): локальные Student/Group/Assessment/Topic/Skill/Question показатели, динамика известных событий, N/A и минимальный UI реализованы и проверены. Ниже сохранена исходная постановка; педагогические интерпретации не входят в согласованный объём.

§§1/13/18 включают базовую статистику в локальный MVP; первый промпт выделяет analytics в Phase 9. Где разместить минимальную долю сданных работ и число вопросов по темам (AC-10)? Счётчик попыток и текущий статус необходимы матрице Phase 2; dashboards относятся к Phase 6. Остальную аналитику не добавляем заранее и AC-10 не объявляем выполненной без отдельного согласования.

## OPEN-013 — Область идемпотентности внешних сообщений

**Статус:** RESOLVED как data contract, 2026-10-01. **Решение:** ADR-028. Live provider normalization/import требует отдельного задания. Ниже сохранена исходная постановка.

§7.1 задаёт external_message_id + channel как ключ повторного импорта, но не уточняет account/thread/provider scope, отсутствие ID при copy/paste и разные способы Telegram-доступа. Нужно определить область внешнего ID и поведение при повторном ручном вводе, не теряя разные реальные сообщения. Исходное требование идемпотентности сохраняем; не выдаём хэш текста за универсальную идентичность сообщения.

## Как закрывать OPEN

Для зависимой задачи оформить ответ пользователя либо обоснованное решение в рамках его задания, примеры и последствия для данных/проверок; добавить ADR и обновить соответствующий документ. Сохранить историю OPEN с ссылкой на решение, не стирать запись. Вопросы поздних фаз не блокируют завершение Phase 0.

## ADR-007 — Уточнённый объём Phase 1 и blocker SDK

**Статус:** SUPERSEDED в части стека/структуры/фаз, ADR-014. Ниже — историческое решение.  **Дата:** 2026-09-30. **Основание:** отдельное задание пользователя на Phase 1.

В этой фазе ядро ограничено AcademicTerm, Course, StudentGroup, CourseOffering, Student, Enrollment, Assessment, StudentWork, Attempt, Grade. Topic/Skill, занятия, файлы, Q&A, аналитика, сервер, sync, AI и auth не реализуются. Пользователь разрешил workspace и только минимальный Flutter bootstrap уже в Phase 1; production UI остаётся Phase 2. Это уточняет прежние более широкие задачи todo и положение shell в roadmap, не меняя выполненную Phase 0.

Flutter и Dart не найдены в PATH и проверенных типовых каталогах. Команды --version/doctor не запускаются. Стандартная установка Visual Studio через vswhere не обнаружена; Windows toolchain пока не подтверждён. SDK/toolchain самостоятельно не устанавливаются. Подготовлены чистые Dart-источники, repository interfaces и SQL-исходник для Drift; Flutter-проект, конкретные Drift repositories, code generation, production MigrationStrategy и Dart/Flutter проверки остаются blocker. Phase 1 не считается завершённой.

## ADR-008 — UUID, UTC и календарная дата

**Статус:** ACCEPTED. **Дата:** 2026-09-30. **Уточняет:** часть OPEN-009/OPEN-010.


AcademicTerm.startsOn/endsOn — LocalDate, в БД starts_on/ends_on как YYYY-MM-DD с проверкой действительной даты и интервала. Исходные starts_at/ends_at ТЗ уточнены как календарные границы периода. Assessment.issuedAt/dueAt и Attempt.occurredAt — абсолютные UTC instants. LocalDate не преобразуется в полночь устройства. Вопросы часового пояса занятий, due date UX, days_late и server revisions остаются OPEN.

## ADR-009 — Консервативный Grade

**Статус:** ACCEPTED. **Дата:** 2026-09-30. **Закрывает:** OPEN-001.

Grade — отдельный immutable факт с UUID/metadata и attemptId; не более одной Grade на конкретную Attempt, включая soft-deleted записи. Варианты: PASS_FAIL (passed true/false), NUMERIC (score и необязательный maxScore), TRADITIONAL (непустой label, например «5» или «отлично»). Числа конечны, score >= 0, заданный maxScore > 0, score <= maxScore.

Attempt сохраняет собственные исходные score/maxScore. Числовая Grade обязана совпадать с ними, а не менять их; maxScore Attempt остаётся снимком, даже если максимум Assessment изменится. PASS_FAIL true соответствует ACCEPTED, false — NEEDS_REVISION/REJECTED. Текстовая Grade не преобразуется в число и не меняет результат Attempt. Новый исправленный результат требует новой Attempt; изменение первичных полей Grade/Attempt запрещено SQL triggers. Это не универсальная grading engine.

## ADR-010 — Восстанавливаемое состояние StudentWork

**Статус:** ACCEPTED. **Дата:** 2026-09-30. **Уточняет:** часть OPEN-002.

StudentWork содержит только устойчивую связь Student + Assessment и metadata; столбцов status/final_score в v1 нет. StudentWorkProgress вычисляется из активных Attempt по attemptNo, а не по occurredAt. Проверяются принадлежность истории, уникальность ID/номера; soft-deleted факты сохраняются, но не участвуют в текущем результате.

Начальное состояние NOT_STARTED. PRESENTED → SUBMITTED; NEEDS_REVISION → REVISION_REQUIRED; ACCEPTED → ACCEPTED. Эти три события заменяют текущий балл своим score, включая null. SCORED обновляет балл, сохраняет прежний статус, а при NOT_STARTED даёт SUBMITTED. REJECTED и COMMENT_ONLY не меняют статус/балл. attemptCount — число всех активных фактов, включая эти два нейтральных результата. Например ACCEPTED(8) → REJECTED(0) → COMMENT_ONLY остаётся ACCEPTED(8), count=3; SCORED(10) без отдельного решения о зачёте остаётся SUBMITTED.

Термины запроса presented/revision_required/passed/rejected отображены на документированные PRESENTED/NEEDS_REVISION/ACCEPTED/REJECTED. Python-поля Attempt: attempt_no, occurred_at, result, comment, score, max_score; новые параллельные status/presentedAt не вводятся. MISSED/EXEMPT/CANCELLED сохранены в enum, но не выдумываются из имеющихся Attempt; ручные overrides, first_try_success и формулы просрочки ещё не реализованы. Поэтому OPEN-002 не закрыт полностью.

## ADR-011 — Локальные revisions и неизменяемые факты

**Статус:** ACCEPTED. **Дата:** 2026-09-30. **Уточняет:** часть OPEN-010/OPEN-011.

Начальная локальная revision=1; изменение требует ровно следующую revision и неубывающий updatedAt. ID и createdAt не меняются. deletedAt nullable, при удалении находится между createdAt и updatedAt. Интерфейсы репозиториев требуют expectedRevision для compare-and-swap; SQLAlchemy реализация с compare-and-swap проверена в Phase 1R (ADR-015). Не создаются sync engine или conflict resolution.

Attempt допускает только изменение metadata, не результата/номера/балла/комментария/учебной связи. UNIQUE(student_work_id, attempt_no) действует также на удалённую историю; новый номер больше любого прежнего. StudentWork/Attempt/Grade нельзя физически удалить через обычный SQL. Исторический контекст CourseOffering, Assessment.offeringId, Enrollment.studentId/offeringId/enrolledAt также защищён от подмены. Общая политика окончательного удаления, audit, backup и прав остаётся OPEN-011; локальные triggers её не заменяют.

## ADR-012 — Membership и идентичность работы

**Статус:** ACCEPTED. **Дата:** 2026-09-30. **Закрывает:** OPEN-008.

Enrollment принадлежит паре Student + CourseOffering, а не только StudentGroup. ACTIVE имеет endedAt=null, WITHDRAWN/COMPLETED — endedAt >= enrolledAt. Для не удалённых записей интервалы [enrolledAt, endedAt) не пересекаются; partial UNIQUE запрещает два ACTIVE membership в одном контексте. Повторное зачисление после завершения создаёт новый Enrollment. В разных offerings студент может состоять одновременно. Тройка term/course/group намеренно не объявлена уникальной: несколько отдельных потоков сохраняют разные UUID без преждевременной модели владельцев.

StudentWork можно создать для студента с активным membership в offering соответствующей Assessment. Это явное назначение, а не автоматическое копирование меняющегося состава группы. UNIQUE(student_id, assessment_id) сохраняет одну логическую работу также после soft delete; история не дублируется при повторном insert. Завершение membership не удаляет существующие работы и попытки. Дальнейшие правила массового назначения/восстановления определяются отдельным сценарием, не новым журналом статусов.

## ADR-013 — Drift schema source и граница проверки

**Статус:** SUPERSEDED в части стека/структуры/фаз, ADR-014. Ниже — историческое решение.  **Дата:** 2026-09-30. **Уточняет:** часть OPEN-005.

SQLite через Drift выбран пользователем. Схема написана в .drift SQL-файле: Drift официально поддерживает SQL-таблицы, индексы и triggers. Подготовлен контракт schemaVersion=1, onCreate/createAll, beforeOpen с foreign_keys=ON и будущим явным onUpgrade. Поскольку SDK отсутствует, не добавлены неподтверждённые версии drift/drift_dev/build_runner/test и не созданы ссылки на отсутствующий database.g.dart. Minimum SDK доменного pubspec — Dart 3.0 из-за используемых final/interface class; это языковое ограничение исходников, не утверждение об установленном SDK.

Python stdlib sqlite3 используется только как независимый тестовый driver точного DDL на временных файлах. Это не реализация repository layer, не production мигратор и не замена Flutter/Drift. SQL-проверки не подтверждают Drift analyzer/code generation, Dart compilation, formatter или Flutter запуск. После появления SDK обязательно выбрать совместимые стабильные зависимости через pub, создать настоящий Flutter workspace, сгенерировать API, реализовать Drift repositories и выполнить отдельные Dart/Drift/Flutter tests.

Первичные технические источники: [Drift SQL files](https://drift.simonbinder.eu/sql_api/drift_files/), [Drift setup](https://drift.simonbinder.eu/setup/), [Migration API](https://drift.simonbinder.eu/migrations/api/), [SQLite foreign keys](https://www.sqlite.org/foreignkeys.html).

## Исторический остаток OPEN после partial Phase 1

Закрыты только OPEN-001 и OPEN-008. OPEN-002, OPEN-005, OPEN-009, OPEN-010, OPEN-011 получили решения для локального ядра, но остаются OPEN в нерешённой части. OPEN-003, OPEN-004, OPEN-006, OPEN-007, OPEN-012, OPEN-013 не закрывались: они относятся к последующим функциям, публикации либо более широкой приёмке.

## ADR-014 — Python / PySide6, Windows-first и Phase 1R

**Статус:** ACCEPTED. **Дата:** 2026-09-30. **Основание:** отдельное задание пользователя Phase 1R. **Заменяет:** выбор клиентского стека ADR-004 и ADR-013, клиентскую структуру ADR-003 и порядок поздних фаз ADR-002.

Studium переходит с Flutter + Dart + Drift shared client на Python + PySide6 Windows-first desktop application. Это осознанное архитектурное решение. Windows — основное рабочее устройство; desktop workflow с таблицами, карточками, файлами и drag-and-drop важнее общего UI-кода с Android. Python подходит будущим analytics/OCR/Vision/AI и серверу FastAPI. Android позднее получает отдельный специализированный клиент.

Локальная БД — SQLite; persistence — SQLAlchemy 2.x; production migrations — Alembic; tests — pytest; formatting/linting — Ruff. Pydantic применяется только при реальной потребности в boundary DTO/contracts. Domain остаётся чистым Python и не зависит от UI, ORM, SQLite implementation или сервера. Смысл десяти сущностей, UUID/UTC/LocalDate, metadata, Grade, истории Attempt и StudentWorkProgress из ADR-008–ADR-012 сохраняется.


До реализации требуется проверить системный Python и совместимость зависимостей. Внутренний embedded Python Codex не может быть production interpreter Studium. Если подходящего Python нет, работа ограничивается документацией и регистрацией blocker; новая системная установка требует разрешения пользователя.

## ADR-015 — Перенос local foundation и production migrations

**Статус:** ACCEPTED. **Дата:** 2026-09-30. **Основание:** реализованная и проверенная Phase 1R. **Уточняет:** ADR-008–ADR-012, локальную часть OPEN-005/009/010/011.

Проверен пользовательский системный Python 3.12.10 x64, SQLite 3.49.1; локальный `.venv` создан им. Stable PyPI metadata и Windows wheels подтвердили совместимость PySide6 6.11.2, SQLAlchemy 2.1.1, Alembic 1.20.0, pytest 9.1.1, pytest-cov 7.1.0 и Ruff 0.16.9. Build backend — setuptools 84.0.0. Прямые pins в pyproject, 18 runtime/dev transitives в requirements-dev.lock. Pydantic и дополнительный type checker сейчас не нужны.

Десять Python frozen dataclasses сохраняют доменную семантику. Имена полей используют snake_case из модели ТЗ: occurred_at/result/comment, attempt_no, max_score. UUID v4 — uuid.uuid4, UTC — timezone-aware UtcInstant с точным integer microsecond conversion, LocalDate не является timestamp. Grade/проекция/membership/immutable facts из ADR-009–ADR-012 перенесены без нового grading/status engine.

SQLAlchemy repositories реализуют domain Protocol; application и presentation не используют ORM Session. Каждая mutation транзакционна; append Attempt + optional Grade атомарен. expected_revision проверяется в SQL UPDATE, errors переводятся в RepositoryError без SQL parameters. StudentWork не хранит status/final_score.

Alembic revision `0001_local_core` содержит immutable SQL snapshot десяти production tables, indexes, checks, FK и triggers; этот ресурс упаковывается с Python package. create_all не используется. Connection policy: foreign_keys=ON до BEGIN на каждом connection, sqlite3 autocommit=False, busy_timeout=5000. WAL для локального desktop file database сохраняет параллельное чтение при коротких записях; durability по умолчанию не ослабляется. Можно явно выбрать wal=False. Backup/network storage policy остаётся OPEN-011.

Fresh migration, rollback при ошибке DDL, идемпотентный upgrade/reopen, unknown/unversioned rejection и additive test-only v1 → v2 проверены. Следующие production revisions требуют down_revision и preservation tests; SQLite batch migrations должны вручную сохранять triggers/checks/indexes. Destructive downgrade initial migration запрещён.

Подготовленные 16 domain scenarios и 25 SQL contracts перенесены на pytest production implementation; дополнительные tests проверяют repositories, atomic rollback, revisions, architecture и offscreen Qt startup. Старые apps/packages удалены из активной структуры; история остаётся в checkpoint, архивных копий нет. Phase 2 не реализована.

Технические первичные источники: [Qt for Python](https://doc.qt.io/qtforpython-6/gettingstarted.html), [SQLAlchemy SQLite transactions/FK](https://docs.sqlalchemy.org/en/21/dialects/sqlite.html), [Alembic cookbook](https://alembic.sqlalchemy.org/en/latest/cookbook.html), [PyPI metadata](https://pypi.org/).

## Актуальный остаток OPEN после Phase 1R

RESOLVED: OPEN-001 Grade, OPEN-008 Enrollment. OPEN: 002/003/004/005/006/007/009/010/011/012/013. Их локальные части решены только в описанном объёме; analytics/UX, Q&A/links/files, future stack versions, публикация, timezone, ownership/sync и audit/purge/backup не закрыты искусственно.

## ADR-016 — Windows MVP UI через application boundary

**Статус:** ACCEPTED. **Дата:** 2026-10-01. **Основание:** отдельное задание Phase 2 после commit `[историческая ссылка опущена]`. **Уточняет:** границу UI ADR-014/ADR-015; Phase 0 и Phase 1R завершены.

Стандартные PySide6 widgets/layouts/dialogs и read-only QAbstractTableModel/QTableView реализуют Обзор, Группы, Работы, Настройки. Карточка студента имеет только Обзор/Работы. Центральный messages.py переводит enum без изменения storage values. Темы, файлы, Q&A, аналитика и mobile не создаются как активные разделы; Phase 3 не разрешена.

StudiumService покрывает CRUD справочников, Enrollment, Assessment, get/create StudentWork, append/history и matrix. UI получает frozen domain values и query DTO, не ORM objects. Repositories/Transaction/Preferences — application ports; общий unit of work обеспечивает atomic Student + Enrollment и snapshot queries. Composition root с ORM находится вне presentation. Не вводится CQRS/widget framework, новые dependencies не нужны. Schema v1 и первичные правила прогресса не меняются.

Matrix query использует bulk reads и chunked UUID filters, без запроса на каждую ячейку. 25 студентов × 30 работ проверяются при не более 10 SQL SELECT; это проверка стратегии запросов, не обещание SLA для любого объёма. Сортировка/поиск по ФИО — Qt proxy, статус читается текстом и символом. UX-приёмка, включая DPI и рабочие размеры окна, перечислена отдельно в ui-navigation.md.

Технические источники: [Qt table model](https://doc.qt.io/qtforpython-6/PySide6/QtCore/QAbstractTableModel.html), [Qt sort/filter proxy](https://doc.qt.io/qtforpython-6/PySide6/QtCore/QSortFilterProxyModel.html).

## ADR-017 — User data, first run и локальные даты UI

**Статус:** ACCEPTED. **Дата:** 2026-10-01. **Основание:** Phase 2 §§3/16–18/20. **Уточняет:** локальную часть OPEN-009/OPEN-011, не закрывает их полностью.

Обычный Windows-запуск использует `%LOCALAPPDATA%/Studium/studium.sqlite`; резервный путь при отсутствующем LOCALAPPDATA — home/AppData/Local/Studium. user_data.py централизует разрешение пути и отвергает обычный data directory внутри Git. Composition root создаёт папку и применяет Alembic перед MainWindow. Нет reset/create_all; исходная миграция не меняется. Dev path задаётся явно `--data-dir`; tests/preview всегда используют temporary databases. Settings показывают путь, application/schema/Python/Qt versions. Admin migration CLI сохранён.

Выбранный период — локальная пользовательская настройка в preferences.json, сохранение atomic replace; это не domain active flag. Без корректной настройки выбирается последний неархивный период. Новый период становится выбранным. Повреждение настройки не уничтожает БД. Backup/purge/audit/защита остаются OPEN-011.

Начало/конец AcademicTerm — LocalDate. Абсолютные issued_at/due_at/occurred_at вводятся и показываются в текущем часовом поясе Windows, хранятся в UTC. Пустая дата выдачи новой работы означает время создания; при редактировании — прежнее issued_at. Deadline имеет дату и время, отдельный date-only режим не добавлен. Учебный timezone, его смена, Lesson.date и days_late остаются OPEN-009.

## ADR-018 — Безопасная новая Attempt и удаление из UI

**Статус:** ACCEPTED. **Дата:** 2026-10-01. **Основание:** Phase 2 §§5–13/14. **Уточняет:** ADR-009–ADR-012; локальную часть OPEN-002/010/011.

StudentWork создаётся сервисом при открытии пары Student/Assessment, существующая запись переиспользуется. UI не задаёт status и attempt_no. Следующий номер — max всей истории, включая deleted attempts, + 1. Чтение завершается до write transaction; при UNIQUE/monotonic-number conflict сервис перечитывает и повторяет append, максимум 5 раз. Реальная гонка двух writers с одинаковым исходным номером проверена тестом. Старые UUID/факты не меняются; sync двух устройств этим не решён.

Attempt и optional Grade сохраняются атомарно. Сервис проверяет active context/student/Enrollment. Максимум по умолчанию берётся из Assessment и сохраняется в Attempt как снимок; пользователь может его уточнить. Numeric Grade повторяет исходные score/max_score; pass/fail согласована с AttemptResult; traditional label не вычисляет балл или зачёт. Старые попытки доступны только для чтения; полноценное исправление ошибочных фактов/override/audit остаётся OPEN-011/OPEN-002.

«Завершить участие» переводит только текущий Enrollment в WITHDRAWN с ended_at и сохраняет его историю; повторное зачисление создаёт новый Enrollment. «Скрыть во всех дисциплинах» в карточке студента выполняет soft delete Student. Группа, дисциплина и Assessment также удаляются только через soft delete, без cascade. UI восстановления/архива/окончательного удаления не создаётся в Phase 2. Скрытие родителя исключает его контекст из активного выбора, факты остаются в БД.

Матрица вычисляет исходную ADR-010 projection: REJECTED/COMMENT_ONLY сохраняют предыдущий итог, SCORED сам по себе не означает зачёт. `✓²` означает две активные записи истории, включая комментарии; новая аналитическая first_try_success формула не вводится. Количество студентов группы — уникальные активные студенты её дисциплин выбранного периода. Desktop create_offering переиспользует активную тройку term/course/group; DB не получает преждевременного UNIQUE этой тройки.

## Остаток OPEN после Phase 2

Ни один полный OPEN не закрыт искусственно. RESOLVED остаются OPEN-001/008; OPEN остаются 002/003/004/005/006/007/009/010/011/012/013. Локальный data directory, ввод дат, UI delete и конкурентный attempt_no уточнены ADR-016–ADR-018; future analytics/overrides, Q&A, topics, files, stack versions, license/remote, учебный timezone, ownership/sync, audit/purge/backup и external idempotency требуют соответствующих будущих заданий.

## ADR-019 — Каталог содержания и фактическое занятие

**Статус:** ACCEPTED. **Дата:** 2026-10-01. **Основание:** отдельное задание Phase 3 §§1–6/18, ТЗ §§4.3–4.4/7. **Уточняет:** тематическую часть OPEN-004.

Topic и Skill принадлежат Course, имеют UUID/metadata, title, optional description и sort_order. Topic.parent_topic_id — nullable ссылка в той же дисциплине; self-reference и более длинные cycles запрещены application и recursive SQLite triggers. TopicSkill — отдельная many-to-many таблица с уникальной парой.

Lesson — фактически состоявшееся занятие CourseOffering, LocalDate lesson_date, optional title/notes. LessonTopic — явная связь реально пройденной темы. Используем разрешённую заданием простую many-to-many: coverage introduced/practiced/reviewed не является необходимым фактом Phase 3, а исходный COMPLETED мог бы смешать разбор материала с освоением студентом. Новый CoverageLevel enum/колонка не вводятся. Каталог не является syllabus, LessonTopic не выводится автоматически; TopicSkill не доказывает отработку каждого навыка на занятии. Факты не оценивают mastery.

## ADR-020 — Минимальная посещаемость и календарная дата

**Статус:** ACCEPTED. **Дата:** 2026-10-01. **Основание:** задание Phase 3 §§5/7/12, ТЗ §7 и приложение A. **Уточняет:** Lesson.date часть OPEN-009, сохраняя остаток.

Attendance связывает Lesson с explicit Enrollment того же CourseOffering, Student доступен через membership. PRESENT/ABSENT/LATE/EXCUSED/UNKNOWN сохраняют набор ТЗ, comment optional. Нет записи — «Не отмечено»; UNKNOWN — явно сохранённая неопределённость. UNIQUE пары плюс trigger запрещают две отметки одного Student на одном Lesson через разные Enrollment. Withdraw сохраняет историю; UI показывает интервалы, преподаватель выбирает конкретный.

Дата занятия — LocalDate YYYY-MM-DD, без скрытого времени/UTC-конверсии. Exact instant занятия/учебный timezone не определены, поэтому нельзя достоверно проверить UTC boundaries Enrollment по одному дню; автоматическую датовую принадлежность не вводим. Это консервативное ограничение, не подтверждение, что любое историческое участие покрывает выбранный день. Остаток OPEN-009 решается до такой автоматизации/date-only deadlines/days_late.

## ADR-021 — Работа, части работы и независимые тематические связи

**Статус:** ACCEPTED. **Дата:** 2026-10-01. **Основание:** задание Phase 3 §§8–12, ТЗ §§4.5–4.6/7/18. **Уточняет:** AssessmentItem часть OPEN-004.

AssessmentItem реализован, поскольку предусмотрен ТЗ: assessment_id, title, description, finite positive optional max_score, nonnegative sort_order и metadata. Части необязательны. Вместо неоднозначного AssessmentTopicSkill(item_id, topic_id?, skill_id?, weight) используем четыре независимые нормализованные связи AssessmentTopic/Skill и AssessmentItemTopic/Skill. UUID + FK/unique пары сохраняют идентичность; работа без items имеет собственные теги, фиктивный item не нужен.

Теги всей работы и каждой части вводятся независимо; ни наследования, ни автоматического объединения для аналитики нет. Максимумы частей не меняют максимум всей работы. Вес/competency framework не требуются заданием. AttemptItemResult отложен: каталог проверяемого содержания логически последователен без результата каждой задачи; Attempt продолжает хранить исходный результат всей работы. Этот результат не подтверждает отдельный Skill. Правила детализации оценок потребуют отдельного задания до analytics по задачам.

## ADR-022 — Additive migration и жизненный цикл учебных связей

**Статус:** ACCEPTED. **Дата:** 2026-10-01. **Основание:** Phase 3 §§12–15/20; ADR-015/016/018.

Revision `0002_learning_model` добавляет 11 таблиц, v1 не редактируется. Snapshot SQL содержит FK RESTRICT, pair UNIQUE, indexes, UUID/calendar/numeric/metadata checks, ownership/cycle/context/history triggers. Все сущности и links используют текущую convention timestamps/revision/deleted_at. Physical delete/downgrade с потерей истории не поддерживаются. Проверки копии populated v1 сохраняют все строки и SQL objects; fresh/reopen/FK и совпадение ORM metadata проверены.

Archive Topic архивирует поддерево атомарно, снизу вверх; raw SQL не может оставить активные подтемы у архивного parent. Старые links остаются доступны. Detach links — soft delete; повторный attach активной темы/навыка восстанавливает тот же UUID с новой revision. Это не журнал каждого прошлого attach/detach (OPEN-011/014). Изменения Lesson+topics, Assessment/Item tags и Item reorder транзакционны. UI передаёт исходные revisions и snapshots связей, конфликт откатывает операцию.

Новые services и frozen query DTO используют те же domain ports/UoW; UI не получает ORM. Добавлены только каталог/формы и вкладка «Занятия» существующей группы. Dependencies/lock/основной дизайн не меняются. Files/analytics/API/sync/AI/Phase 4 не реализуются.

## OPEN-014 — Версии содержания работы при будущей аналитике

**Статус:** RESOLVED, 2026-10-02. **Решение:** ADR-030, semantic lock после любой первой Attempt, application guards + SQL triggers. Состав/смысл Items, теги работы/частей и связанная семантика Topic/Skill защищены, включая архивированные Attempt. v5 фиксирует текущее содержание существующих работ; утраченные до v5 редакции не реконструируются. Переносы сроков/полный audit остаются OPEN-011. Ниже сохранена исходная постановка.

Phase 3 хранит изменяемый текущий каталог и mappings с revisions/tombstones, а Attempt фиксирует результат всей работы. Если преподаватель после сдачи изменил теги или состав Items, какой mapping должен определять содержание старой попытки? Нужны ли версии Assessment content, снимок на Attempt или явная ссылка на редакцию? Restore одной связи сохраняет UUID, но не все исторические интервалы активности. Консервативно не вычисляем mastery/Skill result из текущих тегов, не вводим score/weight/AttemptItemResult заранее. Перед будущей аналитикой выбрать воспроизводимый контракт evidence и хранения редакций.

## Остаток OPEN после Phase 3

RESOLVED остаются OPEN-001 и OPEN-008. OPEN: 002/003/004 (остаток)/005/006/007/009 (остаток)/010/011/012/013/014. Тематические контракты и Lesson.date уточнены ADR-019–ADR-022; весь OPEN-004 не закрыт из-за дополнительных связей исходного ТЗ. Другие OPEN не объявлены решёнными. Blockers разрешённой реализации Phase 3 отсутствуют.

## ADR-023 — Immutable FileAsset и конкретный владелец AttemptAttachment

**Статус:** ACCEPTED. **Дата:** 2026-10-01. **Основание:** задание Phase 4 §§1–5/9–12/24, ТЗ §§4.7/7/12. **Уточняет:** локальную часть OPEN-007.

Разделяем исходный обобщённый Attachment на FileAsset (физические immutable bytes) и AttemptAttachment (факт связи с конкретной Attempt). FileAsset: EntityMetadata, original_filename, relative storage_key, mime_type, size_bytes, sha256. AttemptAttachment: EntityMetadata, attempt_id/file_asset_id FK RESTRICT, nullable caption, sort_order, details_json (JSON object для metadata связи). UNIQUE пары действует и после detach. FileAsset не хранит student_id/owner_type/owner_id; Student и Assessment определяются через Attempt → StudentWork. Поля содержимого/ownership и физическое удаление защищены triggers. Revision/soft delete следуют ядру.

Новая версия — новый FileAsset и новый UUID; исходный файл не изменяется. Два импорта одинаковых bytes имеют разные ID/keys и одинаковый hash: dedup/CAS не вводим, поскольку простая компенсация не затрагивает shared content. Один asset технически может иметь несколько FK-связей; detach одной не затрагивает остальные. UI создаёт новые assets, не перемещает прежние между попытками. Отдельный будущий MessageAttachment → FileAsset добавится без изменения полей FileAsset; проверку «asset используется» нужно расширить на новые links в соответствующей миграции Phase 5. Lesson/другие владельцы из широкого ТЗ сейчас не реализуются.

Detach — soft delete link, его UUID/owner/metadata остаются читаемыми через include_detached. Повторное использование прежней пары не восстанавливает tombstone автоматически; новая предъявленная версия импортируется отдельно. Caption/order/details активной связи изменяемы с compare-and-swap; detached link неизменяем. Архивировать FileAsset можно только без активных links; bytes сохраняются. Немедленной physical cleanup из UI, GC и полной audit-истории редакций caption нет (OPEN-011).

## ADR-024 — Относительный storage и компенсируемый импорт

**Статус:** ACCEPTED. **Дата:** 2026-10-01. **Основание:** Phase 4 §§1/6/15/20–22, ADR-017; локальный import recovery OPEN-007.

Root — `%LOCALAPPDATA%/Studium`, или явно заданный temporary/dev data directory. Ключ: `files/<первые 2 hex UUID>/<UUID>.<разрешённое расширение>`. Имя источника — только metadata. Путь создаётся адаптером из контролируемого root/key; traversal, symlink/junction внутри storage и collision отвергаются. Source — обычный файл, без ссылок/спецфайлов. Копия читается блоками 1 MiB с SHA-256, size/mtime проверяются до/после. Лимит одного импорта 1 GiB ограничивает синхронный MVP workflow; originals сохраняются read-only средствами ОС. Это защита от случайной правки, не запрет владельцу ОС изменить атрибуты.

Перед копией создаётся/fsync журнал `files/.imports/<UUID>.json`; temp bytes — соседний `<UUID>.tmp`, также flush/fsync. Полная копия атомарно публикуется без overwrite (Windows rename; POSIX link/unlink). После публикации короткая DB transaction создаёт оба объекта. Ошибка файловой операции не создаёт DB rows; ошибка transaction компенсируется удалением только нового непредставленного asset. Сбой очистки не скрывается: русское сообщение различает сохранённый импорт и отложенный rollback, журнал остаётся для следующего запуска. Успешно committed original никогда не удаляется из-за сбоя finalization.

Composition root после Alembic сверяет только journal entries с FileAsset, включая archived: committed bytes сохраняются, uncommitted final/temp удаляются, marker очищается. OS lock на `.imports/lock` исключает recovery одновременно с импортом другого процесса; занятое хранилище сообщает ошибку. Повреждённый marker не запускает догадку/массовую очистку: запуск останавливается с понятной ошибкой, файлы сохраняются. Это bounded import reconciliation, не backup/restore/GC; повреждение диска/питания не обещает универсальной транзакции между SQLite и файловой системой (OPEN-011).

## ADR-025 — Integrity, file policy и кэш

**Статус:** ACCEPTED. **Дата:** 2026-10-01. **Основание:** Phase 4 §§7–8/13–15/22/24; локальная integrity часть OPEN-007.

verify_file_integrity возвращает derived available/missing/corrupted; размер и SHA-256 проверяются streaming. Статус не хранится в FileAsset, не меняет revision/deleted_at. Missing/corrupt записи остаются с учебным контекстом. Перед open/preview проверяется original; наличие thumbnail не маскирует пропажу. Permission/disk/IO failures — отдельные application errors с русскими сообщениями, не ложный missing. Автоматического ремонта файла нет.

Принимаются JPEG/PNG/WebP, GIF/BMP/TIFF, PDF, обычные TXT/MD/CSV/TSV/RTF, DOCX/XLSX/PPTX, ODT/ODS/ODP, ZIP/7Z и BIN. Allowlist сознательно не включает исполняемые форматы/скрипты/ярлыки/HTML/SVG/макросные Office; заголовки MZ/ELF/shebang отвергаются также при переименовании. BIN — metadata-only и не открывается через association. Это локальная политика, не антивирус/анализ содержания. MIME берётся из фиксированной extension map, не нестабильного Windows registry; preview дополнительно проверяет decoder/формат. Captured_at не извлекается: EXIF не вводится как новый доменный факт.

`cache/thumbnails/<UUID>-<SHA256>-<maximum>-v1.png` — regeneratable Qt cache вне SQLite, 240 px thumbnail и bounded 1400 px preview. QImageReader проверяет формат/размер (до 50 млн пикселей), использует scaled decoding/auto orientation. Missing/invalid cache пересоздаётся; original metadata не меняется. Кэш не считается evidence. JPEG/PNG/WebP проверены; дополнительные Qt formats доступны в установленном framework. Встроенный PDF — имеющиеся QtPdf/QtPdfWidgets; при недоступности модуля UI предлагает системное приложение. Новых dependencies/lock changes нет.

Открытие — QDesktopServices.openUrl(QUrl.fromLocalFile(controlled_path)), без shell command strings/исходного имени как команды. Windows принимает передачу default application; подтверждение openUrl не гарантирует завершение работы внешнего viewer. Политика безопасности конкретной системной программы остаётся её ответственностью. [Qt QDesktopServices](https://doc.qt.io/qtforpython-6/PySide6/QtGui/QDesktopServices.html), [QImageReader](https://doc.qt.io/qtforpython-6/PySide6/QtGui/QImageReader.html), [QPdfView](https://doc.qt.io/qtforpython-6/PySide6/QtPdfWidgets/QPdfView.html).

## ADR-026 — Additive v3 и минимальный file UI

**Статус:** ACCEPTED. **Дата:** 2026-10-01. **Основание:** Phase 4 §§11–12/16–18/20–28, ADR-015–ADR-018.

`0003_attachments`, down_revision `0002_learning_model`, добавляет только file_assets/attempt_attachments с checks/FK/unique/indexes/metadata/immutability triggers. v1/v2 не редактируются. Автоматический startup upgrade сохраняется; tests используют только temporary roots, реальные пользовательские данные не открываются. Проверяется populated synthetic v2 copy, v1 → latest, fresh/reopen и неизменность старого schema/facts.

История имеет раздел «Файлы» выбранной Attempt: multi-picker/drop local URLs, открыть/preview/detach/refresh. Каждый файл multi-import — отдельный compensated transaction, успешно импортированные файлы сохраняются при ошибке другого; ошибка каждого показывается. Импорт требует уже сохранённую Attempt; новая Attempt не получает прошлые файлы автоматически. Карточка студента получает только третью вкладку «Файлы» с контекстом всех работ/попыток, датой/именем/типом/integrity и простым текстовым фильтром. Double-click — contextual preview; image fit/scroll, QtPDF, metadata других типов. Размеры существующих окон уточнены под раздел файлов; большой redesign не выполняется.

Phase 5 понадобится MessageAttachment и расширение reference guards. Phase 10 сможет ссылаться на стабильный FileAsset UUID/hash и исходную Attempt для evidence; OCR/Vision/AI records не введены. Integrity/thumbnail и первичные факты имеют разные lifecycle. Backup/recovery policy OPEN-011 и остальные будущие OPEN не закрыты искусственно. Полный OPEN-007 остаётся открытым для ещё не реализованных владельцев/server storage; локальный контракт задания Phase 4 определён.

## ADR-027 — Student-owned QuestionCase и immutable Message

**Статус:** ACCEPTED. **Дата:** 2026-10-01. **Основание:** отдельное задание Phase 5 §§1–5/7–10/13–16/30, ТЗ §§5/7; **закрывает:** OPEN-003 в уточнённом контракте текущего задания.

QuestionCase — один содержательный вопрос известного Student, optional CourseOffering/title, opened_at/closed_at и metadata. Message — отдельный STUDENT/TEACHER факт с собственными channel/sent_at/body и metadata. Latest request уточняет более широкий Thread/Participant/QuestionMessage/AnswerMessage рисунок ТЗ: линейная цепочка не требует дублирующего CommunicationThread, ограниченного единственного answer_id или reply-to. Неизвестному внешнему автору нельзя создавать фиктивного Student; future adapter сначала требует явного сопоставления.

State не сохраняется: closed_at → CLOSED; иначе последний active author STUDENT → WAITING, TEACHER → ANSWERED. Пустая active цепочка после explicit soft delete → WAITING. CommunicationState enum служит только query DTO. Порядок sent_at/created_at/UUID устойчив для ties и backdated capture. Close не раньше last active sent_at; новый Message в closed case требует explicit reopen.

Исходные body/author/channel/date/case immutable, UI read-only. Audit/correction editor не добавляется; explicit archive_message сохраняет факт с updated_at/revision/deleted_at, корректная версия вводится новой записью. Общий OPEN-011 остаётся OPEN. Case archive сохраняет Messages/files/context, отдельной hard deletion нет.

Четыре независимые many-to-many QuestionCaseAssessment/Attempt/Topic/Skill обеспечивают реальные FK. Educational links требуют case.offering; Assessment того же offering, Attempt того же Student и offering, Topic/Skill той же Course. Attach Attempt не подменяет Assessment link. Detach/restoration content link сохраняет UUID и revision, не весь audit интервалов. Student ownership immutable; Enrollment не создаётся capture автоматически. Связь Skill/вопроса не оценивает освоение.

## ADR-028 — Scoped external identity и importer boundary

**Статус:** ACCEPTED. **Дата:** 2026-10-01. **Основание:** Phase 5 §§6/25–26, INV-05; **закрывает:** OPEN-013 только как data contract.

UNIQUE `(external_system, external_account_key, external_thread_id, external_message_id)` действует также после soft delete. Identity либо полностью NULL, либо четыре nonblank strings. MANUAL никогда не имеет external key; copy/paste EMAIL/TELEGRAM тоже не требует ID и не deduplicates текст. External-system namespace различает provider/mode/версию нормализации; account key не credential; thread/scope должен быть стабилен. Telegram chat-local ID требует chat scope; account-global ID требует постоянную документированную namespace, без изменяемой display-thread grouping. Примеры namespace `telegram:user:v1`, `telegram:bot:v1`, `email:provider:v1` иллюстративны, adapters не написаны.

Core record_imported_message возвращает исходный Message при повторе совпадающих case/author/channel/date/body; mismatch — явный conflict без логирования body/перезаписи. Archived identity остаётся занятой и replay не resurrects запись. UNIQUE предотвращает две rows даже при concurrent writers; адаптер должен retry/re-read после локальной гонки/занятости.

CommunicationImporter.read_messages → ImportedCommunication отделяет transport от core. Требуется explicit case/Student matching, сохранение исходного текста/UTC и scope normalization до записи. Authentication/secrets, live provider policies, paging/retry/checkpoint, unknown sender review и network/files acquisition относятся к будущим adapters. Telegram/Gmail/IMAP dependencies, API calls и sending не добавлены.

## ADR-029 — Additive v4, общий FileAsset и минимальный Questions UI

**Статус:** ACCEPTED. **Дата:** 2026-10-01. **Основание:** Phase 5 §§11–12/17–22/27–34, ADR-023–ADR-026.

Alembic `0004_communication` после `0003_attachments` добавляет семь tables, UUID/UTC/revision/deleted_at, FK RESTRICT, pair/external uniqueness, context/immutable/metadata/no-delete triggers. Historical v1–v3 сохранены. Проверяются реальные populated copies v1/v2/v3, fresh/reopen и preservation строк/SQL objects/bytes, не production DB.

MessageAttachment переиспользует FileAsset и прежний storage/import journal/SHA-256/integrity/thumbnail/preview. Новые files immutable; отдельная явная связь может переиспользовать asset Attempt. Новый reference guard не разрешает archive asset при active message link. Detach сохраняет original/tombstone; shared owners не теряют bytes. Import DB failures компенсируются; startup journal recovery проверяется также crash tests Message до/после commit. Backup/GC/audit/server storage OPEN-007/011 не закрываются.

UI расширен стандартными Qt widgets: global «Вопросы» за все периоды, case dialogue с ordered roles/messages/вложениями/context/work transition, Student → Questions, capture/paste/channel/timestamp. Search — Unicode casefold literal substring, filters — derived states. Full body видна при выборе сообщения, роли имеют подписи/разные цвета; redesign chat app не выполнялся. Body не логируется. Case/first Message/context commit атомарны; file multi-import — отдельные compensated transactions с явной ошибкой каждого.

Новых dependencies нет. Хороший Teacher Message имеет source UUID для future KnowledgeEntry, но FAQ/analytics/mastery/AI/transport/backend/sync/mobile и Phase 6 не реализованы.

## Остаток OPEN после Phase 5

RESOLVED: OPEN-001/003/008 и OPEN-013 (data contract). OPEN: **002, 004 (остаток), 005, 006, 007 (другие owners/server storage), 009 (остаток), 010, 011, 012, 014**. Общий backup/audit/analytics/sync не объявляется решённым.

## ADR-030 — AttemptItemResult и semantic lock

**Статус:** ACCEPTED. **Дата:** 2026-10-02. **Основание:** отдельное задание Phase 6 §§2–6/23–24/27, ТЗ §§4.6/6.3/13; отвечает на OPEN-014.

Добавляется отдельный frozen AttemptItemResult: explicit Attempt/AssessmentItem FK, ItemOutcome CORRECT/PARTIAL/INCORRECT/NOT_EVALUATED, nullable score/max_score/comment и стандартная EntityMetadata. Outcome или score обязателен; outcome не преобразуется в score. Score without maximum допустим, normalized metric тогда None. Результат Item обязан относиться к Assessment работы Attempt. Активная пара уникальна; первоначальные факты immutable, correction — explicit archive и новый UUID с сохранением прежней row. Переделка создаёт новую Attempt со своими результатами.

Выбрана разрешённая strategy **A: semantic lock после любой первой Attempt**, включая служебную/архивированную. Application guards и additive SQL triggers замораживают Assessment offering/type/number/title/description/max_score; состав/смысл/maximum/archive Items; четыре вида Assessment/Item Topic/Skill links, включая detach/restore. Связанные Topic/Skill course/title/description/archive и ancestor Topic parent защищены; иначе перенос темы изменил бы старую родительскую агрегацию. Unrelated taxonomy остаётся изменяемой. Sort_order/reorder — presentation, разрешены. TopicSkill не является source для автоматической классификации item results и не замораживается ради inference, которого нет.

Расписание issued_at/due_at можно редактировать явно; timeliness пересчитывается по текущему сроку. Archive самой Assessment сохраняет содержание/Attempt/results и скрывает её из текущего среза. Это не full content versioning, deadline/audit history или purge. v5 блокирует последующие семантические изменения существующих работ с Attempt. Изменения до v5 без сохранённых редакций восстановить нельзя; миграция не выдумывает historical snapshot.

Alembic `0005_analytics_foundation` после `0004_communication` добавляет attempt_item_results, active-pair UNIQUE/reverse index, FK RESTRICT, metadata/immutable/context/no-delete triggers и derived lock views/triggers. Views вычисляют scope блокировок из существующих фактов и не хранят primary metrics. v1–v4 py/SQL не редактируются; migration tests требуют populated copies всех четырёх revisions и fresh/reopen/FK. Downgrade с потерей новых фактов запрещён.

## ADR-031 — Вычисляемые показатели и distinct evidence

**Статус:** ACCEPTED. **Дата:** 2026-10-02. **Основание:** Phase 6 §§1/7/9–14/16–18/24–28; определяет aggregation часть OPEN-002 и scope OPEN-012.

AnalyticsService читает один bulk transaction через domain repository ports и возвращает frozen typed DTO. Никаких ORM models/SQL aggregation в Qt и никаких metric tables/cache. Статус и final_score принадлежат прежнему StudentWorkProgress; Grade не создаёт второе grading правило. Все denominators и правила опубликованы в [analytics.md](analytics.md), включая cohort/assignment scope.

Начатая работа имеет активную Attempt, кроме COMMENT_ONLY. REJECTED — записанное неуспешное предъявление: оно препятствует ложному first-pass после следующего ACCEPTED, сохраняя прежнюю status-neutral domain семантику. First-pass — первый содержательный Attempt по attempt_no ACCEPTED; denominator все начатые работы. Raw attempt_count содержит комментарии, average attempts — raw active records только начатых работ / started. Completion/passed — current projection ACCEPTED. Нормированный текущий балл использует final_score и maximum source Attempt, без подстановки mutable Assessment maximum. Group pooled ratios/distribution не создают список ранжирования.

Topic/Skill links Assessment и Items независимы; whole-attempt result не становится результатом каждой Item/Skill. Covering works объединяют direct whole tags и явно tagged items. Evidence отдельно считает исходные whole Assessment Attempt как контекст, ItemResult как проверку части, QuestionCase как связанный вопрос, Topic Lesson/Attendance как exposure. Distinct typed UUID объединяются по descendants; parent+child link не удваивает один source. NOT_EVALUATED и score-only различаются, отсутствие score не ноль. TopicSkill не является LessonSkill (OPEN-004 остаётся OPEN).

PRESENT+LATE / PRESENT+LATE+ABSENT — attendance_rate; EXCUSED/UNKNOWN/missing отдельно, без подмены отсутствием. Все пустые denominators/недостаточные numeric data → None. UI показывает «Нет данных»; отсутствие применимого срока/прямого вида связи → «Не применимо». Teacher/student message counts и question activity не превращаются в штраф или оценку знаний.

Один service query делает bulk reads независимо от Students × Assessments, timeline переиспользует snapshot. Кэш/analytics framework/pandas/new dependencies не требуются. Synthetic performance/read-only tests проверяют strategy, без утверждения SLA для всего будущего объёма. Чистые DTO подходят для будущего экспорта/AI evidence, но ни экспорт, ни AI не реализуются.

## ADR-032 — Deadline, response time и динамика известных фактов

**Статус:** ACCEPTED. **Дата:** 2026-10-02. **Основание:** Phase 6 §§8/14–15/25 и цель «изменения во времени»; уточняет только решённую часть OPEN-009.

Timeliness использует min occurred_at содержательных предъявлений и текущий due_at. <= — вовремя, > — поздно; отсутствие предъявления при due_at < cutoff — overdue/not submitted. Denominator on_time_rate — только наблюдаемые первые сдачи со сроком (on_time+late), pending/unsubmitted показаны отдельно. Отсутствие срока неприменимо; существующий будущий срок без предъявлений означает отсутствие данных, а не 0%. Progress ordering по attempt_no остаётся независимым от source timestamp/backdated capture.

UtcInstant не становится учебной календарной датой. Lesson/term LocalDate не преобразуется в midnight. Calendar days_late допускается только utility с явно переданным reporting timezone; постоянный учебный timezone/date-only deadlines и соответствие UTC Enrollment к Lesson дню не введены и остаются OPEN-009. Явное изменение due_at может пересчитать timeliness; audit deadline versions остаётся OPEN-011.

Response time — один Student episode (первое сообщение и дополнительные подряд) → первый следующий Teacher Message внутри того же case. Seconds от первого Student Message. Неотвеченный эпизод исключён из mean/median; равные sent_at разных ролей неоднозначны и считаются отдельно, metadata/UUID не доказывают причинный порядок. Следующий Teacher Message без ожидающего Student не создаёт второе измерение. Это наблюдаемая задержка, без оценки качества/режима работы/прогноза.

as_of — cutoff исходных Attempt.occurred_at/Message.sent_at/QuestionCase.opened_at, recording-time для ItemResult/Lesson/Attendance, где нет отдельного точного исходного момента. Текущие catalogue/context/archive/correction facts сохраняют свою текущую область. Это динамика известных событий, не полный audit snapshot прежней БД или доказательство, что эти сведения уже были известны в прошлом. Reopen/изменённые attendance без audit и pre-v5 content revisions не реконструируются.

## Остаток OPEN после Phase 6

Это исторический остаток на дату Phase 6. Современная применимость — в [BACKLOG](management/BACKLOG.md): license/target repository решены владельцем, frozen migration tests и local backup реализованы. Публикация Studium-public и Windows acceptance не подтверждаются этой исторической записью.

RESOLVED: **OPEN-001/003/008/012/014**, **OPEN-013** как data contract. **OPEN-002** сохраняется только для manual overrides/correction audit; формулы текущей аналитики определены ADR-031/032. Открыты **004** (прямые LessonSkill/LessonAssessment), **005** (будущие платформы), **006** (license/remote), **007** (другие owners/server files), **009** (учебный timezone/date-only/membership день), **010** (ownership/sync), **011** (audit/purge/backup, в том числе прежние редакции/переносы сроков). Эти остатки не подменяются выводами из текущего каталога и не блокируют согласованную локальную аналитику.
