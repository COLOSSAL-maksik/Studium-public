# Безопасность исходного репозитория

В репозитории только исходники, synthetic tests и проверенные проектные материалы.
Не добавлять .env/secrets, production SQLite/sidecars, student files, user logs,
backups/exports, build outputs или непроверенные screenshot/Office документы.
Runtime данные находятся вне checkout и installation directories.

## Проверки

`python scripts/check_repository_safety.py --worktree` проверяет tracked и
unignored files; `--staged` actual index bytes; `--history` reachable commits/
tree refs и metadata; `--check-identity` будущие author/committer.
Checker offline/stdlib, findings redacted. Hook: `git config --local
core.hooksPath .githooks`; не обходить hook. Проверять также filenames, архивы,
Office relationships/properties, image metadata, OCR и происхождение изображений.
Regex/OCR не заменяют review материалов, прав и license перед публикацией.

## Policies

approved-artifacts.json перечисляет только присутствующие reviewed paths с
exact текущими SHA-256. Identity approvals — только подтверждённые noreply.
reviewed-history.json содержит пустые legacy contact/raw-log maps; разрешений
на раскрытие личных контактов нет. Новый artifact/identity требует review.
Нельзя добавлять исключение, чтобы скрыть leak или пройти CI.
Владелец подтвердил права на публичное размещение всех 310 перечисленных
материалов, созданных для проекта с помощью ChatGPT. Это подтверждение прав
дополняет exact-hash privacy review; лицензии зависимостей сохраняются.

## Tests и распространение

Только synthetic data и temporary LOCALAPPDATA. Логи не содержат значения
секретов, контакты или тела реальных сообщений. Installer и bundles сохраняют
границу данных; native Windows acceptance выполняется отдельно.
COLOSSAL-maksik/Studium-public предназначен для публичных исходников:
All rights reserved, без открытой лицензии. GitHub settings/CI и Windows release
не считаются проверенными результатом локальной подготовки source bundle.
