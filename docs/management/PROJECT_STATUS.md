# Состояние Studium

Studium — самостоятельное локальное приложение преподавателя с PySide6,
SQLAlchemy/Alembic и SQLite. Source содержит учебные программы, группы/студентов,
работы/попытки/оценки, immutable attachments, Q&A, factual analytics,
отчёты, offline help и ZIP backup/recovery. Миграции v0001–v0009 сохранены.

Независимый package discovery и Studium-only routing подготовлены.
Actions/remote/public release не выполнены. Три migration immutability tests
ещё зависят от private old Git SHA; new CI acceptance требует reviewed fixtures.
Windows/manual acceptance, license и material rights остаются открытыми.
Локальные результаты не заменяют Windows или GitHub PASS.

Bender source отделён; результаты foundation/benchmark разработки не считаются
release/acceptance. Всё Bender code/tests/packaging/CI — Jules; bootstrap после
new repository access. Studium API/client ещё отсутствуют; transport утверждён
как JSON-RPC 2.0 over stdio. Нет обязательного cloud server или общей DB.
