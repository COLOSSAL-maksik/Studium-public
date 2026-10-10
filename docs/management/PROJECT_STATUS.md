# Состояние Studium

## Актуальное дополнение — 2026-10-10

База архитектурного аудита: public `main`,
`ef5414faa594eba0f339d4208d605c92e98de903`. Проверено по исходникам:
30/30 ST-QA; 2 реализованы, 22 частично, 6 отсутствуют. Это статусы реализации,
не закрытие ручной приёмки. [Матрица и evidence](QA_AUDIT.md),
[реестр](QA_REGISTER.md), [предлагаемые 10 PR QA-A](QA_AUDIT.md#qa-a-pr-plan).
Разбиение QA-A на 10 PR ещё требует утверждения владельца и не утверждено;
порядок QA-A → QA-B → QA-C → QA-D сохраняется.
Программа связана с периодом; normalized directions, schedule history,
exact min/max, review/return lifecycle требуют расширений. Min уже решён:
минимальный начисляемый балл; отсутствие оценки и доработка без автоматического 0.

Для указанной базы прочитаны существующие публичные результаты
[Quality](https://github.com/COLOSSAL-maksik/Studium-public/actions/runs/38081188251)
и [Repository safety](https://github.com/COLOSSAL-maksik/Studium-public/actions/runs/38081144482)
— success; main защищён с required quality/repository-safety.
Это актуализирует прежнюю запись о локальной подготовке ниже. Результаты базы
не являются evidence исправления ST-QA или native Windows/manual PASS.
В документационном аудите Actions не запускались, pytest/Ruff/package/manual
NOT RUN; приложение, миграции, зависимости, CI и установщик не менялись.
Implementation QA-A ожидает отдельной задачи и решения зависимых контрактов.

Уточнение review 2026-10-10: ST-QA-019/020 дорабатываются и принимаются совместно,
без взаимной обязательной предварительной зависимости. Для документационного PR
разрешены обычные автоматические required checks нового HEAD; их фактические
результаты фиксируются в PR. Ручной workflow_dispatch/full_windows не запускается.

## История состояния — подготовка самостоятельных исходников

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
