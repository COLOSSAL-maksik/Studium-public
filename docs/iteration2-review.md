# Iteration 2 — рабочие программы и ежедневный workflow

> Документ относится к Studium как независимому локальному приложению.
> Bender — отдельный проект; будущая интеграция использует локальный JSON-RPC
> 2.0 over stdio. Прямые импорты Bender, API/client, облачный сервер и новые
> возможности этим переносом не реализованы. Описания прежних фаз сохраняют
> технические требования; их проверки и acceptance не подтверждены этим текстом.

Задание: 3 октября 2026. Проверка: 4 октября 2026. Статус: **реализация,
regression и packaged smoke завершены; ручная приёмка ожидается**.

Ruff check и format --check PASS (155 files), pip check PASS.
Принятое содержимое Iteration 1 сохранено без изменений в safety checkpoint
`[историческая ссылка опущена]`. Пользователь явно разрешил этот checkpoint в задании Iteration 2.
Финальный commit Iteration 2 запрещён до packaged build и ручной приёмки.

Исторические миграции 0001–0006 сохраняются. Пользовательские БД и originals
не используются для разработки/проверок; сценарии выполняются на временных
синтетических данных. Phase 7, AI/OCR, внешние адаптеры, server/sync/mobile,
mastery, прогнозы и рейтинги остаются за границей.

## Информационная архитектура и ежедневная работа

Глобальные разделы: Главная, Работа, Дисциплины, Библиотека, Добавить, Настройки.
Home показывает три крупные tiles, последнюю группу/дисциплину/программу,
текущую неделю и модуль, recent contexts. Preferences сохраняют Light/Dark,
active term и recent offerings, не удаляя неизвестные поля.

Course остаётся канонической Discipline. У дисциплины свои программы, сквозные
Topics/Skills, Problem Bank, методические материалы, литература и база знаний.
Страница WorkProgram содержит обзор/PDF/модули/ДЗ и РК/таксономию/материалы/
литературу/группы. CourseOffering выбирает конкретную программу той же
дисциплины и периода. Group.faculty и faculty_short — отдельные поля.
Контекстные вкладки находятся внутри объекта; group analytics не помещена
в discipline context. Back/breadcrumb и прежние student/work/file/case flows сохранены.

## Модель WorkProgram и migration strategy

Новые основные сущности: WorkProgram, ProgramModule, ProgramWork,
HomeworkPack, MethodicalMaterial, KnowledgeEntry/KnowledgeSource,
AssessmentProblem, StudentProblemAssignment/StudentProblemFile,
AttemptSkillResult и concrete taxonomy/material/file links.
WorkDefinition — alias прежней HomeworkDefinition; дополнительный дубликат
каталога не создаётся. Definition.type различает ДЗ/РК. Problem.identifier
уникален внутри дисциплины при непустом значении; Topic/Skill scope проверяется.
SeminarMaterial имеет lecture/seminar type.

WorkProgram хранит направление, факультет, версию, Autumn/Spring, первую
учебную дату, длительность (default **17**), fixed UTC offset и AcademicTerm.
Weeks начинаются с 1, odd/even отображается как числитель/знаменатель.
ProgramModule имеет непересекающийся диапазон внутри duration. ProgramWork —
M2M applicability reusable определения с module/order/issue/due weeks/dates.
Date picker ограничивается выбранной неделей. Один РК может применяться к двум
программам без дублирования определения; группы видят планы своей программы.

Additive migration **`0007_work_programs`**: **30 новых таблиц**, **77 user /
78 total**. Alembic выполняет frozen SQL, без create_all/reсоздания БД.
Исторические 0001–0006 неизменны. Backfill создаёт отдельную программу для
каждого legacy offering и связывает прежние работы. Только новые nullable
columns заполняются; старые значения, revisions, IDs и bytes сохраняются.
Metadata triggers временно снимаются и точно восстанавливаются внутри одной
upgrade transaction. Legacy explicit planned weeks расширяют duration до
сохранённой недели; учебный год не превращается в 50+ недель. >104 — явный
отказ без отсечения данных. Legacy календарь начинается с term.starts_on,
тип первоначально Autumn; преподаватель должен проверить semester settings.
Программа offering после учебных фактов не меняется скрытно.

Проверена заполненная synthetic v6 copy: attempts/grades/files/messages/
attendance/topics/skills/tickets и прежние schema objects сохраняются;
fresh/reopen/integrity/FK, миграции прежних версий проверены regression suite.
Пользовательская production БД и originals не открывались.

