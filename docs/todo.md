# Оставшаяся работа

## Общая приёмка пакета 0.2.0

Промежуточные manual/merge gates отменены прямым пакетным заданием. Реализация
всех 30 UI/backend требований собрана в одной ветке; текущая проверка и реальные
blockers отражены в [матрице](management/QA_ALL_30_IMPLEMENTATION.md).
После full automated regression проверить единый [manual checklist](qa-all-30-manual.md)
на synthetic Windows candidate, включая Light/Dark/DPI/архивы/хвосты.
Manual PENDING, merge/release/deploy не выполнять. История ниже superseded там,
где требует 10 implementation PR или отдельного разрешения на каждый QA этап.

## QA-A — следующие действия 2026-10-11

- Review [технических proposals/migration mapping](management/QA_A_CONTRACTS.md):
  product B1–B6 уже согласованы, B4 integer default + fractional 2 digits/OFF,
  B2 допускает confirmed deadline после семестра. Не переоткрывать смысл min.
- 10-PR plan остаётся предложением. Ближайший предложенный implementation scope
  — directions foundation PR-02: concrete FK/code import/raw preservation,
  additive schema и соответствующий backup/new-head tests; prerequisites/exit
  зафиксированы в contracts. Implementation только отдельной задачей после review.
- PR-09/10 учесть exact int64 cents/range и mode validation, ReviewGrade/rule
  snapshots/evidence resolver, сохраняемый Settings toggle и unsaved/historical
  fractional display. Будущие PR сейчас не созданы.
- Приёмка всех 30 ID остаётся открытой, порядок QA-A → QA-B → QA-C → QA-D
  прежний; B7–B9 последующим этапам. Application/migration/Windows/manual NOT RUN.

Ниже сохранена прежняя история до согласования B1–B6; повторно получать
product agreement для них не требуется. Technical review и отдельное разрешение
реализации не заменяются этим documentation PR.

После review 2026-10-11: [B2 individual debt/closure](management/QA_A_CONTRACTS.md#b2-student-debt)
требует будущего required-work binding и явных preconditions late-debt записи
при ended enrollment/explicit archive; не угадывать legacy mandatory/closure.
QA-A-REV-01/02 включить в future score validation/snapshot сценарии; полный доступ,
регистрация/summary/queue долгов исходного T1 при active T2 — QA-B. Directions
foundation остаётся следующим предложенным scope, полный план не утверждён.

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
