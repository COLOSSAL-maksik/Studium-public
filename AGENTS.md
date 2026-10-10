# Правила работы в Studium

Studium — независимое локальное приложение преподавателя. Codex отвечает
за его код и будущий интеграционный клиент. Bender принадлежит отдельному
репозиторию; весь Bender code/tests/packaging/locks/CI/API/GUI пишет Jules.
Прямые imports Bender и общая БД не допускаются; future API — JSON-RPC 2.0 stdio.

## Изменения и проверки

Новая задача имеет отдельную ветку agent/codex/<task>. Initial source root
создаётся по разрешённому локальному bootstrap; последующие изменения через PR.
Не merge, push, создавать remote, запускать Actions или публиковать без
соответствующего разрешения. Required safety/quality приоритетны; необходимость
второго reviewer согласует владелец отдельно. Лицензию не выбирать за владельца.

Читать README, docs/architecture.md, docs/data-model.md, docs/decisions.md и
релевантную спецификацию. Сохранять миграции, UUID/UTC, history attempts/grades,
transaction/file boundaries, ресурсы и Windows installer contracts.
Не добавлять API/client/AI/sync/cloud или другую функцию без отдельной задачи.
После разрешённых изменений обновлять done/todo; не путать код, тесты и manual
acceptance. Выполнять relevant pytest/Ruff/package проверки и указывать NOT RUN.

## Данные и Git

Только synthetic fixtures и временные профили. Production DB/student data/
storage/backups/logs недоступны агентам. Environments/cache/build outputs
снаружи source tree либо явно ignored; ничего из этого не commit.
Hook `.githooks/pre-commit` проверяет actual index и identity; не обходить его.
Identity policy содержит только подтверждённые public-safe noreply; history
contact/raw-log exemptions пустые. Новые materials требуют review и exact SHA-256.
Source provenance, migration ledger и операционные записи хранятся private.
Не переносить старые Git objects/refs и не переписывать историю.
