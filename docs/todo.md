# Оставшаяся работа

## Следующее действие после принятия — 2026-10-12

Владелец выбирает один функциональный модуль для отдельной ограниченной задачи.
Затем уточняются реальные сценарии, остатки и acceptance по [ROADMAP](management/ROADMAP.md).
Действующий список — [BACKLOG](management/BACKLOG.md), решение о принятии базы —
[ADR-053](decisions.md#adr-053). Первый модуль не выбран; нового общего implementation
пакета/задач агентам сейчас нет. Недостающие manual проверки относятся к выбранным
модулям и не становятся повторным gate принятия всех 30.

## История прежней очереди до принятия базы

QA-A–D, directions foundation/10-PR proposals и прежний запрет merge ниже заменены
актуальным решением ADR-053. Они не являются новыми заданиями.

## Дополнение ST-PR3-002 — frozen taxonomy

На базе `67986fd` archive Topic/Skill, используемых сохранённой версией/назначением,
отклоняется с concrete dependency list. Новая v12 добавляет только два archive
guards; 22 v1–v11 payloads, прежние facts/UUID и SQL guards сохраняются.
27 новых synthetic regressions, итоговый targeted пакет **165 PASS**. Required CI
нового HEAD фиксируется в PR; manual всех 30 — PENDING. [Отчёт](management/PR3_REVIEW_FIXES.md).
Ниже сохранены предыдущие implementation/verification результаты.

## Общая проверка после review PR #3

Все четыре замечания исправлены в существующей ветке и PR #3 с сохранением
пакета всех 30: late first submission при ended participation; frozen V1
problem/family/attachments; explicit preview/CAS переназначения с прежними
bindings; полная сводка ДЗ/РК/посещаемости и переходы. Additive v11,
v1–v10 payloads неизменны. [Отчёт](management/PR3_REVIEW_FIXES.md), [ADR-051](decisions.md#adr-051).
Целевые DB/GUI: 38 PASS; полный local regression: 1113 PASS / 3 ожидаемых
Windows-only SKIP. Wheel, Ruff/pip, frozen migrations и safety: PASS. Exact-HEAD
CI evidence — в итоговом PR.
Manual всех 30 — PENDING, промежуточная приёмка не требуется. История ниже
сохраняется; старые результаты не объявляются проверкой нового HEAD.

## Общая приёмка пакета 0.2.0

Промежуточные manual/merge gates отменены прямым пакетным заданием. Реализация
всех 30 UI/backend требований собрана в одной ветке; текущая проверка и реальные
blockers отражены в [матрице](management/QA_ALL_30_IMPLEMENTATION.md).
Полная локальная регрессия прошла (1080 PASS / 3 Windows SKIP); результаты required
CI конкретного итогового HEAD фиксируются в PR перед передачей владельцу.
Проверить единый [manual checklist](qa-all-30-manual.md)
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
