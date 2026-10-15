# Реализованные компоненты Studium

## Учебная программа — ST-PROG-001–012

Реализованы годовой редактор, draft/CAS/immutable editions, структура занятий,
результаты/подготовка, часы/бюджеты, обмен и использование в планах; additive v13.
[Матрица и фактические проверки](program-window.md). Manual Windows PENDING.

## Пакет принят как рабочая база — 2026-10-12

Этап ST-QA-001–030 завершён и принят владельцем с остаточными замечаниями,
включая четыре review fixes и frozen taxonomy ([ADR-053](decisions.md#adr-053)).
[Матрица](management/QA_ALL_30_IMPLEMENTATION.md) сохраняет реализацию и automated
mapping; ручные результаты отдельно, массового manual PASS нет. Дальше выполняются
ограниченные module tasks по [ROADMAP](management/ROADMAP.md).

## История выполненного и прежних проверок

## Дополнение ST-PR3-002 — frozen taxonomy

На базе `67986fd` archive Topic/Skill, используемых сохранённой версией/назначением,
отклоняется с concrete dependency list. Новая v12 добавляет только два archive
guards; 22 v1–v11 payloads, прежние facts/UUID и SQL guards сохраняются.
27 новых synthetic regressions, итоговый targeted пакет **165 PASS**. Required CI
нового HEAD фиксируется в PR; manual всех 30 — PENDING. [Отчёт](management/PR3_REVIEW_FIXES.md).
Ниже сохранены предыдущие implementation/verification результаты.

## Исправления ST-PR3-001–004

Все четыре замечания исправлены в существующей ветке и PR #3 с сохранением
пакета всех 30: late first submission при ended participation; frozen V1
problem/family/attachments; explicit preview/CAS переназначения с прежними
bindings; полная сводка ДЗ/РК/посещаемости и переходы. Additive v11,
v1–v10 payloads неизменны. [Отчёт](management/PR3_REVIEW_FIXES.md), [ADR-051](decisions.md#adr-051).
Целевые DB/GUI: 38 PASS; полный local regression: 1113 PASS / 3 ожидаемых
Windows-only SKIP. Wheel, Ruff/pip, frozen migrations и safety: PASS. Exact-HEAD
CI evidence — в итоговом PR.
Manual всех 30 — PENDING, промежуточная приёмка не требуется. История ниже
сохраняется; старые результаты не объявляются проверкой нового HEAD.

## Единый implementation-пакет 0.2.0

Реализованы пользовательские маршруты всех ST-QA-001–030 в прежней ветке,
с сохранением PR #2/B1–B6. Course content version/calendar, exact review/rules,
submission/teacher files/return, queue/summary/debt, topic tree/structured answers,
staged picker и общий GUI включены одним пакетом. Additive v10, v1–v9 unchanged.
[Матрица actual source/evidence](management/QA_ALL_30_IMPLEMENTATION.md),
[ADR-050](decisions.md#adr-050--qa-all-30-implementation).
Full local regression: 1080 PASS / 3 предусмотренных Windows SKIP, 58 modules;
synthetic scale, Ruff/dependencies/safety и isolated wheel/GUI smoke прошли.
После обновления Help исправлен устаревший запрос installed-app smoke;
PowerShell query проверяется actual GUI regression; fresh installed schema строго
проверяет current head/all tables и отказывает при unknown/missing. Targeted
Help/installer: 69 PASS.
Exact code candidate и evidence — в матрице, CI конкретного PR HEAD — в PR.
Общая [manual acceptance](qa-all-30-manual.md) PENDING.
Ниже — история предыдущего документационного этапа.

## Документационные контракты QA-A — 2026-10-11

Подготовлены [QA_A_CONTRACTS](management/QA_A_CONTRACTS.md) и
[ADR-049](decisions.md#adr-049--qa-a-product-contracts), actual main
`b620ef3635c2965ad3630bae15d00d1b7bd9a82d`: B1–B6 product agreement,
integer default/fractional toggle OFF, confirmed deadline после семестра,
конкретные transitions/Grade/rule/date и actual-source migration mapping.
Обновлены register/audit/management, сохранены 30 ID/приоритеты и previous baseline.
Технические решения PROPOSED до review; подготовка документации не является
реализацией QA-A или закрытием замечаний. Application/migration/Windows/manual
tests NOT RUN; код, SQL/Alembic, зависимости, CI и installer не изменены.
Actual docs/safety/ordinary required checks нового HEAD — в PR/итоговом отчёте.

Последующее review 2026-10-11 после HEAD `3649afaee48be28d27f81ac41aff86087d594636`:
документированы [индивидуальные долги B2](management/QA_A_CONTRACTS.md#b2-student-debt),
исправлены QA-A-REV-01 (новая SCORED из REVISION_REQUIRED reject) и QA-A-REV-02
(OFF integer score с unchanged saved fractional bounds snapshot). Реализация
mandatory/closure/debt UI не выполнена; исходные замечания не объявлены закрытыми.

## Актуальное дополнение — 2026-10-10

Выполнен документационный [аудит 30 ST-QA](management/QA_AUDIT.md),
создан [реестр](management/QA_REGISTER.md), записан предлагаемый план QA-A на 10 PR.
Разбиение ещё требует утверждения владельца; порядок QA-A → QA-B → QA-C → QA-D
сохраняется. Запись плана не означает его утверждения или начало реализации.
Файлы/functions/tests, delta модели/сервисов/UI/миграций, зависимости,
риски сохранности и acceptance зафиксированы для каждого исходного ID.
По коду: 2 реализованы, 22 частично, 6 отсутствуют; manual 30/30 NOT RUN.
QA-A не реализуется в этой работе. Новые схемы и scoring contracts — предложения.

Публичная база и existing Quality/safety success актуализированы в
[PROJECT_STATUS](management/PROJECT_STATUS.md); это прежние проверки базы,
не evidence закрытия QA. Локальные documentation/safety проверки — в PR.

Уточнение review 2026-10-10: статус плана приведён к предлагаемому;
для ST-QA-019/020 совместная доработка/приёмка отделена от обязательных
предварительных зависимостей, взаимный цикл устранён.

## История — сохранённые компоненты и подготовка исходников

Самостоятельный source repository сохраняет локальное приложение, domain/application contracts,
SQLite/Alembic v0001–v0009, группы/студентов/программы, попытки/оценки,
immutable file storage, Q&A, factual analytics, отчёты и backup/recovery.
Windows installer path/ownership/lifecycle contracts, offline help и ресурсы сохранены.

Внесены repository-specific package discovery и CI routing; сохранены existing
Linux/Windows test partitions и privacy guards. Эти configs не означают CI PASS.
Новая история не содержит source Git commits; private provenance хранится отдельно.
Migration immutability tests переведены на проверенные frozen SHA-256 fixture
без Git dependency и преобразования raw bytes. Все 18 миграций неизменны.
Владелец утвердил COLOSSAL-maksik/Studium-public, All rights reserved и право
публичного размещения всех 310 текущих материалов. Сторонние лицензии сохраняются.

Работа Bender перенесена в отдельный source candidate без содержательных правок.
Bender packaging/tests/CI bootstrap принадлежит Jules; API/client после миграции.
Snapshot миграция не является review/acceptance новых Bender foundation contracts.
Ни новый remote, ни публикация, ни GitHub Actions этим этапом не выполнялись.
Actual локальные проверки фиксируются отдельным частным отчётом; старые числовые
test/build результаты не заявляются как результаты этой версии.
