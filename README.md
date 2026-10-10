# Studium

Локальное Windows-first приложение преподавателя: студенты и группы,
дисциплины и программы, работы, попытки и оценки, immutable вложения,
ручные вопросы/ответы, фактическая аналитика, PDF/CSV отчёты и ZIP backup/recovery.
SQLite/Alembic и пользовательские файлы находятся вне репозитория.

Это частный source candidate независимого Studium. Лицензия, публичная
публикация, remote имя и окончательная Windows acceptance ещё не определены.
Наличие кода не означает выпуск или принятие всех пользовательских сценариев.

## Архитектура и документы

[Архитектура](docs/architecture.md), [модель данных](docs/data-model.md),
[требования](docs/requirements.md), [решения](docs/decisions.md),
[состояние и backlog](docs/management/README.md), [навигация](docs/ui-navigation.md).
Приложение сохраняет domain/application/infrastructure/presentation,
исторические миграции v0001–v0009 и пакетную offline справку.
Схемы в assets и исходное ТЗ сохранены; их права нужно проверить до публикации.

Bender разрабатывается отдельно Jules. У Studium нет runtime dependency на
Bender. Будущий клиент использует JSON-RPC 2.0 over stdio; API/client ещё не
реализованы. Обязательный облачный сервер не требуется.

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

GitHub Actions не запускались. Native Windows/manual acceptance выполняется
отдельно. Старые Git-SHA assertions migration tests требуют независимых frozen
fixtures до готовности новой CI; схема/миграции этим переносом не меняются.
Оставшиеся проверки и публикация перечислены в docs/todo.md.
