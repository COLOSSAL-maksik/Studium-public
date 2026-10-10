# Backlog Studium

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
