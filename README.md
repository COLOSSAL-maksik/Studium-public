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
отдельно. Migration immutability tests используют проверенные frozen SHA-256
fixtures и raw bytes; все 18 исходных migration payloads сохранены. Тестам не
нужны commits исходного репозитория; схема/миграции этим переносом не меняются.
Оставшиеся проверки и публикация перечислены в docs/todo.md.
