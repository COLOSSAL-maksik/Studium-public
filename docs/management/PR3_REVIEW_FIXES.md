# Исправления review PR #3

## Дополнение ST-PR3-002: архивирование frozen Topic/Skill

Проверенная база `67986fd28e7288437d175d031e5137ca4f580dcc`, та же ветка и PR.
На actual synthetic DB оба случая сначала воспроизведены: **2 FAIL** — archive
успешен, последующая выдача V1 получает `INVALID_REFERENCE` от прежних link guards.

Выбран предварительный отказ archive. LearningService проверяет всё поддерево до
записи; QAContentSources находит только **сохранённые** UUID в ProgramVersion,
VersionReference, concrete PlanContentSource и StudentProblemAssignment. Ошибка
перечисляет версии, работы плана (группа/период) и отдельные назначения (студент/
работа), названия и UUID. Меняющиеся библиотечные связи не подставляются.
Новые индивидуальные teacher snapshots сохраняют topic_ids наряду со skill_ids;
прежние immutable snapshots не меняются. Student DTO whitelist остаётся прежним.
Создание нового StudentWork и индивидуального назначения проходит одной
транзакцией: отказ freeze не оставляет пустую работу.

Новая additive **v12 / 0012_frozen_taxonomy** добавляет только два archive triggers.
Raw repository/SQL archive того же frozen endpoint также отвергается. Общие
assessment/item context guards и все прежние SQL objects сохраняются; tables
по-прежнему 102 user / 103 с Alembic. **22 published v1–v11 payloads неизменны**.
Нет backfill/переписывания старых rows или попытки восстановить отсутствующие связи.

Source: application/learning_services.py, qa_content_sources.py, qa_services.py,
program_services.py, errors.py; desktop/messages.py; migrations/v0012.py/.sql.
Regression: [test_pr3_frozen_taxonomy.py](../../tests/integration/test_pr3_frozen_taxonomy.py).
**27 новых случаев**, включая обе taxonomy, definition-level, family/variant,
независимый manual plan source, unassigned version/direct references, отдельное
назначение, реальные GUI actions/message, subtree rollback, populated v11 upgrade/
late DDL rollback, UUID/facts/files/reopen/backup. Целевой итоговый пакет:
**165 PASS**, 104.49 s. Ruff check/format (298 files), pip check, staged diff
и safety worktree/identity (650 checked, 0 errors/signals): PASS. Isolated wheel:
167 source/resource files + четыре SVG, v12/103 tables, first late submission,
frozen taxonomy application/raw SQL refusal → issuance, GUI и reopen: PASS.
SHA-256 `68235ddd2c3bbcac937c1c828103898f5f6bd9d6859d32c1194508621d5f7cd7`.
Полный local regression после этого дополнения — NOT RUN; full regression
и required CI нового HEAD фиксируются в итоговом PR. Прежние full результаты
ниже — история, не проверка нового кода.

