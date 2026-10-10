# Оставшаяся работа

## Актуальное дополнение — 2026-10-10

- Review [реестра 30 требований](management/QA_REGISTER.md) и
  [аудита](management/QA_AUDIT.md); реализация пока не начата.
- Перед зависимыми QA-A PR решить B1–B6, кроме уже закрытого смысла min.
  Выполнить [10 последовательных PR](management/QA_AUDIT.md#qa-a-pr-plan)
  только по отдельной задаче, с preservation/reopen/backup/native acceptance.
- После приёмки QA-A: QA-B → QA-C → QA-D, сохранить исходные приоритеты и историю.
  Все manual сценарии пока NOT RUN, включая реализованные по коду 001/025.

Publication/main и существующие quality/safety базы уже подтверждены чтением
public GitHub, см. PROJECT_STATUS. Соответствующие прежние пункты ниже —
исторические, не повторная задача публикации. Новый запуск Actions не разрешён
этим documentation audit; native Windows, second reviewer и integration остаются.

## История — задачи после подготовки самостоятельного репозитория

- Native Windows/manual acceptance: dialogs, paths/reparse/ACL, packaged Help/PDF,
  installer upgrade/recovery на disposable synthetic account.
- Владельцу опубликовать проверенный main bundle в COLOSSAL-maksik/Studium-public;
  All rights reserved и права на 310 материалов уже подтверждены.
- После отдельного разрешения GitHub/Actions: actual required safety/quality;
  second reviewer/CODEOWNERS обсудить отдельно.
- Учесть unpublished работу текущих Bender задач до любого переключения.
- Jules: independent Bender packaging/tests/CI bootstrap; позднее stdio API.
- Codex: будущий Studium integration client и synthetic contract tests.

Solvers/API/Bender GUI не блокируют сохранение разделённых source trees.
Production data/DB migrations, внешние сообщения/cloud/sync/AI здесь не меняются.
