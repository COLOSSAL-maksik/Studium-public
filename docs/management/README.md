# Управление Studium

## Текущая рабочая база — 2026-10-12

ST-QA-001–030 приняты владельцем с остаточными замечаниями: [ADR-053](../decisions.md#adr-053).
[Состояние/evidence](PROJECT_STATUS.md) отделяет прежние code runs от новых docs checks.
[BACKLOG](BACKLOG.md) — действующие остатки; [ROADMAP](ROADMAP.md) — процесс по одному
модулю. Первый модуль не выбран. Индивидуальные manual PENDING сохраняются,
но не блокируют принятое решение о базе.

## История подготовки и реализации пакета

Предложения и прежние «не начато» ниже не составляют активную очередь.

## Дополнение ST-PR3-002 — frozen taxonomy

На базе `67986fd` archive Topic/Skill, используемых сохранённой версией/назначением,
отклоняется с concrete dependency list. Новая v12 добавляет только два archive
guards; 22 v1–v11 payloads, прежние facts/UUID и SQL guards сохраняются.
27 новых synthetic regressions, итоговый targeted пакет **165 PASS**. Required CI
нового HEAD фиксируется в PR; manual всех 30 — PENDING. [Отчёт](PR3_REVIEW_FIXES.md).
Ниже сохранены предыдущие implementation/verification результаты.

## Review PR #3

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

## Единый пакет ST-QA-001–030

Все 30 требований реализованы в прежней ветке `agent/codex/qa-a-contracts`;
PR #2/B1–B6 и QA-A-REV-01/02 сохранены. QA-A → QA-B → QA-C → QA-D выполнены
как внутренние этапы одного пакета, без промежуточной ручной приёмки и merge.
[Актуальная матрица реализации и проверок](QA_ALL_30_IMPLEMENTATION.md),
[ADR-050](../decisions.md#adr-050--qa-all-30-implementation),
[единый manual checklist и Windows candidate](../qa-all-30-manual.md).
Общая ручная приёмка всех ID — PENDING. Ниже сохранена история подготовки
контрактов; её прежние implementation/10-PR gates заменены пакетным заданием.

## Предыдущие документационные этапы

[QA-A — согласованные контракты и migration mapping](QA_A_CONTRACTS.md),
[ADR-049](../decisions.md#adr-049--qa-a-product-contracts). Актуально 2026-10-11:
B1–B6 согласованы продуктово; B4 integer default + fractional 2 digits/OFF,
B2 разрешает confirmed deadline после семестра. Technical proposals до review;
implementation/manual acceptance не выполнены. 10-PR plan ещё не утверждён,
исходные 30 требований и baseline ниже сохранены.

Последующее review 2026-10-11 уточняет [индивидуальные долги B2](QA_A_CONTRACTS.md#b2-student-debt)
и исправляет QA-A-REV-01/02. Required-work/closure/write policy остаются proposals,
полный UI долгов прошлых периодов — QA-B. Исходные статусы/acceptance не закрыты.

[QA Register — 30 требований](QA_REGISTER.md), [QA Audit и предлагаемый план QA-A](QA_AUDIT.md).
Актуализация 2026-10-10: аудит завершён как документационная работа;
реализация QA-A и ручная приёмка не начаты. Исходные ID/приоритеты сохранены,
порядок QA-A → QA-B → QA-C → QA-D. Датированные дополнения документов ниже
уточняют прежнее состояние, не удаляя историю подготовки исходников.

Уточнение 2026-10-10: разбиение QA-A на 10 PR — предлагаемый план, ещё требующий
утверждения владельца. Порядок этапов сохраняется. Совместная доработка/приёмка
ST-QA-019/020 отделена в аудите от обязательных предварительных зависимостей.

[Состояние](PROJECT_STATUS.md), [backlog](BACKLOG.md), [решения](DECISIONS.md),
[roadmap](ROADMAP.md), [выполненное](../done.md), [остаток](../todo.md).
Docs описывают самостоятельный source repository COLOSSAL-maksik/Studium-public.
Исходный код: All rights reserved, без открытой лицензии; права на текущие
310 материалов подтверждены владельцем. Наличие кода, автоматические проверки,
ручная acceptance и release — разные состояния. Private operational history,
source ledger и task metadata находятся вне этого репозитория.