## Journal, Homework и РК

Journal строится из программы до появления Attempt: 17 недель attendance,
плановые ДЗ/РК, grouped module headers, режимы Все/Посещаемость/ДЗ/РК и collapse.
ФИО закреплено, header остаётся, горизонтальный scroll; unplanned works
показаны явно. Пустые клетки не создают фактов. Клик/Enter открывает нужное
действие, ФИО — студента. Homework compact states: предъявлено/доработка/
зачтено и число попыток; РК — зачтённые задачи / все задачи.

Quick Attempt оставляет дату, результат, комментарий и один Save;
score/Grade раскрываются по необходимости. Поля Grade зависят от kind.
Новое ДЗ принимает PRESENTED/NEEDS_REVISION/ACCEPTED; REJECTED запрещён в
UI/application/DB. Старые факты не переписываются. Переделка создаёт новую
Attempt, число переделок не ограничено, прежние файлы и комментарии остаются.

Структура работы: общие файлы/текст/Topics/Skills, optional parts.
HomeworkPack связывает несколько ДЗ с общим PDF и теми же FileAsset IDs,
без копирования bytes при linking. Прямые files Assessment также поддержаны.
Не требуется искусственно создавать parts для монолитного ДЗ.

РК использует bank selection с identifier/tag/topic/skill/collection filters,
ручное назначение индивидуальных задач или сохранённый TicketSet. Generator
criteria/replacement/regeneration/export прежней итерации сохранены;
сохранённые варианты применяются к конкретной РК. Выданное условие, teacher
snapshot, Skill IDs и FileAsset FK фиксируются отдельно от изменяемого банка.
Создание/подмена назначения после Attempt запрещено. Файлы доступны для
preview из task checking. AttemptItemResult и AttemptSkillResult независимы:
задача может быть CORRECT, а выбранный навык — INCORRECT. Никакой mastery
или автоматической классификации студента нет.

Lesson Topic и Topic Skill — работающие searchable multi-select pickers с
create/unlink/selected/empty state. Cancel с причиной сохраняет занятие и
исключает его attendance из аналитики; transfer хранит planned date/week,
actual date меняется отдельно. Неделя/модуль плана остаются прослеживаемыми.

## Factual analytics и Knowledge Bank

Group radial: одинаковый угол для каждого студента, radius = доля зачтённых
назначенных работ, 0–100%; порядок alphabetical FIO, tooltip раскрывает контекст.
Weekly line использует ту же метрику, только на конец учебных недель; будущие
недели пусты, current week отмечена. Знаменатель — фактически назначенные к
cutoff работы, не ещё не выданные определения программы. Module filter
ограничивает works/lessons/cases; Student Progress и topic/skill evidence имеют
тот же контекст. Отдельно показаны независимые counts Skill outcomes.
Прежние QtCharts остаются дополнительными вкладками.

as_of и сравнение действительно меняют cutoff запросов. Это известные сейчас
факты с датами событий, **не полный audit snapshot старых редакций каталога,
сроков, attendance или архивирования**. Детали — ADR-032/041. Производные DTO
не меняют Attempt/Grade и не ранжируют студентов.

Из QuestionCase можно вручную создать generalized Knowledge draft или
добавить source к существующей записи. Несколько cases связываются M2M;
count/first/last вычисляются по distinct cases. Сохраняются исходные Messages,
канал/дата/текст/attachments. В Knowledge по умолчанию нет ФИО; raw case доступен
по явной source link. MethodicalMaterial и Topics/Skills связываются вручную.
Автоматического clustering/matching/AI нет.

## Проверки, производительность и Windows bundle

- Baseline: **552 PASS / 132.82s**, Ruff 155 files, pip check PASS.
- Финальный `.venv/Scripts/python -m pytest -q --tb=short`: **577 PASS / 242.76s**.
- `.venv/Scripts/python -m ruff format --check`: **176 files PASS**.
- `.venv/Scripts/python -m ruff check`: **PASS**; `pip check`: **No broken requirements found**.
- Добавлены meaningful domain/calendar/scope/migration/journal/knowledge/
  task-file-snapshot/skill/as_of/theme/Qt enum regression checks.
- Bank 1000: filter **0.0566s / 2 SELECT**; generation 30: **0.1117s / 3 SELECT**.
- Journal 30 students × 17 weeks + 6 works: **0.0378s / 23 SELECT**.
- Progress DTO: **0.0294s / 24 SELECT**.
- Analytics: 30 students / 20 assessments / 1800 attempts / 600 item results /
  10 lessons / 30 cases: **0.195s / 24 SELECT**.
