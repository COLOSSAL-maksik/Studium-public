# Реализованные компоненты Studium

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
