# Реализация единого пакета 30 требований

База: `d23eee39fcb0f3bd463c2868459fa48d0778925a`. Ветка:
`agent/codex/qa-a-contracts`. PR #2/B1–B6/QA-A-REV-01/02 сохранены.
Один пакет/PR, без промежуточной manual acceptance и без merge.
Implementation QA-A–D выполнена; полная локальная регрессия прошла.
Проверенный code candidate: `c50bd5538623aaade1f135815180556d623041db`;
последующее дополнение изменяет только документы. Точный PR HEAD и результаты
его required checks указываются в итоговом PR.
Manual acceptance всех 30 ID — PENDING.

Имена UI файлов ниже относятся к `src/studium/presentation/desktop/`,
application/domain/infrastructure явно указаны. Базовые ссылки:
[UI](../../src/studium/presentation/desktop),
[application](../../src/studium/application/qa_services.py),
[domain](../../src/studium/domain/qa.py),
[migration](../../src/studium/infrastructure/database/migrations/versions/v0010.py),
[интеграционные tests](../../tests/integration),
[domain tests](../../tests/unit/test_qa_domain.py).
Полная suite запускает все указанные modules, без selective skip.

| ID | Этап | Приоритет | Implementation | Automated evidence modules | Manual |
|---|---|---|---|---|---|
| ST-QA-002 | QA-A | P2 | Реализовано: qa_plans.py; domain/qa.py | test_qa_package; test_qa_desktop | PENDING |
| ST-QA-003 | QA-A | P2 | Реализовано: qa_plans.py; application/qa_services.py | test_qa_package; test_qa_scale | PENDING |
| ST-QA-006 | QA-A | P2 | Реализовано: qa_plans.py; programs.py | test_qa_package; test_program_desktop | PENDING |
| ST-QA-010 | QA-A | P2 | Реализовано: qa_plans.py; application/qa_services.py | test_qa_desktop; test_qa_package | PENDING |
| ST-QA-011 | QA-A | P2 | Реализовано: qa_plans.py; application/qa_services.py | test_qa_package; test_qa_domain | PENDING |
| ST-QA-013 | QA-A | P2 | Реализовано: qa_plans.py; application/journal.py | test_qa_package; test_qa_migration | PENDING |
| ST-QA-030 | QA-A | P1 | Реализовано: qa_workflow.py: RuleForm/ReviewForm; domain/qa.py | test_qa_domain; test_qa_package; test_qa_migration | PENDING |
| ST-QA-008 | QA-B | P2 | Реализовано: pages.py; qa_plans.py | test_learning_desktop; test_phase65_desktop | PENDING |
| ST-QA-009 | QA-B | P2 | Реализовано: pages.py: WorksPage | test_learning_desktop; test_iteration4_workflows | PENDING |
| ST-QA-012 | QA-B | P1 | Реализовано: application/journal.py; desktop/journal.py | test_program_regressions; test_learning_desktop | PENDING |
| ST-QA-015 | QA-B | P2 | Реализовано: design.py; journal.py | test_desktop; developer visual | PENDING |
| ST-QA-017 | QA-B | P1 | Реализовано: qa_workflow.py; main_window.py | test_qa_domain; test_qa_scale | PENDING |
| ST-QA-027 | QA-B | P1 | Реализовано: qa_workflow.py: SubmissionForm | test_qa_desktop; test_qa_package; test_qa_scale | PENDING |
| ST-QA-028 | QA-B | P1 | Реализовано: qa_workflow.py: SubmissionHistory; file_storage.py | test_qa_desktop; test_qa_package; test_qa_migration | PENDING |
| ST-QA-029 | QA-B | P1 | Реализовано: qa_workflow.py: PackageSummary | test_qa_desktop; test_qa_package; test_qa_scale | PENDING |
| ST-QA-014 | QA-C | P2 | Реализовано: learning.py; tickets.py | test_workflow_desktop; test_content_workflow | PENDING |
| ST-QA-021 | QA-C | P2 | Реализовано: attachment_picker.py; library.py | test_qa_desktop; test_workflow_desktop; test_qa_package | PENDING |
| ST-QA-022 | QA-C | P2 | Реализовано: qa_content.py; application/content_services.py | test_qa_domain; test_qa_desktop; test_content_workflow | PENDING |
| ST-QA-023 | QA-C | P2 | Реализовано: qa_content.py: TopicTreePicker | test_qa_desktop; test_iteration4_workflows | PENDING |
| ST-QA-001 | QA-D | P2 | Переиспользовано/проверено: calendar.py; dialogs.py | test_workflow_desktop | PENDING |
| ST-QA-004 | QA-D | P3 | Реализовано: calendar.py | test_workflow_desktop; developer visual | PENDING |
| ST-QA-005 | QA-D | P2 | Реализовано: theme.py; design.py | test_desktop; test_workflow_desktop; developer visual | PENDING |
| ST-QA-007 | QA-D | P3 | Реализовано: pages.py | test_desktop; test_learning_desktop | PENDING |
| ST-QA-016 | QA-D | P2 | Реализовано: progress_charts.py | test_program_desktop; test_workflow_desktop | PENDING |
| ST-QA-018 | QA-D | P2 | Реализовано: visuals.py: HomeTile | test_workflow_desktop; test_phase65_desktop | PENDING |
| ST-QA-019 | QA-D | P3 | Реализовано: pages.py; learning.py | test_learning_desktop; test_phase65_desktop | PENDING |
| ST-QA-020 | QA-D | P2 | Реализовано: learning.py: TopicTree | test_iteration4_workflows; test_learning_desktop | PENDING |
| ST-QA-024 | QA-D | P2 | Реализовано: library.py: ContentEditor | test_workflow_desktop; developer visual | PENDING |
| ST-QA-025 | QA-D | P2 | Переиспользовано/проверено: programs.py: KnowledgeWidget | test_program_desktop; test_iteration4_workflows | PENDING |
| ST-QA-026 | QA-D | P2 | Реализовано: theme.py; design.py | test_desktop; developer visual | PENDING |