- Group analytics source UI: около **0.25s** в native Windows QA.

Замеры локальные, synthetic, без обещания одинаковых секунд на другом ПК;
bounded SQL budgets проходят, N+1 по ячейкам не появился. Логи в ignored tmp.
Предыдущий analytics snapshot 22 SELECT расширен до 24 для program context.

Свежая `scripts/build_windows.ps1` / PyInstaller clean onedir сборка:
весь `dist\Studium` — **138 952 155 bytes**. Переносить всю папку с `_internal`.
Python/runtime pins/spec сохранены, новых dependencies нет. QtPDF/Charts и
v7 Python/SQL migration resources включены. `scripts/smoke_iteration2_packaged.py`
проверил **fresh / populated v6 migration / workflow / reopen**, все **exit 0**.
Сохранились старые row values/revisions и legacy file bytes, integrity/FK PASS.
В actual exe открыты WorkProgram/modules, Home, Light/Dark, Journal, Problem Bank,
PDF/image/ticket snapshots и дополнительные QtCharts. Native multi-file picker
добавил два вложения, они сохранились после reopen. Через Journal записана пятая
Attempt ДЗ и второй independent task/skill result РК. Пустой task result показал
ожидаемое предупреждение, форма осталась открыта, новый факт не создан.
SQL после reopen подтверждает Homework latest=ACCEPTED, task=CORRECT и
Skill=INCORRECT для обеих проверенных задач. Machine report.

## Screenshots и visual QA

**60 PNG**, по 20 на DPI 100/125/150:
`docs/screenshots/iteration2/dpi-100`, `dpi-125`, `dpi-150`; рядом qa.json.
Qt platform windows; DPR реально 1.0/1.25/1.5 (монитор 200%, scale adjusted).
Empty/Home, Discipline, Program/modules/works/PDF, Journal light/dark,
radial/line, Student Progress, structure/shared PDF, task skills, bank,
Knowledge, calendar, Attempt/history. Проверены размеры 1240×780 и resize
960×620; исправлены hidden page minimum sizes, Form scroll, clipped Home
titles/radial chart. Buttons и calendar читаемы в обеих темах.
Дополнительно **22 native exe PNG** в `docs/screenshots/iteration2/packaged`:
всего **82 PNG**. Windows captures ограничены собственными QA PID, synthetic data.

## Ограничения и ручная приёмка

Native Explorer → frozen exe drag/drop **не подтверждён**. Две попытки
инициализации установленного computer-use helper завершились
`trusted Node process exited unexpectedly`; CUA native surfaces отключены.
Qt component/local-URL drop и native multi-file picker проверяются отдельно;
они не считаются Explorer OLE PASS. Этот сценарий требуется пользователю.
Реальные private данные в QA не использовались. Legacy calendar default
требует просмотра, automatic mapping факультета/направления из старых notes
не выполняется. Historical semester/audit/timezone OPEN остаются явными.

В ранних native smoke сохранение РК после некорректного automation выбора
Combo сопровождалось `ntdll.dll / 0xc0000374` (heap corruption). Native причина
не установлена; это не Python assertion/test failure. QA теперь выбирает поля
по accessible names, открывает реальный Combo popup, подтверждает выбор и
нажимает Save мышью. Финальный корректный workflow, пустой task result с
предупреждением и reopen PASS. Причина раннего native crash остаётся
неустановленной; явная проверка keyboard/assistive automation в сложной форме
включена в ручную приёмку. Нельзя объявлять универсальное устранение native crash
по одному успешному способу ввода.

Перед commit проверить на своей копии данных:

1. Home → Работа → группа → Journal; продолжение/recent contexts после reopen.
2. Одна Discipline → две WorkProgram; Group A/B выбирают A/B, видят свои ДЗ/РК.
3. 17 недель, три модуля, Journal modes/collapse/scroll/frozen FIO и empty cells.
4. Общий PDF комплекта ДЗ; revision cycle с несколькими Attempt, history/files.
5. РК из bank/manual/variants; task checking и отдельные Skill correct/error;
   пустой результат не сохраняется. Проверить Combo мышью и клавиатурой.
