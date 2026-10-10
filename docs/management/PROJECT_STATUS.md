# Состояние Studium

Studium — самостоятельное локальное приложение преподавателя с PySide6,
SQLAlchemy/Alembic и SQLite. Source содержит учебные программы, группы/студентов,
работы/попытки/оценки, immutable attachments, Q&A, factual analytics,
отчёты, offline help и ZIP backup/recovery. Миграции v0001–v0009 сохранены.

Независимый package discovery и Studium-only routing подготовлены.
Целевой публичный repository: COLOSSAL-maksik/Studium-public, main.
GitHub repository/push/Actions и Windows release этой локальной подготовкой
не выполняются. Три migration immutability tests используют проверенные frozen
SHA-256 и raw bytes без old Git dependency; 18 migrations сохранены.
Принятый Stage 2: 1043 passed, 3 expected Windows skips, 0 failed/errors;
Ruff и source wheel/sdist/import PASS на Linux. Результат не означает Windows PASS.
Исходный код: All rights reserved, без открытой лицензии; лицензии зависимостей
сохраняются. Владелец подтвердил публикационные права на все 310 материалов.
Windows/manual acceptance остаётся отдельной задачей.
Локальные результаты не заменяют Windows или GitHub PASS.

Bender source отделён; результаты foundation/benchmark разработки не считаются
release/acceptance. Всё Bender code/tests/packaging/CI — Jules; bootstrap после
new repository access. Studium API/client ещё отсутствуют; transport утверждён
как JSON-RPC 2.0 over stdio. Нет обязательного cloud server или общей DB.
