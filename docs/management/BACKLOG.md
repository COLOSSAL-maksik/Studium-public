# Backlog Studium

## Выбранное окно — Учебная программа, 2026-10-16

ST-PROG-001–012 зарезервированы этим заданием; конфликтующих ID в базе нет.
Каждая строка реализована и имеет собственное evidence в
[матрице окна](../program-window.md#матрица-реализации-и-проверок).
Локальные целевые проверки, package и safety PASS; exact-HEAD CI — в PR.
Ручная Windows-приёмка PENDING.
Связаны ST-QA-002/003/006/010/011/013/021/023/030; прежние ID не перенумерованы.
Остаток только этого окна: Windows Light/Dark/DPI/keyboard и приёмка владельца.
Полный UX фактического проведения/автоматического отставания — последующее окно.

## Действующий backlog принятой базы — 2026-10-12

База [PR #3](https://github.com/COLOSSAL-maksik/Studium-public/pull/3),
`3eff0293f8540fa848a3175dd15ad34994268235`, принята владельцем с остаточными
замечаниями ([ADR-053](../decisions.md#adr-053)). Изменение этих остатков сейчас
не выполняется; первый модуль для отдельной задачи ещё не выбран.

**Тип записи:** ограничение — известная граница текущего поведения; проверка —
недостающее evidence, а не доказанный дефект; требует описания — сообщение владельца
без конкретного воспроизведения. Новые подтверждённые дефекты добавляются после
описания сценария на выбранном модуле, с исходным ST-QA ID, если требование прежнее.
Нового defect ID для переописания старого требования или проверки не создаём.

| Модуль/раздел | ID | Тип и наблюдаемая граница | Ожидаемое поведение | Приоритет | Источник / воспроизведение | Критерий проверки | Статус |
|---|---|---|---|---|---|---|---|
| Библиотека и версии | ST-QA-003 | Ограничение: pre-v11 версия не содержит утраченных problem snapshots; unissued work без них нельзя выдать | Не подставлять текущую библиотеку; новая явная версия/назначение | P2 | [Review report](PR3_REVIEW_FIXES.md), ADR-051 | Synthetic legacy copy: старые UUID/JSON прежние, явный отказ, новая версия выдаётся | Ограничение сохранено |
| Материалы и вложения | ST-QA-003 | Ограничение: legacy shared files без исторического snapshot показывают прежний compatibility view/current links | Не объявлять current links историческим снимком; новые выдачи используют frozen file IDs/hashes | P2 | Review report, ADR-051 | Reopen/restore legacy и новой версии; сравнить file IDs/hashes и student whitelist | Ограничение сохранено |
| Темы/навыки и версии | ST-QA-003 | Ограничение: saved V1 удерживает taxonomy UUID даже без группы; V2/archive плана не освобождают зависимость. Уже архивированные pre-v12 endpoints не восстанавливаются | Archive заранее отказывает со списком dependencies; старый повреждённый snapshot не заменяется живыми связями | P2 | Review report, ADR-052; test_pr3_frozen_taxonomy | Task/definition/family/individual assignment, atomic refusal, UUID, issue V1, reopen/backup | Ограничение; frozen archive defect исправлен |
| План семестра | ST-QA-003/010/011 | Ограничение: пересечения retained/new modules требуют согласования календаря; retained assignments блокируют смену ordinal | Preview/refusal без частичных записей; исходные bindings/facts не переносить между семестрами | P2 | Review report, ADR-051; test_pr3_review | Cancel/stale/conflict; согласованный non-overlap apply; независимая группа | Ограничение сохранено |
| Регистрация и старые долги | ST-QA-011/027 | Ограничение: явно deleted исходный контекст требует подтверждаемого восстановления; archived term допускается | Первая поздняя сдача сохраняет исходные UUID/enrollment; не выполнять auto-restore/re-enroll | P1 (027), P2 (011) | ST-PR3-001 regression mapping в Review report | WITHDRAWN/COMPLETED, отсутствующий StudentWork, T1→T2, restore/cancel и file rollback | Политика сохранена; late-submission defect исправлен |
| Исторические даты и баллы | ST-QA-013/029/030 | Ограничение: неизвестные legacy actual timestamps/ordinal/min не достраиваются; REAL/NULL сохраняются | Показывать unknown без выдуманной просрочки/зачёта; exact и REAL без потери precision | P1 (029/030), P2 (013) | ADR-050/051 и Review report | Synthetic legacy/fractional/unknown boundary cases, неизменность старых фактов | Ограничение сохранено |
| Backup/recovery | OPEN-011 | Ограничение совместимости: старый ZIP требует matching прежнего candidate/release и затем upgrade отдельного профиля | Не подменять manifest/schema и не ослаблять unknown-head/fingerprint guards | Не назначен | ADR-051/052, unified checklist | Synthetic ZIP v10/v11: compatible restore → v12 upgrade, rows/bytes и guard failures | Compatibility ограничение; local backup реализован |
| Аналитика и история коррекций | OPEN-002/011 | Исторический остаток manual overrides/correction audit и полной audit/purge политики за пределами реализованных QA snapshots/PlanHistory | Конкретный новый scope уточняется в выбранном модуле; текущие формулы и immutable facts не переоткрывать | Не назначен | [Архитектурные OPEN/ADR](../decisions.md) | Описать конкретный сценарий и критерии до отдельной реализации | Требует module specification; не подтверждённый дефект |
| Функциональные сценарии/UI | ST-QA-001–030 | Проверка: полного ручного прохода владельцем по 30 строкам нет; developer/CI evidence отдельно | Фиксировать результат каждого проверенного сценария и SHA; не ставить массовый manual PASS | По исходному ID | [Manual checklist](../qa-all-30-manual.md), implementation matrix | Выполнить относящиеся к выбранному модулю сценарии, включая нужные Light/Dark/DPI/keyboard checks | Manual PENDING; не блокирует принятие базы |
| Windows/distribution | Native Windows/manual acceptance (существующая запись) | Проверка: full_windows pytest, non-admin interactive client VM и ручные PDF/DPI acceptance не выполнены | Native CI 17 PASS/build/lifecycle отделять от полного Windows и manual evidence | Не назначен | [Состояние и run context](PROJECT_STATUS.md), checklist | При отдельной задаче фактически выполнить нужные проверки и записать среду/результат | NOT RUN/PENDING; не доказанный дефект |
| Остаточные замечания владельца | Привязать к исходному ST-QA при описании | Требует описания: владелец сообщил недоработки; конкретных текстов/скриншотов в решении нет | Не выдумывать ошибки; собрать наблюдаемое/ожидаемое поведение и воспроизведение выбранного модуля | Требует уточнения | Решение владельца 2026-10-12, ADR-053 | Конкретный module scope, existing/new issue mapping, воспроизведение и acceptance | Требует описания при проверке соответствующего модуля |

ST-PR3-001–004 и frozen Topic/Skill сохраняются как исправленные в
[отчёте и regression mapping](PR3_REVIEW_FIXES.md). Нового воспроизведения их
неисправности нет; они не возвращаются в очередь. OPEN-009 не переоткрывает
реализованные typed deadlines/offset/SLA ADR-050; иные сценарии требуют отдельного
описания. License/repository решения OPEN-006 и Bender scope не изменены.

## История backlog до принятия базы

Таблицы QA-A–D и 10-PR proposals ниже не являются действующей очередью.

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


## QA-A — актуальное дополнение 2026-10-11

| Задача | Состояние | Следующий результат |
|---|---|---|
| B1–B6 product contracts | Согласованы; B4 integer default + fractional 2 digits/OFF, B2 confirmed deadline после семестра | [Технический review contracts/mapping](QA_A_CONTRACTS.md), не повторная продуктовая анкета |
| Documentation scope QA-A-PR-01 | Документы подготовлены по actual main `b620ef3635c2965ad3630bae15d00d1b7bd9a82d`; implementation/manual NOT RUN | Один docs PR; actual quality/repository-safety на final HEAD, отдельный review/merge владельцем |
| Ближайший implementation | Не начат; предложен PR-02 directions foundation, 10-PR plan не утверждён | Отдельное задание после technical review; concrete FK/code import, raw preservation, backup/new-head tests |
| Score foundation/UI | PR-09/10 — предложения, не созданы | Int64 exact cents/range, mode validation/ReviewGrade/rule snapshots; затем сохраняемый Settings toggle/unsaved validation/historical display |
| B7–B9 | Не решаются в QA-A docs | QA-B queue/summary и QA-C structured answers |

Min уже решён. Исходные 30 требований и их статусы/приоритеты не закрыты;
порядок QA-A → QA-B → QA-C → QA-D сохраняется. Product agreement не является
implementation acceptance. История прежнего backlog ниже сохраняется.

Дополнение review 2026-10-11 после `3649afaee48be28d27f81ac41aff86087d594636`:
[B2](QA_A_CONTRACTS.md#b2-student-debt) — индивидуальные долги T1 в T2,
обязательные работы/explicit ACCEPTED и original offering history (011/029).
Схема required-work/closure и write preconditions ended membership/explicit
archive требуют technical review; полный доступ/регистрация/queue/summary — QA-B,
не новый QA-A UI. QA-A-REV-01/02 устраняются в docs; future score checks включают
reject REVISION_REQUIRED→SCORED и OFF integer score с unchanged fractional bounds.
Directions foundation по-прежнему следующий proposed scope, не начатая работа.

## QA — актуальное дополнение 2026-10-10

[Реестр 30 требований](QA_REGISTER.md) сохраняет номера и приоритеты;
[аудит](QA_AUDIT.md) содержит файлы/functions/tests, delta model/service/UI,
migration safety, dependencies и acceptance каждого ID.

| Задача | Состояние | Следующий результат |
|---|---|---|
| Архитектурный аудит ST-QA-001–030 | Выполнен по коду актуального main; проверки приложения NOT RUN | Документационный review, без реализации/merge |
| QA-A: 002/003/006/010/011/013/030 | Не начато; 5 частично, 2 отсутствуют | Утверждение владельцем [предлагаемого плана из 10 PR](QA_AUDIT.md#qa-a-pr-plan), затем отдельная задача и контракты B1–B6 |
| QA-B: 008/009/012/015/017/027/028/029 | Не начато; 6 частично, 2 отсутствуют | После QA-A; review/queue и minimal preview |
| QA-C: 014/021/022/023 | Не начато; 3 частично, 1 отсутствует | После QA-B; snapshots/answers/tree/picker |
| QA-D: 001/004/005/007/016/018/019/020/024/025/026 | 2 реализованы по коду, 8 частично, 1 отсутствует; manual открыт | После QA-C; Windows visual acceptance |

Все acceptance остаются открытыми. Min не является blocker; B1–B9 —
[конкретные контрактные вопросы](QA_AUDIT.md#blocking-contracts) перед
зависимыми PR. Required checks базы уже подтверждены, см. PROJECT_STATUS;
старые очереди и их исходные статусы ниже сохранены как история.

Уточнение review 2026-10-10: разбиение QA-A на 10 PR ещё не утверждено и требует
утверждения владельца; порядок QA-A → QA-B → QA-C → QA-D сохраняется.
ST-QA-019/020 имеют совместную доработку/приёмку, без взаимного prerequisite.

## История backlog — подготовка самостоятельного репозитория

| Задача | Состояние | Ответственный |
| --- | --- | --- |
| Frozen migration fixtures без old Git objects dependency | Выполнено и принято локально | Codex |
| Native Windows/manual installer, packaged workflow и recovery acceptance | Не проверено здесь | Владелец/Codex |
| License/material rights и remote name | Решено: All rights reserved; все 310 материалов подтверждены; Studium-public | Владелец |
| Actual required safety/quality checks | После отдельно разрешённых Actions | Codex/владелец |
| Second reviewer/CODEOWNERS | Согласуется отдельно | Владелец |
| Учёт residual unpublished Bender работы до переключения | Отдельный continuity gate | Владелец/Jules |
| Bender packaging/tests/CI bootstrap | В отдельном repo после подключения | Jules |
| JSON-RPC stdio API и Studium integration client | Отдельный этап после миграции | Jules/Codex |

Не реализовывать отложенные features без отдельного задания. Existing source
и конфиги не являются доказательством CI, release или manual acceptance.