6. Lesson Topic/Topic Skill поиск/create/unlink; cancel и transfer сохраняют план.
7. Analytics radial/line/module/as_of; Topic/Skill evidence соответствует фактам.
8. Question → Knowledge draft; объединение sources и MethodicalMaterial link.
9. Light/Dark, calendar, 100/125/150% DPI, resize и Form scrolling.
10. Explorer: несколько PDF/images → drop zone, preview, close/reopen, files сохраняются.

Финальный commit Iteration 2 не создан. Текущий HEAD — safety checkpoint
`[историческая ссылка опущена]`; изменения Iteration 2 остаются
в рабочем дереве для review. Remote не создан. Deferred: Phase 7,
server/cloud/sync/mobile, AI/LLM/OCR, live Telegram/email, mastery/risk/
prediction/ranking, student portal, automatic sending, rich text, full audit/
backup/installer/signing. Эти возможности не получили дату старта.

## Git status перед ручной приёмкой

53 modified unstaged; 24 untracked entries (screenshots directory grouped); staged: 0.

```text
 M AGENTS.md
 M README.md
 M docs/architecture.md
 M docs/data-model.md
 M docs/decisions.md
 M docs/done.md
 M docs/roadmap.md
 M docs/todo.md
 M docs/ui-navigation.md
 M src/studium/application/analytics.py
 M src/studium/application/content_services.py
 M src/studium/application/file_services.py
 M src/studium/application/item_result_services.py
 M src/studium/application/learning_services.py
 M src/studium/application/ports.py
 M src/studium/application/services.py
 M src/studium/application/workflow_analytics.py
 M src/studium/domain/content.py
 M src/studium/domain/entities/__init__.py
 M src/studium/infrastructure/database/migrations/__init__.py
 M src/studium/infrastructure/database/models/__init__.py
 M src/studium/infrastructure/database/models/content.py
 M src/studium/infrastructure/database/models/learning.py
 M src/studium/infrastructure/database/repositories/__init__.py
 M src/studium/infrastructure/database/unit_of_work.py
 M src/studium/infrastructure/user_data.py
 M src/studium/presentation/desktop/analytics.py
 M src/studium/presentation/desktop/charts.py
 M src/studium/presentation/desktop/communication.py
 M src/studium/presentation/desktop/components.py
 M src/studium/presentation/desktop/dialogs.py
 M src/studium/presentation/desktop/learning.py
 M src/studium/presentation/desktop/library.py
 M src/studium/presentation/desktop/main_window.py
 M src/studium/presentation/desktop/messages.py
 M src/studium/presentation/desktop/navigation.py
 M src/studium/presentation/desktop/pages.py
 M src/studium/presentation/desktop/quick_attempt.py
 M src/studium/presentation/desktop/theme.py
 M src/studium/presentation/desktop/tickets.py
 M src/studium/presentation/desktop/widgets.py
 M src/studium/presentation/desktop/workflow_widgets.py
 M tests/database/test_contracts.py
 M tests/integration/test_analytics_migrations.py
 M tests/integration/test_application.py
 M tests/integration/test_communication_migrations.py
 M tests/integration/test_desktop.py
 M tests/integration/test_file_migrations.py
 M tests/integration/test_migration_evolution.py
 M tests/integration/test_phase65_desktop.py
 M tests/integration/test_repositories.py
 M tests/integration/test_workflow_desktop.py
 M tests/legacy_schema.py
?? docs/iteration2-request.md
?? docs/iteration2-review.md
?? docs/screenshots/iteration2/
?? scripts/freeze_iteration2_schema.py
?? scripts/iteration2_scenario.py
?? scripts/preview_iteration2.py
?? scripts/smoke_iteration2_packaged.ps1
?? scripts/smoke_iteration2_packaged.py
?? src/studium/application/journal.py
?? src/studium/application/program_services.py
?? src/studium/application/progress_charts.py
?? src/studium/domain/program.py
?? src/studium/infrastructure/database/migrations/versions/v0007.py
?? src/studium/infrastructure/database/migrations/versions/v0007.sql
?? src/studium/infrastructure/database/models/program.py
?? src/studium/infrastructure/database/repositories/program.py
?? src/studium/presentation/desktop/journal.py
?? src/studium/presentation/desktop/programs.py
?? src/studium/presentation/desktop/progress_charts.py
?? tests/integration/test_program_desktop.py
?? tests/integration/test_program_migration.py
?? tests/integration/test_program_regressions.py
?? tests/integration/test_program_workflow.py
?? tests/unit/test_program_domain.py
```
