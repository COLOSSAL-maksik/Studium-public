# QA-A — согласованные решения и предлагаемые технические контракты

## Дополнение ST-PR3-002 — frozen taxonomy

На базе `67986fd` archive Topic/Skill, используемых сохранённой версией/назначением,
отклоняется с concrete dependency list. Новая v12 добавляет только два archive
guards; 22 v1–v11 payloads, прежние facts/UUID и SQL guards сохраняются.
27 новых synthetic regressions, итоговый targeted пакет **165 PASS**. Required CI
нового HEAD фиксируется в PR; manual всех 30 — PENDING. [Отчёт](PR3_REVIEW_FIXES.md).
Ниже сохранены предыдущие implementation/verification результаты.

## Реализация уточнений review PR #3

Все четыре замечания исправлены в существующей ветке и PR #3 с сохранением
пакета всех 30: late first submission при ended participation; frozen V1
problem/family/attachments; explicit preview/CAS переназначения с прежними
bindings; полная сводка ДЗ/РК/посещаемости и переходы. Additive v11,
v1–v10 payloads неизменны. [Отчёт](PR3_REVIEW_FIXES.md), [ADR-051](../decisions.md#adr-051).
Целевые DB/GUI: 38 PASS; полный local regression: 1113 PASS / 3 ожидаемых
Windows-only SKIP. Wheel, Ruff/pip, frozen migrations и safety: PASS. Exact-HEAD
CI evidence — в итоговом PR.
Manual всех 30 — PENDING, промежуточная приёмка не требуется. История ниже
сохраняется; старые результаты не объявляются проверкой нового HEAD.

## Единый implementation-пакет — решение 2026-10-10

Владелец расширил задачу до всех ST-QA-001–ST-QA-030 в одной ветке
`agent/codex/qa-a-contracts` и одном итоговом implementation PR. База реализации:
`d23eee39fcb0f3bd463c2868459fa48d0778925a`; документационная база PR #2 сохранена.
QA-A → QA-B → QA-C → QA-D — внутренний порядок зависимостей после необходимых
автоматических проверок. Промежуточные ручные приёмки и merge между этапами
отменены этим решением; общий manual acceptance остаётся PENDING после пакета.
Прежний план десяти QA-A PR и directions-only scope — исторические предложения.

B7–B9 впервые заданы этим пакетным решением: SLA 7 календарных дней от received_at
в explicit offset, near-due последние 24 часа, overdue строго после deadline;
«выполнено» — подтверждённая содержательная сдача, «зачтено» — explicit ACCEPTED,
cancelled исключается из active denominator; шаблоны structured answers копируются
в immutable task/variant snapshots, teacher-only данные не публикуются студенту.
Норматив и near-due настраиваются. Ранее не подтверждённое согласование не выдумывается.

Текущие implementation/evidence и manual pending ведутся в
[QA_ALL_30_IMPLEMENTATION](QA_ALL_30_IMPLEMENTATION.md). Матрицы и записи ниже
сохраняют исторический baseline; они не являются статусом нового пакета.


**Дата:** 2026-10-11. **Проверенная база:** актуальный `origin/main`,
`b620ef3635c2965ad3630bae15d00d1b7bd9a82d` (получен fetch перед созданием ветки).
Первоначальный [аудит](QA_AUDIT.md) на
`ef5414faa594eba0f339d4208d605c92e98de903` сохраняется как предыдущий baseline.

Продуктовые B1–B6 **СОГЛАСОВАНЫ**. B4: целые новые баллы по умолчанию,
сохраняемый переключатель дробного ввода с двумя знаками. Дополнение B2:
владелец разрешил срок ДЗ/РК после окончания семестра при предупреждении
и явном подтверждении. Это не разрешает выход модулей за семестр.
**Последующее уточнение 2026-10-11, при review HEAD
`3649afaee48be28d27f81ac41aff86087d594636`:** долг конкретного студента
сохраняется в следующих семестрах до явного ACCEPTED; индивидуальное закрытие
модуля отделено от календаря группы. Это новое уточнение B2/ST-QA-011 и
будущей сводки ST-QA-029, не ранее известное решение и не закрытие этих ID.

Модель таблиц, алгоритмы и диапазон хранения ниже — **PROPOSED, до технического
review**, а не реализованная схема. Этот документ выполняет документационный
scope QA-A-PR-01. Разбиение на [10 PR](QA_AUDIT.md#qa-a-pr-plan) остаётся
предложением, не утверждённым владельцем. Приложение и Alembic/SQL не изменены;
implementation, application/migration tests и Windows/manual acceptance **NOT RUN**.
[ADR-049](../decisions.md#adr-049--qa-a-product-contracts) фиксирует эту границу.

## 1. Фактическая основа и несовпадения с новым поведением

Все ссылки ниже относятся к исходникам указанной базы; evidence статическое.

| Область | Что реально есть | Следствие для реализации |
|---|---|---|
| Программа | [WorkProgram/ProgramWork](../../src/studium/domain/program.py), [ORM](../../src/studium/infrastructure/database/models/program.py): обязательный `term_id`, `semester` AUTUMN/SPRING, `first_week_start`, `weeks` 1–104, offset; `version` — строка | Это календарь и содержание вместе; строка version не является immutable версией. AUTUMN не доказывает порядковый семестр курса |
| Назначение | [ProgramService](../../src/studium/application/program_services.py) `set_offering_program` проверяет course/term и блокирует переключение при фактах; [v7 backfill](../../src/studium/infrastructure/database/migrations/versions/v0007.py) создавал программу на offering | Новое назначение версии/плана требует нового контракта; старые программы не сливать по названию |
| Ограничения плана | [v7 SQL](../../src/studium/infrastructure/database/migrations/versions/v0007.sql) `program_works_program_context_insert/update`: due week внутри модуля, недели внутри программы; guards модулей предотвращают пересечения/выход за duration | B2 с module 1=1–6 и due week=7 сейчас отвергается. Новый offering plan должен разрешать подтверждённое исключение, сохранив legacy guards |
| Выдача | `issue_program_work` берёт `issued_at` из плановой `issue_date`, иначе clock; `_program_instant(..., end=True)` вычисляет следующий день минус 1 microsecond | Legacy issued_at не всегда actual issuance. Сохранить существующий точный timestamp, новую date-only границу хранить с другим видом сравнения |
| Deadline | [Analytics snapshot](../../src/studium/application/analytics.py) `_Snapshot.work_facts`: exact `due_at` имеет приоритет над planned week, exact `<=` вовремя и `>` поздно; [journal](../../src/studium/application/journal.py) читает planned due week | Новый typed deadline нужен и аналитике, и журналу; не двигать старое exact значение ради унификации |
| Attempt/Grade | [entities](../../src/studium/domain/entities/__init__.py), [progress](../../src/studium/domain/services/progress.py), [service](../../src/studium/application/services.py) `add_attempt/_grade`, [v1 SQL](../../src/studium/infrastructure/database/migrations/versions/v0001.sql): immutable facts, monotonic number, Grade UNIQUE attempt | Запись numeric Grade к PRESENTED со score=None сейчас отвергается: Grade должна равняться score/max Attempt. Нельзя менять эту Attempt или создавать фиктивную сдачу для review |
| Баллы | [ORM core](../../src/studium/infrastructure/database/models/__init__.py), [item results](../../src/studium/infrastructure/database/models/analytics_facts.py): REAL score/max, min отсутствует | Legacy REAL и отсутствие min требуют compatibility, не массового Decimal backfill с округлением |
| Критерии | [ADR-030](../decisions.md): Assessment max/content/Items/semantic links заблокированы после любой Attempt, включая архивную | Новые ScoringRuleVersion добавляются отдельно; снятие старого lock не реализует B6 безопасно |
| Индивидуальный долг | В `ProgramModule/ProgramWork` нет обязательности работ или student module closure; analytics `completed` проверяет явный status ACCEPTED. `add_attempt/_context` не проверяют конец календарного периода, но требуют active enrollment и не deleted контекст; SQL `attempts_active_work` требует active Work/Assessment | Future required-work binding и debt/module result нужны отдельно; окончание семестра не является archive. Завершённое enrollment сейчас блокирует запись и требует отдельного late-debt use case, а не выдуманной ACTIVE записи |
| Preferences | [JsonPreferences](../../src/studium/infrastructure/user_data.py): JSON вне учебной БД, read/merge/temp replace, theme/recent/table widths | Новый bool добавлять без замены других ключей и без изменения учебных фактов |
| Backup | [adapter](../../src/studium/infrastructure/backup.py) `_supported_schema_hash/_manifest`, [ZIP contract](../iteration5b-backup-recovery.md): exact current revision/schema hash, все FileAsset, preferences исключены | Новая schema обязана обновить поддержку backup; нельзя объявить старый archive уже поддержанным или подменять revision |

## 2. B1: содержание версии и календарь конкретной группы

Предложение: `ProgramContent` — логическая программа целого Course;
`ProgramContentVersion` — её содержание, список направлений и placements
модулей/работ/тем по `course_semester_no` (положительный порядковый номер).
У версии нет обязательного AcademicTerm, календарных дат или timezone группы.
Legacy `work_programs.id` сохраняется и связывается explicit map с отдельной
content/version; ни title, ни faculty, ни version string не являются ключом слияния.

В reusable content ссылки на definitions/topics/materials сохраняют source UUID,
но назначенная версия хранит нужные content snapshots/source revisions.
Изменение mutable библиотеки не должно незаметно менять её содержание.
Направления: `Direction(code, optional name)` и concrete ProgramDirection FK;
предлагается canonical code после NFC/trim (casefold для сравнения), уникальный
в локальном справочнике, с сохранением исходного display code,
UNIQUE program/code. Код не выводится из названия. Только однозначно распознанный
полный код вида `[0-9]{2}.[0-9]{2}.[0-9]{2}` (точки literal) связывается
автоматически; другие непустые коды задаются явно, не угадываются из raw text.
Свободная строка сохраняется дословно,
её разбор/сопоставление требует явного действия. Не клонировать темы/задачи.
Display name — derived title + codes + при неоднозначности version/UUID suffix;
исходный title не заменяется display name.

`SemesterPlan` имеет concrete `offering_id`, `content_version_id`,
`course_semester_no`, `first_week_start`, `weeks`, `utc_offset_minutes` и revisions.
CourseOffering сохраняет Course/StudentGroup/AcademicTerm и исторический UUID.
Один активный план на offering; другие периоды группы получают свои offering/plan.
Пример: семестр курса №1 → группа G-A, AcademicTerm T-A, 17 недель с 07.09.2026;
№2 → та же группа, T-B, 18 недель с 08.02.2027, та же content version V1.
Другая группа имеет свои dates/offset. Наступление T-B не создаёт content copy
и не переключает G-A на V2; явное продолжение выбирает V1 и номер №2.

Legacy AUTUMN/SPRING/term не доказывают №1/№2. При upgrade placement и ordinal
отмечаются `legacy_unmapped`; календарь текущего offering доступен через
compatibility adapter. До переиспользования версии в новом периоде преподаватель
явно сопоставляет номер; не создавать ложную «первую половину курса».

| Состояние | Действие | Следующее состояние / эффект |
|---|---|---|
| Content draft, не назначен | Изменить содержание | Тот же draft с revision check |
| Content draft | Назначить группе | Атомарно freeze V1 и bind plan; версия immutable |
| V1 назначена | Изменить содержание | Новый draft V2 с lineage к V1, новые snapshot IDs; группы остаются на V1 |
| План draft | Отложить настройку / reopen | Тот же draft, без fake Assessment/Attempt/Grade и дубликатов |
| План готов | Изменить даты/недели/сроки | Новая PlanRevision; V1 и другие планы не меняются |
| V2 готова | Явно переназначить группу | Отдельный preview/confirmation, сохранение старого binding и фактов; при существующих работах нельзя просто заменить FK |

Content modules не хранят actual calendar interval группы. `PlanModule` ссылается
на content module; `PlannedAssessment` — на content work/definition и свой модуль.
UNIQUE offering/source placement предотвращает повторное клонирование при reopen.
Исходный план новой реализации фиксируется при первом подтверждённом сохранении;
для legacy первая запись — «состояние на миграции», не утраченный начальный план.

## 3. B2–B3: переносы, выдача, даты и точные границы

`PlanRevision` и `PlanChange` immutable: initial/current revision, affected concrete
IDs, before/after, recording UTC, optional reason, подтверждённые исключения
`outside_module`/`outside_semester`. Current pointer меняется в одной транзакции.
Preview читает snapshot и возвращает DTO без записи revision/event/preferences.
Apply проверяет expected revisions плана и затронутых записей, срок/контекст,
подтверждения и весь пакет; late failure/stale edit откатывают весь пакет.
Idempotency key на подтверждённой операции предотвращает повторный apply.

| Пример в 17-недельном плане | Preview | Подтверждённый результат |
|---|---|---|
| Модуль 1: 1–6 → 1–7; модуль 2: 7–12 | Конфликт недели 7, показать конкретные модули/работы, предложить 8–12 | Только явно выбранный согласованный пакет; без него нельзя сохранить пересечение |
| ДЗ модуля 1, due week 6 → 7 | Предупредить о выходе из модуля и новой позиции журнала | module_id остаётся прежним, соседние работы/модули не меняются |
| РК модуля 3, deadline после последнего дня семестра | Отдельно предупредить о выходе из семестра и последствиях для overdue/журнала | После явного подтверждения срок разрешён; показать дату и «после семестра» в плане/журнале, не выдумывать учебную неделю 18 |
| Модуль 3: 13–18 | Ошибка: последняя неделя 17 | Выход модуля за семестр запрещён даже с подтверждением |
| Выданное ДЗ, срок перенесён | Показать новый due и затронутую planned/issued запись | Один current deadline для plan/journal/analytics через adapter; actual issue, Attempt/Grade dates не меняются |

Предлагаемые новые плановые недели модулей остаются 1..weeks, без пересечений,
внутри соответствующего AcademicTerm. Legacy несогласованность term ends и
program duration не исправляется сокращением; показывается compatibility warning,
новый нормальный план требует явного согласования календаря.
Для срока после семестра хранится дата/instant и marker, а не некорректная
AcademicWeekNumber. Отмена/архивирование работы с фактами сохраняет их и связи;
молчаливое удаление запрещено.

<a id="b2-student-debt"></a>

### B2: индивидуальный долг и закрытие модуля после семестра

**Продуктовое уточнение 2026-10-11 после первоначального HEAD PR #2.** Работа
остаётся долгом конкретного студента в исходном offering/модуле/семестре.
Календарное окончание T1, начало T2 и выбор T2 активным периодом не закрывают
долг, не запрещают позднюю сдачу и не переносят H1 в новый offering.
UUID Assessment/StudentWork, module binding, Attempt/Review и их история прежние.
Новая реальная сдача получает следующий attempt_no из всей истории, включая
архивные записи; проверка/перепроверка сохранённой сдачи меняет лишь review_seq.

Для этого контракта «сдал работу» означает явный **ACCEPTED** преподавателем.
PRESENTED означает зарегистрированную сдачу, SCORED — числовую проверку без
автоматического зачёта; сами по себе они долг не закрывают. NEEDS_REVISION
оставляет долг открытым и в новом Review-контракте не начисляет текущий балл.
Если прежний ACCEPTED уже существует, допустимый SCORED не создаёт новый зачёт:
status может сохранить прежний ACCEPTED по resolver, а долг уже закрыт им.

Индивидуальный модуль закрыт, когда в известном назначенном наборе обязательных
работ **все** работы имеют актуальный результат ACCEPTED. Непринятая обязательная
работа сохраняет открытый долг. Поздность сдачи и долг различны: поздняя работа
может быть зачтена, а PRESENTED вовремя может ещё оставаться непринятой.
Состояние модуля студента не удлиняет PlanModule, не переносит Lesson группы и
не зависит от переключения активного семестра.

Предлагаемая будущая граница модели: versioned required-work set с concrete
plan/module/work FK и binding к студенту/исходному назначению; read DTO
`StudentModuleResult` отдельно от календарного PlanModule. Обязательность
сохраняется явно с историей набора, не выводится из score/min, типа работы или
наличия Attempt. Отсутствующий StudentWork не создаётся чтением DTO и не считается
зачётом. Legacy не хранит required flag/closure: набор неизвестен, до явного
сопоставления/подтверждения нельзя миграцией объявить все работы обязательными
или модуль закрытым; неизвестный/ненастроенный набор отображается как unknown.
Точная схема binding/истории и derived closure — PROPOSED до technical review,
не существующая реализация и не новый UI этого PR.

| Синтетический пример | Срок и факт сдачи | Индивидуальный долг / модуль | Сохранённый контекст |
|---|---|---|---|
| T1 окончен 31.01.2027; M1 требует H1; у A нет зачёта, у B все обязательные работы ACCEPTED | Действующий date-only срок H1: 20.01.2027, +03; наступил T2 | A: H1 долг, M1 открыт; B: M1 закрыт. Календарь группы T2 идёт как запланировано | H1/M1/offering T1, те же UUID |
| A предъявил H1 10.02.2027 в T2 | Новый PRESENTED позднее excluded boundary 21.01 00:00+03; срок не изменён | Долг открыт, M1 открыт; регистрация не означает ACCEPTED | Новый attempt_no у прежнего StudentWork; никаких копий H1 в T2 |
| Review1: NEEDS_REVISION | Дата сдачи/срок те же; review не новая сдача | Долг открыт, M1 открыт, current score=NULL | Review1 неизменяемая, attempt_no прежний |
| После Review1 попытка SCORED(24) | Проверка того же submission в REVISION_REQUIRED | Reject без новой Review/Grade; долг и current score=NULL прежние | Нет нового attempt_no или consumed review_seq |
| Явная Review2: ACCEPTED(24), rule 18–30 | Срок не переносили: сдача остаётся поздней | Долг H1 закрыт; M1 у A закрыт, если других обязательных долгов нет | ACCEPTED/history остаются H1/M1/T1; только новый review_seq |
| M1 требует H1 и H2, H1 ACCEPTED, H2 не ACCEPTED | Поздность H1 не подменяет результат H2 | H1 закрыт, H2 долг; M1 открыт до явного ACCEPTED H2 | Оба исходных work/module bindings сохраняются |
| Отдельный перенос H1 на 15.02.2027 после preview/confirmation | Новая PlanRevision меняет только current deadline; сдача 10.02 может стать вовремя относительно нового срока | Перенос сам по себе не зачёт: долг определяется ACCEPTED, не новой датой | Старый deadline в history; исходные submitted_at/reviewed_at не переписаны |

Каждая новая сдача/пересдача сравнивается с сохранённым **действующим сроком**
своей H1 по B3; факт сдачи/начала T2 не переносит его автоматически. Legacy
`_Snapshot.work_facts` использует первое предъявление для своей timeliness
метрики: его прежний output сохраняется. Future per-submission timeliness нужен
отдельно, чтобы поздняя пересдача не становилась «вовремя» лишь из-за ранней S1.
Deadline, late submission, debt и individual closure — разные поля/DTO.

Для QA-B требуется доступ к долгам прошлых offering/периодов из нового активного
семестра: scope по студенту и исходным work/module bindings, а не только по
active_term/current roster. Полный UI сводки/очереди/регистрации относится к
ST-QA-029/027/017 в QA-B. B7–B9 целиком этим уточнением не решаются.

Явное архивирование рассматривается отдельно: `_require(..., historical=False)`
скрывает deleted контекст, `attempts_active_work` отвергает запись в deleted
StudentWork/Assessment, `add_attempt` требует active Student/enrollment. Сам
`AcademicTerm.archived` — отдельный bool, не равен ended date или deleted_at;
не объявлять его автоматическим запретом, которого эти guards не проверяют.
Чтение истории с historical=True не даёт права записи. Архивирование не
превращает незачтённую работу в ACCEPTED и не стирает долг/историю.

Предлагаемый late-debt use case проверяет исходное назначение, student/offering
scope и evidence прежнего enrollment; поддержка завершённого membership должна
быть явно спроектирована, без fake re-enrollment, изменения ended_at/status или
обхода archive guards. Для explicitly deleted контекста нужен отдельный явный
путь восстановления/разрешения записи с сохранением фактов; его точные
preconditions ещё требуют technical review. Текущий `add_attempt` этот путь
не реализует. Это зависимый технический вопрос QA-B регистрации долгов, а не
повторное согласование разрешённой сдачи в следующем семестре.

### Deadline kind и приоритет

Предложение: `DeadlineSpec` = `EXACT_INCLUSIVE(instant)` /
`DATE_EXCLUSIVE(local_date, offset, next_day_start)` / `WEEK_ONLY(week)` / `NONE`.
У нового ввода режимы взаимоисключающие; derived weeks не заменяют deadline.
Legacy exact due_at сохраняет приоритет над week/date, в том числе когда они
расходятся. При новой явно выбранной date-only редакции её typed boundary
заменяет current spec; старый exact остаётся в предыдущем snapshot.

Offset плана задаётся явно. Для нового преподавательского плана default Москва,
UTC+03:00 (`180` минут); существующие offsets копируются без смены на Москву.
Пояс ОС не используется как скрытая истина. Изменение offset плана — явная
calendar revision; существующие exact instants не пересчитываются, последствия
для date-only future deadlines показываются и подтверждаются.

| Срок / сдача / cutoff | Сравнение | Результат |
|---|---|---|
| Date-only 14.10.2026, +03:00 | Boundary E = 15.10.2026 00:00:00+03 = 14.10.2026 21:00:00Z | Вовремя `submitted_at < E`; поздно `>= E` |
| Сдача 14.10 20:59:59.999999Z | `< E` | Вовремя без округления |
| Сдача ровно 14.10 21:00:00Z | `= E` | Поздно |
| Нет сдачи, cutoff ровно E | `cutoff >= E` | Просрочено; до E ещё не просрочено |
| Exact 14.10.2026 18:00+03 = 15:00Z | `submitted_at <= D`; поздно `> D` | Ровно 15:00Z вовремя; 15:00:00.000001Z поздно |
| Нет сдачи, exact cutoff ровно D | `cutoff > D` | Ещё не просрочено на равенстве, как ADR-032 |
| Week-only 6, exact отсутствует | Week в offset плана `<=6`; overdue после недели 6 | Не приписывать исходной записи выбранную календарную дату |
| Legacy exact вместе с week 6/date | Использовать исходный exact и inclusive operator | Не менять timestamp на начало следующего дня |

UTC хранится в прежних INTEGER microseconds. Не использовать `23:59:59`,
epsilon subtraction или hidden rounding для новых DATE_EXCLUSIVE.
Legacy `_program_instant` next-day-minus-microsecond остаётся exact совместимостью.
Журнал помещает ДЗ в неделю effective current due в offset плана, а не выдачи;
date-only использует выбранный день, не дату excluded boundary. Вне календаря —
явная секция «после семестра» с due date; без срока — отдельное «без срока».
План выдачи может быть до начала модуля. Это не меняет module affiliation.

### Planned issuance и actual issuance

Плановая date/week — часть изменяемого календаря. `IssuanceEvent` — отдельный
факт actual issue, source/action provenance, actual UTC и recording UTC;
явное действие преподавателя идемпотентно для одной выдачи Assessment.
Date-only ввода выдачи означает planned day, не вымышленную actual midnight.
Для actual преподаватель подтверждает факт/время; время действия может быть
явно показанным default. Reschedule deadline не меняет actual issue.

Legacy `assessments.issued_at` хранится дословно с `legacy_ambiguous` provenance.
Наличие issue_date или совпадение с clock/created_at — не доказательство actual.
Подтверждение преподавателем создаёт отдельную запись с происхождением, сохраняет
raw issued_at и не переписывает датировки Attempt/Grade. Историческая аналитика
legacy продолжает прежний путь; новые fact-based readers должны отличать unknown
issuance от confirmed и показывать это в DTO, не пропускать данные молча.

## 4. B4: точные новые числа, целый default и preferences

Предложение хранения: domain `ScoreValue` принимает Decimal из decimal text,
SQL хранит scaled **INTEGER в сотых**, `units = value × 100` точно.
Новый finite диапазон `0 .. 92233720368547758.07`
(`units 0 .. 9223372036854775807`, signed SQLite int64); max > 0,
`0 <= min <= max`. Это технический предел представления, не общий maximum работ.
До умножения/записи проверяются scale, диапазон и переполнение; bool/NaN/Infinity,
scientific/non-decimal UI input и out-of-range отвергаются понятной ошибкой.
SQL CHECK typeof INTEGER + domain/application проверки нужны и при прямой записи.
Для сумм использовать Python int/Decimal и проверенный диапазон результата,
не переполняющий SQLite SUM и не binary float; отсутствие данных остаётся None.

В preferences.json предлагается bool `fractional_scores_enabled`, default false
при отсутствующем/невалидном ключе. Запись через existing read/merge/temp replace,
без потери unrelated keys; ошибка сохранения оставляет прежний effective режим
и введённый текст. Application validation получает effective mode через port,
Qt только показывает правила. Хранение всегда сотые, независимо от переключателя.

| Сценарий | Ввод/валидация | Отображение / сохранность |
|---|---|---|
| Новый профиль, режим OFF | Новые score/min/max только математически целые, 24 допустимо, 24,5 нет | `24/30`, без `,00` |
| Режим ON | 24, 24,5, 24,75 допустимы; 24,751 отклоняется, не округляется | `24/30`, `24,5/30`, `24,75/30`; decimal separator locale |
| Смена ON → OFF при unsaved 24,75 | Текст остаётся; явная ошибка «Дробный ввод выключен», save блокируется до включения или ручного исправления | Никакого truncate/reset/автосохранения |
| Сохранённое exact 24,75, режим OFF | Просмотр и сохранение другого изменяемого поля формы работы без изменения numeric field допустимы; immutable Review/Grade не редактируются | История показывает `24,75`; новое/изменённое fractional значение отклоняется |
| Старый диапазон 18,25–18,75, режим OFF | `ceil(min)=19 > floor(max)=18`: допустимых целых нет | Объяснение и действие включить дробный ввод; не менять границы |
| Сохранённая exact rule 18,25–30, режим OFF | Новые целые 19–30 допустимы, 18 нет; Review с новой оценкой 24 разрешена | Выбор rule и копирование неизменённых min/max 18,25–30 в Review snapshot допустимы при OFF; точные bounds сохраняются |
| Создать/изменить min=18,25, режим OFF | Reject нового/изменённого fractional bound; требуется ON | Существующая rule не переписывается; unrelated fields её границы не меняют |
| Новая Review с score=24,75, режим OFF | Reject, даже если прежняя Review имела ровно 24,75 | История прежнего score видна; snapshot copying не разрешает новый fractional score |
| Mode toggle при сохранённой работе | Только preferences write | Scores/min/max/rules/snapshots/statistics не пересчитываются |
| Min=18, max=30 | 18 и 30 включительно; 17,99/30,01 reject в ON | Pending и revision без score; ноль не подставляется |
| Min=0, max=30 | 0 — допустимый реальный балл | Отличим от NULL/нет оценки |
| Max=int64 limit, следующий cent | Предел допустим в ON; +0,01 reject до SQL write | Нет wraparound или silent float cast |

**QA-A-REV-02:** mode ограничивает только новые/изменяемые числа, вводимые
преподавателем. Выбор уже сохранённой rule и служебное копирование её
**неизменённых** min/max в immutable Review/result snapshot не являются
новым вводом границ: разрешены при OFF и ON, точно и без округления. Новая оценка
в Review всё равно проверяется по текущему mode и inclusive выбранным bounds;
при OFF score=24 под exact rule 18,25–30 допустим, score=24,75 — нет, даже если
он совпадает с прежним результатом. Создание самих fractional bounds в новой
rule или изменение прежних границ требует ON; сохранение unrelated fields
без изменения границ оставляет их прежними.
Нельзя прогонять неизменённый rule snapshot через валидатор нового ввода границ
или включать настройку автоматически ради snapshot.
Grade numeric score/max согласованы с этим result snapshot; min проверяется
по выбранной rule, не вводится заново для Grade. Settings не меняют
TRADITIONAL label и PASS_FAIL. Decimal parsing принимает один comma или dot;
mixed separators/лишняя точность возвращают validation error. Канонический
новый display убирает только незначащие нули; historical compatibility display
не обрезает существующие значащие цифры. Новое число не пишется в legacy REAL.

### Lossless compatibility для REAL

Миграция **не** делает `ROUND(score,2)`, REAL×100→INTEGER или конверсию всего
исторического каталога в якобы исходные decimal значения. Legacy score/max
остаются в исходных колонках вместе с NULL/metadata. Compatibility DTO имеет
tag `LEGACY_REAL`, source table/row/field, binary64 payload (hex/8-byte encoding
при необходимости snapshot) и original numeric value. Это сохраняет наблюдаемое
binary значение, а не потерянную строку ввода/десятичную точность.

Например REAL с наблюдаемым `repr` 24.751 показывается без усечения до 24,75
с признаком legacy; для 0.1 shortest roundtrip text `0,1` не доказывает точную
исходную десятичную запись. Technical details доступны в details, без вывода
binary noise вместо обычного балла. Existing >2 digits/вне int64 диапазона
сохраняются; upgrade не отказывает из-за невозможности represent их как cents.
Детальная проверка `float.hex()`/binary64 и NULL до/после даёт lossless evidence.

Legacy-only stats остаются на прежней семантике и не меняются при toggle.
Для mixed exact/legacy adapter не переводит exact в float: сравнения legacy
через точный binary rational (`as_integer_ratio`), суммирование с пометкой
происхождения. Такой результат не называется восстановленной decimal accuracy.
Новый/изменённый преподавателем min/max при создании rule вводится по текущему режиму;
legacy max не переписывается и не превращается автоматически в exact bound.
Legacy min отсутствует: хранить unknown, не выдавать backfill 0 за согласованный
индивидуальный min. Пока old rule incomplete, новая numeric review требует
явно созданную полную rule; «прежние критерии» показываются с ограничением,
не дополняются выдуманным min.

## 5. B5: сдача, immutable проверка, Grade и актуальный результат

Предложение минимальной новой границы: новая реальная сдача записывает
immutable `Attempt(result=PRESENTED, score=NULL)` и submission evidence binding.
Её `occurred_at` — действительное время сдачи, recording time отдельно.
Новая `Review` имеет concrete `submission_attempt_id`, `review_seq`, result,
reviewed_at, recording UTC, optional comment, selected rule и result snapshot.
Review/result/Grade записываются атомарно, unique submission/review_seq и
idempotency key защищают повтор; stale rule/plan требует новый preview.
Повторная проверка меняет review_seq, **не** attempt_no и **не** число сдач.

Legacy `grades.attempt_id` и его UNIQUE/consistency/immutable triggers сохраняются.
Для новых проверок предлагается отдельный concrete `ReviewGrade(review_id UNIQUE)`
с тем же tagged Grade contract и FK к Review, не вставка Grade к score-less
PRESENTED Attempt. Read DTO указывает binding kind `legacy_attempt`/`review`;
не использовать polymorphic owner columns без FK. Новый numeric result/max
берётся только из выбранного review snapshot; Grade не независимый источник
status/score. Review из другой работы/студента и review без saved submission reject.

| Событие | Preconditions | Состояние / score после fold | Нумерация |
|---|---|---|---|
| Реальная новая сдача PRESENTED | StudentWork сохранён, context/enrollment проверены | SUBMITTED, score=NULL | Следующий attempt_no = max всей legacy/new Attempt history, включая архив, +1 |
| Review NEEDS_REVISION | Saved submission, score=NULL | REVISION_REQUIRED, score=NULL | Только новый review_seq |
| Review ACCEPTED | Saved submission; если numeric — inclusive выбранные min/max | ACCEPTED, score выбранной проверки или NULL | Только review_seq |
| Review SCORED | Saved submission; numeric обязателен; состояние этой сдачи перед review по resolver только SUBMITTED или ACCEPTED; при REVISION_REQUIRED reject | Score заменяется; допустимый status сохраняется, нового ACCEPTED не создаётся | Только review_seq; reject не пишет Review/Grade/счётчики |
| Review REJECTED | Для нового Homework запрещено; для других типов status-neutral по legacy contract | Status/score не меняются; отрицательная review остаётся в истории | Только review_seq |
| Review COMMENT_ONLY | Saved submission, без нового score | Status/score не меняются | Только review_seq |
| Повторная review той же сдачи | Тот же submission FK; новые правила показаны | Fold следующей review; прежняя immutable | attempt_no неизменен |
| Новая пересдача студента | Новый подтверждённый факт сдачи | Новая PRESENTED сбрасывает current score в NULL | Новый attempt_no; Grade не копируется |

PRESENTED относится к submission, не к review. Новая pending сдача без завершённой
содержательной проверки имеет score=NULL. SUBMITTED после допустимого SCORED
означает численно проверенную, но ещё не принятую работу: это не pending review
и не ACCEPTED, долг остаётся открытым. В новом REVISION_REQUIRED current score
всегда NULL; legacy PRESENTED/NEEDS_REVISION с сохранённым score не очищаются.
Исходные [ADR-009/010](../decisions.md) и StudentWorkProgress для legacy остаются
прежними: PRESENTED/NEEDS_REVISION/ACCEPTED заменяют status и score, SCORED меняет
score без автоматического ACCEPTED, REJECTED/COMMENT_ONLY нейтральны.

**QA-A-REV-01:** новая Review SCORED из REVISION_REQUIRED запрещена, даже при
score в диапазоне. Для завершения доработки преподаватель явно записывает
ACCEPTED с подходящим Grade/score и выбранной rule. Также SCORED недопустим для
NOT_STARTED без saved submission. Preconditions оцениваются на той же сдаче
перед новой review (по её anchor и предыдущим review_seq), а не по current
status другой, более новой сдачи. При конфликте ожидаемой review revision
проверяется fresh state, не создаётся обходной Attempt и нет partial commit.

| Документированный future scenario | Результат нового Review-контракта | История/нумерация |
|---|---|---|
| S1 → NEEDS_REVISION → попытка SCORED(24), rule 18–30 | Reject; REVISION_REQUIRED, current score=NULL и долг прежние | Нет новой Review/Grade/Attempt, review_seq не расходуется |
| S1 → NEEDS_REVISION → явный ACCEPTED(24), rule 18–30 | Разрешён при остальных guards; ACCEPTED, score=24, долг H1 закрыт | Новая immutable review, attempt_no неизменен; module закрывается только при всех обязательных ACCEPTED |
| S1 → SCORED(24) в SUBMITTED | Разрешён, current score=24, status=SUBMITTED; нового зачёта нет | Только review_seq; долг остаётся |
| S1 NEEDS_REVISION, затем новый S2 PRESENTED, попытка SCORED(24) для S1 | Reject по state S1, несмотря на SUBMITTED у S2 | Для S2 допустимый SCORED отдельно; никакой подмены target anchor |
| Legacy-only Attempts NEEDS_REVISION → SCORED(24) | Прежний fold REVISION_REQUIRED/24 сохранён в tagged compatibility | Никакой миграционной очистки/перенумерации или новой записи |

Сценарии — спецификация будущих тестов, не новые исполняемые tests этого PR.

Предлагаемый unified resolver группирует события по существующему attempt_no:
legacy Attempt применяется как прежде; к явно bound submission применяются
reviews по review_seq. Группы fold в порядке attempt_no, а не reviewed_at или
occurred_at. Новая проверка старой сдачи после появления новой сдачи меняет историю
старой группы, но не вытесняет более новую PRESENTED. Backdated timestamp не
меняет progression. Legacy-only output должен побитно/семантически совпадать
с прежним status/score/max source/raw attempt_count. Для новых Review resolver
использует таблицу с запретом REVISION_REQUIRED→SCORED; legacy события применяются
с прежним fold, не проходят новые ограничения ретроактивно. Запрет проверяется
атомарно **до append** Review/Grade, а не маскируется преобразованием при чтении.
Required-work/debt DTO проверяет explicit ACCEPTED текущего результата; наличие
score или Grade без принятия не закрывает долг/модуль. Детали — [B2](#b2-student-debt).

Новый `submission_count` считает только evidence-backed новые/подтверждённые
сдачи; `review_count` отдельно. Legacy raw attempt_count не переименовывать
в достоверное число сдач. Нет доказательства — unknown/compatibility, не 0 фактов.

### Grade validation

| Kind | Допустимые поля | Binding / результат |
|---|---|---|
| NUMERIC | Новый score по mode B4 и min<=score<=max; max и min взяты точно из выбранной сохранённой rule, неизменённые bounds snapshot разрешены и при OFF; passed/label NULL | Grade.score/max точно равны Review.score/max; SCORED требует numeric и допустимый prior state; NEEDS_REVISION не может иметь numeric score/Grade; ACCEPTED может иметь numeric |
| PASS_FAIL | passed bool; score/max/label NULL | true только ACCEPTED; false только NEEDS_REVISION/REJECTED, как existing `_grade`/SQL; Homework REJECTED запрещён |
| TRADITIONAL | Непустая исходная label; numeric/passed NULL | Не вводить новую шкалу/преобразование в баллы; Grade не задаёт зачёт автоматически |
| Нет Grade | Отдельный допустимый факт, без фиктивного нуля | Current result берётся из Review/legacy Attempt, не из наличия Grade |

Min/max — индивидуальные для работы/rule; Item results не суммируются автоматически
в whole score. Различие outcome и score/Skill evidence прежнее. Полный queue UI,
returned teacher file, регистрация сдачи и minimal attachment preview — QA-B;
QA-A фиксирует и реализует только необходимую независимую scoring/review основу
в будущих score PR, без новой очереди и автоматической отправки.

### Legacy evidence, которое нельзя «достроить»

Каждая legacy Attempt остаётся исходным событием с собственными result/score/time.
PRESENTED — явный recorded presentation marker, но его время не становится датой
отдельной проверки. ACCEPTED/SCORED/NEEDS_REVISION/REJECTED дают result evidence,
но не доказывают отдельные submission и review timestamps/число реальных сдач.
COMMENT_ONLY не submission evidence; attachment ownership не доказывает новую
сдачу. Ни соседство номеров, ни Grade, ни date similarity не являются основанием
привязать legacy review к предыдущей PRESENTED.

Автомиграция новых Review/Submission evidence для неоднозначных rows отсутствует.
Учитель может явно подтвердить/сопоставить существующую Attempt как submission
через additive evidence binding без изменения attempt_no/occurred_at; неизвестное
время отдельной сдачи остаётся unknown. Последующий review использует этот FK.
Не создавать dummy Attempt ради переноса Grade; старые FK/UUID не переносить.

## 6. B6: версии критериев и три обязательных сценария

`ScoringRuleVersion` принадлежит конкретной работе, immutable UUID/version,
min/max exact или tagged legacy-incomplete, критерии и effective recording order.
Current rule pointer revisioned; old Assessment.max/content lock сохраняется.
На новой submission фиксируется current rule binding (rule UUID, запись/дата
действия), независимо от возможного backdated submitted_at. Если правило меняется
до проверки/перепроверки, UI показывает обе версии и требует явного выбора.
Review фиксирует выбранный rule UUID и полный immutable snapshot min/max/criteria,
не read-time lookup нынешнего max. Concurrent rule change после preview вызывает
conflict, не скрытый выбор. Точная дата сама не доказывает, какие правила были
показаны преподавателю в прошлом; legacy binding unknown не угадывается.

| Синтетический сценарий | До изменения | После current R1: 18–30 → R2: 20–40 | Сохранность |
|---|---|---|---|
| Pending сдача S1 | S1 записана под R1, review отсутствует | Первая review явно выбирает R1 (18 допустимо) или R2 (18 reject); показать выбор до save | S1/no/time не меняются; snapshot выбранной rule в Review |
| Пересдача S2 | S1 checked ACCEPTED 24/30 под R1 | Новая реальная S2 после смены имеет R2; новая проверка показывает R2, 32/40 допустимо | S1 Review остаётся 24/30; S2 получает следующий номер только за сдачу |
| Повторная проверка S1 | S1 Review1 ACCEPTED 24/30 под R1 | После смены явный выбор R1/R2; Review2 ACCEPTED 32/40 под R2 | Review1 immutable; no новых Attempt; если S2 уже есть, Review2 S1 не вытесняет результат S2 |
| Доработка S1 после смены rule | S1 Review1 NEEDS_REVISION, score=NULL под R1 | Выбор R1/R2 не разрешает SCORED(24) из REVISION_REQUIRED; только явный ACCEPTED(24) по выбранной полной rule и остальным guards | Reject без записи или новая immutable ACCEPTED review; attempt_no прежний, debt только по ACCEPTED |
| Сохранённая R3 18,25–30, mode OFF | R3 уже exact, S1 ещё SUBMITTED | Новая целая оценка 24 под явно выбранной R3 допустима, min/max копируются без нового fractional input; новая 24,75 reject | Exact snapshot 18,25–30 сохранён независимо от toggle; прежние Review/Grade не меняются |

Новая сдача после изменения использует current R2. Если правила ещё раз меняются
пока она pending, применяется тот же явный выбор между её binding и новой current.
При выборе legacy неполных критериев отображаются сохранённый max/unknown min
и причина невозможности новой numeric проверки без полного определения rule.
Исторические snapshots до внедрения versioning не реконструируются из нынешнего
Assessment.max или library metadata.

## 7. Migration mapping по существующим источникам

Это план будущих additive revisions, **не выполненная миграция**. Target names —
предложения; source names/fields существуют в base v9. Все старые UUID, values,
created/updated/revision/deleted_at и FK сохраняются, если ниже явно не описан
новый mapping. Старые records не переименовываются/переидентифицируются.
New maps имеют concrete FK, UNIQUE source scope, deterministic UUIDv5 из kind
и source UUID (для плана также offering UUID); никаких ключей из title.

| Источник → целевой контракт | Сохраняемые IDs/значения | Преобразование / compatibility | Неоднозначность | Проверка сохранности |
|---|---|---|---|---|
| `courses`; `work_programs.course_id/title/version/notes` → Content/Version + LegacyProgramMap | course/program UUID, title/version literal, metadata | Одна независимая content/version на source program; freeze imported snapshot, source refs; legacy table остаётся | Version string не история; утраченные редакции неизвестны | Cardinality map 1:1 по source program, no title merge, row equality |
| `work_programs.direction/faculty` → Direction/ProgramDirection + legacy attributes | Исходный текст без изменения | Полный однозначный code → link; остальные raw, explicit reconciliation | Строка может быть code/name/несколько кодов | Raw equality, duplicate/scope checks, пустой/свободный текст не теряется |
| `course_offerings.work_program_id/term_id/course_id/group_id`; `work_programs.term_id/semester/first_week_start/weeks/week_utc_offset_minutes`; `academic_terms.starts_on/ends_on/week_utc_offset_minutes` → SemesterPlan/binding | Все offering/term/group/program IDs, календарные значения и archived state | Один plan на source offering, календарь из связанной программы; term отдельно; без программы явный compatibility контекст | Номер курса unknown; program vs term calendar конфликт не исправляется автоматически | Offering scope, exact dates/weeks/offset, no clone on reopen, оба источника видны |
| `program_modules.work_program_id/start_week/end_week/sort_order`; `module_topics.module_id/topic_id` → version module + PlanModule/topic placement | Source module/link/topic UUID и ranges | Content placement со source map; отдельный календарный module на offering/module | Ordinal unknown, baseline только на миграции | Все module/topic pairs, source IDs, range/overlap guards и tombstones |
| `program_works.definition_id/module_id/planned_issue_week/planned_due_week/issue_date/due_date/sort_order` → content work + PlannedAssessment | ProgramWork/definition/module UUID, order/weeks/dates | Новый plan work per offering/source work; даты сохраняются как плановые, actual не выводится | Могут отличаться от выданного Assessment | Mapping coverage, две группы без общих mutable calendar rows, dates/order equality |
| `program_topics/program_skills/program_materials/program_literature/program_attachments`, `homework_definitions`, `definition_problems/definition_topics/definition_skills` → content refs/snapshots | Все link/source/file UUID, captions/order/role, библиотечный text/type | Snapshot существующего content плюс source revision, no bytes copies; не создавать nonexistent definition min/max | Старый mutable content не даёт утраченный historical snapshot | FK/link cardinality, literal content, FileAsset SHA-256, deleted links сохранены |
| `assessments.offering_id/program_work_id/homework_definition_id/type/number/title/description/max_score`; `student_works` → issued identity/scoring compatibility | Assessment/StudentWork/student UUID, metadata и facts | Additive plan→assessment map; standalone Assessment получает собственную planned identity, не fake definition/student work | Issued due/week могут отличаться от ProgramWork | Все facts/UUID equality, no ghost StudentWork, duplicate planned/issued association reject |
| `assessments.issued_at/due_at/planned_issue_week/planned_due_week`; `program_works.issue_date/due_date` → Issuance provenance + DeadlineSpec | UTC integer microseconds дословно, original plan date/week | issued_at=legacy_ambiguous; nonnull due_at=EXACT_INCLUSIVE; нет exact → week fallback; planned date сохраняется отдельно | Нельзя вывести actual issuance; conflicting dates не перезаписываются | Timestamp equality, exact precedence, boundary fixtures, raw provenance, no fabricated event |
| `lessons.course_offering_id/lesson_date/planned_date/planned_week/module_id/cancelled/cancellation_reason`; `attendance/enrollments` → calendar reader/context | Lesson/attendance/enrollment UUID, фактические и плановые даты, cancel/state | Additive lesson↔plan-module map; historical module_id остаётся; actual занятия/посещаемость не переносятся | LocalDate не exact instant; старое участие не угадывается | Row/FK/metadata equality, прежние attendance denominator, no fictitious lesson |
| `attempts.student_work_id/attempt_no/occurred_at/result/score/max_score/comment`; `grades.attempt_id/kind/passed/score/max_score/label` → LegacyResult + evidence-aware resolver | Все Attempt/Grade IDs, номера, значения, archive metadata | Только compatibility read; no generated submission/review/Grade; explicit evidence binding позже | Одна запись не доказывает две даты/число сдач/выбранное правило | Legacy fold status/score/max/raw count равны прежним; Grade consistency; max+1 numbering |
| `assessment_items.max_score`, `attempt_item_results.score/max_score/outcome/attempt_id/assessment_item_id`; `attempt_skill_results` → immutable granular evidence | Все item/result/skill IDs, scores/outcomes/links | Старые результаты не пересчитывать по whole rule; concrete review item binding проектировать отдельно при необходимости | Whole score не сумма items, outcome не score | Cross-assessment guards, active uniqueness, archive и source precision сохраняются |
| REAL `assessments.max_score`, `assessment_items.max_score`, `attempts/grades/attempt_item_results.score/max_score` → LEGACY_REAL union / новые exact cents | NULL или original binary64, source row/field | Lossless existing columns; payload snapshot для нового compatibility reference; без массового ROUND/cast | Исходная decimal text/scale и min не восстановимы | NULL/type/float.hex сравнение, >2 digits/huge values survive, toggle no fact writes |
| `assessment_problems.statement_snapshot/source_revision`; `student_problem_assignments.title_snapshot/statement_snapshot/teacher_snapshot_json/source_revision`; `ticket_sets.criteria_json`; `ticket_problems` text/teacher snapshots, file links | Assignment/ticket/problem/file UUID, text/JSON literal и revisions | Сохранить snapshots как исходные immutable источники; новая rule snapshot независима | Генераторные criteria не являются scoring rule/min/max | Exact text/JSON/links equality, teacher data не становится student output |
| `file_assets`, `attempt_attachments`, `student_problem_files`, остальные concrete attachment links → прежние storage/backup facts | UUID/storage_key/size/SHA-256 и immutable bytes | Никаких reimport/dedup/переназначений; новый review owner только отдельным FK позже | Filename не submission/review evidence | Все active/archived/detached/shared files, byte hash и FK integrity |
| `preferences.json` (JsonPreferences) → fractional bool default OFF | active_term/theme/recent/sidebar/table widths и unknown keys | Missing key читается false; schema upgrade не пишет JSON; явный toggle atomic merge | Corrupt JSON имеет существующий fallback, не восстанавливать «предпочтение» по fractional history | Reopen default/explicit bool, unrelated keys equality, failed replace no loss |

### Fresh, populated, повторное открытие и откат

Для дополнительного B2 migration не вычисляет mandatory/closed из даты окончания
term, наличия Attempt/score или количества ProgramWork: источников обязательности
и индивидуального закрытия в v9 нет. Future required-work binding создаётся явно;
legacy unknown сохраняется. Поздние события T2 относятся к source work/offering T1,
без новой копии Assessment, изменения enrollment history или календаря группы.

1. Fresh: upgrade v1→v9→будущая revision, пустые новые таблицы без fake учебных
   фактов; preference missing=false, первый план только по действию пользователя.
2. Populated: только synthetic копия; inventory всех source rows/FK/schema objects,
   archived rows и file hashes. Backfill из actual IDs, не из названий; current
   dates issued Assessment при конфликте не заменять ProgramWork schedule.
   Baseline PlanRevision сохраняет оба источника и effective current deadline;
   provenance `migration_baseline`, первоначальный до-миграционный план unknown.
3. Reopen/repeated upgrade: Alembic revision + UNIQUE source maps; никаких новых
   content/plan/event/Attempt и no JSON migration side effect. Immutable imported
   baseline не обновляется из изменившейся source table на каждом запуске.
4. Late fault: DDL/backfill/map/snapshot/revision в одной настоящей SQLite transaction
   с foreign_keys ON; rollback возвращает row inventory, schema objects и old
   Alembic version. Не отключать guards/FK глобально ради записи новой модели.
   При необходимости нового trigger/rebuild — отдельная additive revision с
   exact old objects preservation; historical v0001–v0009 raw bytes неизменны.
5. Архив: include_deleted, archived programs/offerings/Attempt/Grade/file links
   также сохраняются; новые maps не воскрешают архив. No physical cascade/purge.
6. Rollback релиза: downgrade с удалением новых фактов запрещён. Без новых записей
   можно восстановить проверенный pre-upgrade backup в отдельный пустой профиль
   совместимым релизом. При новых exact/review facts старый бинарник не открывает
   новую schema; не обещать lossless возврат его записи в REAL. Restore не меняет
   исходный профиль и не подменяет version marker.

### Backup/restore каждого нового schema head

Текущий verifier принимает только `0009_daily_workflow`/точный schema fingerprint
и current app version; это ограничение фактического кода, не готовая поддержка
QA-A. В каждом будущем schema PR одновременно обновляются canonical fingerprints
и tests new-head roundtrip всех таблиц/maps/snapshots/ReviewGrade и всех files,
включая tombstones. Новый backup содержит exact cents без float conversion.

Предлагаемый compatibility path старого v9 archive: allowlist точных поддержанных
app/schema revision+fingerprint; verify оригинального snapshot и bytes, staging
вне активного профиля, upgrade staging, повторные FK/integrity/new-schema checks,
лишь затем atomic publication в пустой destination. Без отдельно реализованного
и проверенного allowlist нужен соответствующий старый релиз для verify/restore
в пустой профиль с последующим обычным upgrade новым релизом. Не spoof schema,
не in-place migrate источник/архив и не ослаблять verifier для unknown future DB.
Сбой позднего upgrade/restore оставляет исходный архив/профиль и destination intact.

Preferences по действующему ZIP v1 исключены и остаются исключены: новый профиль
после restore начинает OFF, даже если historical scores fractional; они всё равно
видны полностью. Restore в отдельный профиль не копирует preference из исходного.
Обычный upgrade/reopen существующего профиля сохраняет явно выбранный bool.
Изменение backup format для переноса preferences в этот контракт не входит.

## 8. Следующий implementation PR и проверки

**Предлагаемый ближайший небольшой scope — QA-A-PR-02: directions foundation
(ST-QA-002).** После technical review этого документа и отдельного разрешения
реализации: Direction + ProgramDirection concrete repositories/ports, additive
revision, NFC/trim/casefold code uniqueness и только exact unambiguous import, сохранение
raw direction. Без большой формы, content/calendar/review/scoring изменений.
План из 10 PR не утверждён; это предложение scope, не автоматически начатая работа.

Prerequisites: review mapping/direction normalization, выбранный FK bridge к
legacy program с будущим explicit content map, актуальный main после отдельного
merge docs, backup поддержки нового head в том же PR. Existing actual source
`work_programs.direction` остаётся доступным; source title/UUID не меняются.

Будущие tests/exit: три синтетических codes одной программы, optional names,
trim duplicates/empty reject, unknown/free text без heuristic split, разные
одноимённые программы без merge; populated v9→new с archived/links/REAL/history
equality, fresh/reopen/no dup, late rollback DDL/backfill, frozen v1–v9 hashes,
FK/integrity и new-head backup/restore всех rows/bytes. Existing workflow/UI
сохраняется; required quality/safety, relevant/full regression, architecture
и repository checks зелёные на implementation HEAD. Это foundation, не закрытие
всего ST-QA-002 без multi-select UI/manual acceptance.

В QA-A-PR-09 необходимы exact storage/range/validation, Review/ReviewGrade binding,
rule selection и legacy resolver. В QA-A-PR-10 — Settings fractional toggle,
сохранение bool, unsaved validation, integer default и historical display во всех
DTO/journal/student/analytics/reporting views. Полный review queue остаётся QA-B.

Существующие подходящие тесты основы, **прочитаны, NOT RUN в этом PR**:

| Файл | Существующие сценарии / будущие расширения |
|---|---|
| [test_domain.py](../../tests/unit/test_domain.py) | `test_history_order_by_number_not_date`, `test_rejected_comment_preserve_accepted_result`, `test_scored_does_not_mean_accepted`, `test_grade_variants_and_validation`; дополнить evidence-aware fold без изменения legacy output |
| [test_application.py](../../tests/integration/test_application.py) | `test_invalid_grade_rolls_back_attempt`, `test_next_attempt_number_includes_deleted_facts`, `test_concurrent_attempt_number_assignment`; новые review не увеличивают номер, поздняя ошибка атомарна |
| [test_program_migration.py](../../tests/integration/test_program_migration.py) | `test_populated_v6_copy_program_mapping_files_tickets_reopen`; новые v9 maps без title merge/ordinal inference |
| [test_migration_evolution.py](../../tests/integration/test_migration_evolution.py) | `test_v1_database_copy_preserves_all_phase2_rows_and_schema`, `test_fresh_database_to_latest_and_reopen`; все будущие additive heads |
| [test_backup_recovery.py](../../tests/integration/test_backup_recovery.py) | `test_complete_backup_verify_restore_preserves_every_fact_schema_and_byte`, `test_schema_spoof_with_supported_revision_is_rejected`, `test_restore_failure_has_no_partial_root`; new schema и supported legacy staging |
| [test_user_data.py](../../tests/unit/test_user_data.py) | `test_corrupt_preferences_fall_back_and_selection_is_persisted`; bool default/persistence, unrelated keys и failure, backup exclusion |

Будущая QA-A acceptance дополнительно покрывает date/exact равенство и ±1µs,
выход срока из модуля/семестра с confirm/cancel/stale rollback, early issuance,
две группы и два семестра с одной V1, content freeze/V2, decimal parse/overflow/
lossless REAL, NULL vs 0, empty integer interval, pending/resubmission/re-review
под R1/R2. Никаких новых tests в текущем documentation diff.
Дополнительно специфицированы future scenarios QA-A-REV-01/02: reject
REVISION_REQUIRED→SCORED без записи, явный ACCEPTED(24) с прежним attempt_no,
legacy fold unchanged, OFF integer score с unchanged fractional rule snapshot,
OFF reject new fractional score/bounds и no-integer interval. B2: долг H1 из T1
при active T2, два студента с разным closure, несколько обязательных работ,
late submission без deadline change, отдельный confirmed reschedule, ended
enrollment и explicitly archived context как разные guards. Полный UI/очередь
и registration долгов — QA-B; mandatory/closure schema до review PROPOSED.

## 9. История документационного review

2026-10-11, после review `3649afaee48be28d27f81ac41aff86087d594636`:
добавлено новое продуктовое уточнение B2 об индивидуальном долге T1 в T2 и
explicit ACCEPTED всех обязательных работ для закрытия модуля. Первоначальное
согласование срока после семестра сохранено; индивидуальный debt не объявляется
известным до этого дополнения. QA-A-REV-01 устраняет разрешённое ранее таблицей
новых Review сочетание REVISION_REQUIRED/числовой score после SCORED;
QA-A-REV-02 разделяет новый numeric input и копирование unchanged rule bounds.
Legacy history/REAL/baseline не переписываются. Это исправления контрактов
документационного PR #2, не реализация и не новые ST-QA ID/закрытые acceptance.

Для текущего PR: сверка B1–B6/Grade examples/source fields, 30 ID/приоритетов/
порядка матриц с baseline, относительных ссылок, Markdown-only diff,
`git diff --check`, existing repository-safety worktree/index/history/identity.
Ordinary automatic quality/repository-safety нового HEAD фиксируются в PR/отчёте;
старые CI results не выдаются за новые. Local pytest/Ruff/package, application,
migration и Windows/manual acceptance **NOT RUN**; workflow_dispatch/full_windows
не запускать. B7–B9 остаются последующим QA-B/C. Продуктовых узких blocker после
дополнения B2 нет; technical proposals ожидают review, не implementation acceptance.