Сохранённая версия удерживает классификацию даже без группы; новая V2 и archive
плана не освобождают immutable зависимость V1. Unbound taxonomy архивируется как
прежде. Новое сохранение уже архивной классификации и выдача старого повреждённого
snapshot дают понятный отказ без подмены связей. Уже архивированные endpoints из
pre-v12 DB автоматически не восстанавливаются. Pre-v11 отсутствующие topic
snapshots индивидуальных назначений не реконструируются; защищаются известные
сохранённые связи. [ADR-052](../decisions.md#adr-052).

## Предыдущие четыре исправления и результаты на 67986fd

Ветка `agent/codex/qa-a-contracts`; проверенная исходная точка
`1df071dff41d389fbc88972d3161499cdfab4e84`; прежний пакет всех 30 сохранён.
Обновляется [PR #3](https://github.com/COLOSSAL-maksik/Studium-public/pull/3).
Manual acceptance всех 30 — PENDING. Merge/force-push/release не выполняются.

Каждый исходный сценарий сначала воспроизведён actual synthetic DB regression:
четыре теста FAIL на прежнем содержимом, затем PASS после исправлений.

| Замечание | Причина и изменение | Source | Meaningful regression |
|---|---|---|---|
| ST-PR3-001 | Старый StudentWork insert требовал ACTIVE. Scoped late authorization разрешает первую сдачу по исходной выдаче при ended participation; explicit restore audit для deleted context. UUID/ended_at/status прежние. | qa_services.py, domain/qa.py, models/qa.py, v0011.py/.sql, qa_workflow.py | test_pr3_review: первая/существующая работа, WITHDRAWN/COMPLETED, T1→T2, чужой offering, deleted endpoints/archived term, explicit restore, raw guard, late DB/file rollback |
| ST-PR3-002 | Frozen definition_problems хранили только problem ID. Сохраняются effective text, family/variant/source revision, exact semantic links, teacher schema/answers и file IDs. Выдача/assignment/shared files используют saved content. | qa_content_sources.py, qa_services.py, program_services.py, content_services.py, file_services.py | test_pr3_review: text/classification changes, family parameters, archived source, V1/V2, files/teacher whitelist, reopen и backup/restore |
| ST-PR3-003 | Замена plan FK оставляла старые placements без привязки. Concrete immutable sources + pure preview, retained/retired/incoming пакет, expected revisions/fact fingerprint, confirmed transaction. | qa_content_sources.py, qa_plans.py, v0011.py/.sql | test_pr3_review: issued/pending/required/reviews, ordinal conflict и unissued replacement, другая группа, stale new facts/late rollback; test_qa_desktop: реальный preview/cancel/confirm |
| ST-PR3-004 | Первый экран не показывал все исходные показатели. Typed summary добавляет homework revision/waiting/late, control scores и подробную attendance; SCORED не waiting/ACCEPTED. | qa_summary.py, qa_workflow.py, analytics.py | test_pr3_review: exact date/week boundary, repeat reviews, REAL/unknown dates, cents/attendance/cancelled; test_qa_desktop: все показатели и evidence/charts navigation |

Source paths в таблице относительно `src/studium/application/`, кроме явно
названных domain/infrastructure/desktop modules. Regression module:
[test_pr3_review.py](../../tests/integration/test_pr3_review.py);
[GUI](../../tests/integration/test_qa_desktop.py),
[migration](../../tests/integration/test_qa_migration.py).

Head `0011_qa_review_fixes`: 102 user tables / 103 с Alembic. Raw v1–v10 payloads
неизменны. Корректируется один StudentWork membership trigger; его новый полный
DDL проверяется, все прочие прежние objects/rows/REAL/NULL/files сохраняются.
Populated v10 failure возвращает прежние rows, schema objects и version; upgrade
idempotent/reopen и new-head backup/restore проверяются без ослабления guards. Legacy content compatibility после исправления: **30 PASS** (program migration + review regressions).

Целевые DB/GUI tests: **38 PASS**. Полный module-isolated local regression:
**1113 PASS, 3 предусмотренных Windows-only SKIP**, 1116 tests / 59 modules,
811.87 s. После удаления trailing whitespace в новой v11 (SQL tokens прежние)
целевой migration/DB/GUI пакет повторно проверен. Ruff check/format (296 files),
pip check и staged diff --check: PASS. Repository safety worktree/identity:
647 checked, 0 errors, 0 manual-review signals. Все 20 v1–v10 Python/SQL payloads
побайтово совпадают с исходным HEAD. Required CI нового HEAD отражается в
итоговом PR; прежний зелёный HEAD не считается evidence нового содержимого.

Wheel 0.2.0: isolated install, 165 packaged source/resource files совпадают
побайтово, четыре embedded SVG совпадают с исходниками; synthetic v11/103 tables,
first late submission, actual GUI и reopen: PASS. Точный SHA-256 записан в матрице.

Ограничения: старые shared files без snapshot сохраняют legacy compatibility view;
его current links не выдаются за исторический снимок. Pre-v11 версии не содержат
утраченных снимков задач; новые snapshots
нельзя выдавать за прежнюю историю. Пересекающееся содержание требует явного
согласования календаря; retained facts блокируют смену ordinal. Manual Windows
Light/Dark/DPI, non-admin interactive acceptance — PENDING/NOT RUN. Полная Windows
pytest workflow_dispatch — NOT RUN: connector не предоставляет dispatch, доступный
gh не авторизован. Обычный PR native Windows CI отражается отдельно.
