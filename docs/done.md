# Реализованные компоненты Studium

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
