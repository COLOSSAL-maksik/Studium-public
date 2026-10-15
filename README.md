# Studium

Локальное Windows-first приложение преподавателя: студенты и группы,
дисциплины и программы, работы, попытки и оценки, immutable вложения,
ручные вопросы/ответы, фактическая аналитика, PDF/CSV отчёты и ZIP backup/recovery.
SQLite/Alembic и пользовательские файлы находятся вне репозитория.

Исходный репозиторий независимого Studium предназначен для публичного размещения
в [COLOSSAL-maksik/Studium-public](https://github.com/COLOSSAL-maksik/Studium-public).
Наличие кода не означает готовый Windows-релиз или принятие всех пользовательских
сценариев: native Windows/manual acceptance выполняется отдельно.

## Права и лицензирование

Исходный код доступен для просмотра. Открытая лицензия не предоставлена:
**All rights reserved**. Это не меняет лицензии сторонних компонентов,
включая PySide6/Qt, SQLAlchemy и Alembic; их условия сохраняются.
Владелец подтвердил право на публичное размещение всех 310 проектных материалов,
созданных для проекта с помощью ChatGPT. Материалы сохранены без изменений.

## Архитектура и документы

[Архитектура](docs/architecture.md), [модель данных](docs/data-model.md),
[требования](docs/requirements.md), [решения](docs/decisions.md),
[состояние и backlog](docs/management/README.md), [навигация](docs/ui-navigation.md).
Приложение сохраняет domain/application/infrastructure/presentation,
исторические миграции v0001–v0009 и пакетную offline справку.
Схемы в assets, исходное ТЗ и synthetic screenshots входят в сохранённые материалы.

Пакет 0.2.0 объединяет все 30 ST-QA: версии программ и независимые планы,
сдачи/проверки/возвраты, очередь, сводку и долги, структурированные ответы и GUI.
[Матрица реализации и проверок](docs/management/QA_ALL_30_IMPLEMENTATION.md),
[общая ручная проверка и Windows candidate](docs/qa-all-30-manual.md).
Ручная приёмка всех 30 требований остаётся PENDING.

Bender разрабатывается отдельно Jules. У Studium нет runtime dependency на
Bender. Будущий клиент использует JSON-RPC 2.0 over stdio; API/client ещё не
реализованы. Обязательный облачный сервер не требуется.

## Учебная программа

Годовой редактор с сохраняемыми черновиками, неизменяемыми редакциями,
занятиями/темами, результатами обучения, часами и баллами. Программа не требует
созданной группы или периода. Обмен одним `.studium-program` и применение к
независимым планам групп — [инструкция, формат и проверка](docs/program-window.md).
Ручная Windows-приёмка нового окна остаётся PENDING.

## Разработка

Python >=3.12,<3.14. Runtime: PySide6 6.11.2, SQLAlchemy 2.1.1, Alembic 1.20.0.
Dev pins находятся в requirements-dev.lock; PyInstaller отдельно в
requirements-build.lock. Setuptools discovery включает только studium/studium.*.

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.lock
.\.venv\Scripts\python.exe -m pip install --no-deps -e .
```

Обычный запуск: `python -m studium`. Для проверок использовать только временный
synthetic профиль; production DB и storage не открывать.
[Тесты](tests/README.md), [команды](scripts/README.md),
[Windows installer](docs/windows-beta-distribution.md),
[manual checklist](docs/windows-installer-smoke-tests.md).
Локальные environments/build outputs не являются исходниками и не публикуются.

## Граница приёмки

Результаты required Quality/repository-safety относятся к конкретному HEAD в PR;
автоматические проверки не заменяют ручную приёмку. Migration immutability tests
используют frozen SHA-256 fixtures и raw bytes: все 18 payloads v1–v9 сохранены,
v10/v11 добавляют новые таблицы и lossless mapping прежних фактов; v12 защищает
архивирование frozen классификации без переписывания данных. Тестам не нужны
commits исходного репозитория. Оставшаяся приёмка перечислена в docs/todo.md.
