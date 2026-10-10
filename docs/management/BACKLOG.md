# Backlog Studium

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