## Проверки и совместимость

- Полный module-isolated runner на `0ace4f8` до корректировки Help/probe:
  **1080 PASS, 3 SKIP**, 1083
  collected tests / 58 modules, 695.83 s. Пропуски только предусмотренные Windows
  sharing lock и два junction contracts; unexpected/collection skips запрещены.
  Python-код приложения с тех пор не менялся. На финальном candidate исправлен
  устаревший поисковый запрос native installer smoke и инструкции Help;
  actual PowerShell query → packaged Help проверяется GUI regression: 68 PASS
  вместе с installer unit contracts. Полная проверка final PR HEAD — в CI PR.
- Target DB/repositories/reporting/migration: 50 PASS; финальные GUI формы и
  редактор: 35 PASS; отдельная строгая ORM/DDL comparison: PASS.
- Synthetic scale: две группы, 60 студентов, 18 недель, 72 работы,
  120 submissions, 60 reviews, 300 files; FIFO/bulk budget/hash/debt T1→T2: PASS.
- Новые review/rule/bounds, stale/cancel/late failure, material batch rollback,
  working-copy preservation и new-head restore — actual real DB/file tests.
- Ruff check/format (291 files), pip check, git diff --check: PASS.
- Repository safety worktree/identity/history: 0 errors, 0 manual-review signals;
  все 18 migration payloads v1–v9 совпадают с base raw bytes.
- Wheel 0.2.0: isolated install, synthetic fresh/reopen/GUI, Help и четыре
  встроенных SVG ресурса: PASS; 128 Python files совпадают с source, DB/logs
  отсутствуют. SHA-256:
  `b62333bee9e4b566dacd2cf0fbefc8650d738bcb9fb1ef511393d6fc5e49416b`.
  Запрос native installer probe находит актуальную статью в изолированном wheel.
- Developer Qt offscreen осмотр: Light/Dark, 100/125/150%, 960×620 и HD;
  формы/план/сводка/главная, стрелки и адаптивная вкладка «Коллекции» проверены.
  Это Linux evidence, не Windows/user acceptance.
- Required quality/repository-safety и native Windows contracts/build/installer
  smokes запускаются в едином итоговом PR; их actual links/results для PR HEAD
  записываются в description/checks PR. Local results выше не объявлены CI PASS.
- Windows native/DPI installer: NOT RUN locally (Linux). Полная Windows pytest
  suite через full_windows workflow_dispatch: NOT RUN — connector не имеет
  dispatch capability, доступный gh не авторизован. Обычный PR Windows job
  проверяет native marked contracts и сборку/installer smokes отдельно.
- User manual: PENDING, [единый checklist и candidate](../qa-all-30-manual.md).

Schema v10 — 21 additive tables; v1–v9 raw bytes неизменны. Raw legacy rows,
REAL/NULL/UUID/UTC/revisions/FK и файлы сохраняются, unknown timestamps/ordinal/min
не изобретаются. Archive 0.1.0 restore прежним compatible release → upgrade
synthetic separate profile. Unknown schema guards не ослаблены. ZIP v1 preferences
не содержит, новый restore fractional OFF при видимости saved fractions.
[ADR-050](../decisions.md#adr-050--qa-all-30-implementation).
