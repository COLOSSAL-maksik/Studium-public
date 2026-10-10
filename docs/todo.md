# Оставшаяся работа

## Актуальное дополнение — 2026-10-10

- Review [реестра 30 требований](management/QA_REGISTER.md) и
  [аудита](management/QA_AUDIT.md); реализация пока не начата.
- Согласовать с владельцем [предлагаемый план QA-A из 10 PR](management/QA_AUDIT.md#qa-a-pr-plan):
  разбиение ещё не утверждено и требует его утверждения. Реализация — только
  после утверждения и отдельной задачи. Перед зависимыми PR решить B1–B6,
  кроме уже закрытого смысла min; сохранить preservation/reopen/backup/native acceptance.
- После приёмки QA-A: QA-B → QA-C → QA-D, сохранить исходные приоритеты и историю.
  Все manual сценарии пока NOT RUN, включая реализованные по коду 001/025.

Publication/main и существующие quality/safety базы уже подтверждены чтением
public GitHub, см. PROJECT_STATUS. Соответствующие прежние пункты ниже —
исторические, не повторная задача публикации. Первоначальный documentation audit
не разрешал запуск Actions; native Windows, second reviewer и integration остаются.

Уточнение review 2026-10-10: порядок QA-A → QA-B → QA-C → QA-D сохраняется;
ST-QA-019/020 совместно доработать и принять, без взаимного обязательного prerequisite.
Для текущего документационного PR разрешены обычные автоматические required checks
нового HEAD. Ручной workflow_dispatch/full_windows не запускается.

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
