# Iteration 5A — Reporting & Export

> Документ относится к Studium как независимому локальному приложению.
> Bender — отдельный проект; будущая интеграция использует локальный JSON-RPC
> 2.0 over stdio. Прямые импорты Bender, API/client, облачный сервер и новые
> возможности этим переносом не реализованы. Описания прежних фаз сохраняют
> технические требования; их проверки и acceptance не подтверждены этим текстом.

**Статус интеграции, проверка 2026-10-10:**
 влит в `main`
(`[историческая ссылка опущена]`). Ниже сохранены контракт и evidence этапа; прежние ожидания
нового CI/review не являются текущим PR status. Ручная acceptance открыта;
актуальные проверки и задачи — в [management](management/README.md).

Реализована самостоятельная локальная подсистема отчётов основного Studium.
Работа выполняется в `agent/codex/iteration5a-reporting` от `origin/main`.
Код, тесты, документация и интеграции Bender не изменяются.

## Архитектура и модель

`ReportingService` — application mixin существующего `StudiumService`.
Один transaction загружает прежний analytics `_Snapshot`, дополненный
Course, StudentGroup и Grade. `_View` сохраняет прежние правила выдачи работ,
участия, cutoff, посещаемости и topic/skill evidence. Статус и текущий балл
вычисляет прежний `StudentWorkProgress`; отчёты не вводят собственных переходов.

`Report`, `ReportTable`, `ReportChoices` — frozen DTO с tuple metadata,
колонками в фиксированном порядке и tuple строками. В них нет ORM/Qt/IO.
Preview, CSV и PDF используют один экземпляр `Report`. В domain нет
изменений; generated reports не сохраняются в БД. Схема остаётся
`0009_daily_workflow`: **новых миграций и зависимостей нет**.

Студенты упорядочены по ФИО и ID, работы — по типу, номеру, названию и ID,
попытки — по существующему `attempt_no`, части — по `sort_order` и ID.
Дата последней попытки относится к последнему `attempt_no`, включая
backdated capture; source timestamps не изменяют порядок истории.
При фиксированном cutoff и неизменных фактах модель и CSV детерминированы.
PDF содержит дату формирования и технические metadata Qt, поэтому равенство
его bytes между генерациями не является контрактом.

## Три вида отчётов

- Студент: ФИО и контекст; работы/сроки/недели/статусы/попытки/последние даты,
  последняя записанная Grade с номером её попытки и текущий factual балл;
  полная история попыток, item outcomes, посещаемость, topic/skill evidence
  со счётчиками и source IDs.
- Группа: одна строка на студента с числом работ, зачтённых работ, попыток
  и распределением существующих статусов; отдельные таблицы результатов
  конкретных работ, частей и посещаемости каждого студента/группы.
- Работа / РК: название, тип, срок, контекст; результаты каждого студента,
  история item outcomes; распределения существующих статусов и числа попыток.

Последняя Grade не объявляется новой «общей оценкой» и не заменяет статус.
Например, комментарий после зачтённой попытки сохраняет предыдущий статус,
а номер попытки Grade показывает её происхождение. Пустая оценка не становится
нулём. Не создаются mastery, rankings, predictions, AI interpretations.

## UI и экспорт

Раздел **Отчёты** — пятый элемент существующей sidebar navigation. Используется
общий выбранный период и один selector CourseOffering с дисциплиной/группой.
Архивные контексты и завершившие участие включаются явным переключателем.
Фильтр дат не вводится: UI показывает текущее состояние выбранного контекста.
Смена условий/периода и повторный вход сбрасывают устаревший preview.
Preview использует обычные read-only TableModel/DataTable, тематические
контролы, вкладки секций и scroll. Reports загружается при открытии,
не добавляя пакетную загрузку фактов на каждый refresh главной страницы.

CSV: stdlib `csv.writer`, стандартный comma-separated quoting/CRLF,
UTF-8 BOM для русских Windows spreadsheet workflows. Экспортируется таблица
выбранной вкладки; даже пустая таблица содержит заголовки. Даты CSV — UTC ISO,
а UI/PDF — локальное время компьютера. PDF: существующие QTextDocument,
QPdfWriter и QPainter; A4 landscape, переносы длинного текста/таблиц,
повторение table headers и номера страниц. HTML экранирует данные.
Цвет текста печатной страницы задан явно и не наследует светлый foreground
из Dark: экспорт остаётся читаемым на белой бумаге в обеих темах приложения.
Print layout использует PDF paint device и явный outline Arial (с системным
font fallback); footer рисуется тем же шрифтом. PDF reader tests всегда
закрывают документ, в том числе при assertion failure.

Оба формата сохраняются через Save File dialog и атомарный QSaveFile.
Отмена не записывает файл. Выбор managed data directory или любого Git working
tree отклоняется до открытия QSaveFile; тот же guard действует при прямом
вызове export operation. Проверяются вложенные и ещё не созданные пути,
symlinks, существующие файлы и `.git`-файлы worktree. UI передаёт фактическую
папку данных, включая --data-dir; прямой вызов по умолчанию проверяет штатное
хранилище, а keyword `data_directory` задаёт override.
Нет импорта в FileAsset, копирования в managed storage, database registration,
сетевой отправки или логирования содержимого. Attachment bytes не читаются
и не встраиваются. Offline Help дополнен статьёй **Отчёты и экспорт**;
прежние package-data/collect_data_files включают новый Markdown resource.


CSV сериализуется отдельно от UI/PDF: Grade.score и Grade.max_score используют
точное строковое представление записанных чисел, без `display_grade`/`:g` и
изменений в БД. Настоящие отрицательные числа остаются числами.
Для пользовательского текста и текстовых Grade проверяется первый значимый
символ после whitespace/Unicode control/format characters. Перед `=`, `+`,
`-`, `@` добавляется апостроф в начало всей ячейки, включая ведущие символы;
quoting остаётся отдельной CSV-сериализацией. Защищены также текстовые headers.

Локализация применяется только к AssessmentType, AttemptResult,
AttendanceStatus, ItemOutcome и StudentWorkStatus через отдельные словари.
Совпадающие обычные строки, текстовые Grade и неподдерживаемые enum остаются
буквальными. Это правило одинаково для CSV, UI и HTML, используемого PDF;
одноимённые enum разных типов, например ACCEPTED, не смешивают подписи.

Дополнительное review заголовков: application projection сохраняет
AttendanceStatus и StudentWorkStatus в названиях колонок, вместо потери типа
через `.value`. Строковые ключи колонок и порядок сохранены; существующий
presentation formatter локализует enum одинаково в preview, CSV и PDF.
Пять новых случаев проверяют заголовки посещаемости/итогов студента и группы
и статусы группы в CSV, HTML и actual QtPdf text; preview regression читает
headerData реальных таблиц. Все пять случаев воспроизвели ошибку до исправления.
Прежняя регрессия сохраняет буквальные строки PRESENT/ABSENT/ACCEPTED и другие
ключи локализации. Общий `LABELS.get` для пользовательского текста не возвращён.
После этого follow-up: targeted reporting/export/desktop **106 PASS**,
полный Linux/Python 3.13 **845 passed, 1 skipped / 534.95s**; skip — прежний

До исправлений 42 новых регрессионных случая воспроизвели все четыре замечания.
Дополнительные проверки охватывают пользовательский data-directory override,
сочетания ссылок и сохранение в обычную папку вне Git/Studium. Refusal tests
сравнивают все файлы и ссылки до/после: нет перезаписи и временных артефактов.
CSV precision regression сравнивает также все строки БД и schema до/после.
Экспортный набор после исправлений: **77 PASS**, включая все четыре замечания.
Полный Linux/Python 3.13 pytest после исправлений: **840 passed, 1 skipped**
за 530.02s; skip — существующий Windows junction contract. В PR добавлены
73 новых review regression cases; Ruff format/check, pip check, Repository
safety worktree/history/staged и diff whitespace checks — **PASS**.
Для проверки PDF подписей QtPdf text extraction нормализует добавленные между
глифами пробелы и исключает декоративные status symbols с зависимой от платформы
font mapping. HTML сравнивает подписи буквально; печатный raster regression
сохранён. Изменения PDF-шрифтов в эту задачу не входят.

## Проверки

Тесты используют исключительно synthetic records, pytest temporary roots
и отдельные export paths вне managed application root. Проверяются все
виды/empty cases/scope/архив, отсутствие Grade, zero score, порядок попыток,
все attendance states/unmarked, factual evidence, Unicode/quoting CSV,
валидный PDF header, реальное чтение Unicode и последней строки через QtPdf,
несколько страниц, ошибки IO, UI/selectors/preview/cancel/stale context,
Light/Dark при 960×620 и 1240×780, keyboard focus и локальный поиск Help.
Отдельный regression рендерит PDF через QtPdf, композитит прозрачную страницу
на белый фон и сравнивает изображения после экспорта из Light и Dark.

Read-only regression сравнивает **все** строки **всех** таблиц и весь
`sqlite_master` до/после генерации, HTML preview, CSV всех секций и PDF
для каждого типа. В исходном наборе есть Attempt, Grade, Attendance,
FileAsset и attachment. Дополнительно захватываются SQL statements:
разрешены только SELECT, revisions/facts/schema сохраняются.

Performance regression: 30 студентов × 20 работ, 1 200 Attempts,
1 200 item results, 15 Lessons, 450 Attendance. Пустой и полный group report
выполняют одинаковые **27 SELECT**, без N+1. Загрузчик повторно использует
текущую database-wide analytics infrastructure; SQL budget фиксирован,
но объём памяти зависит от общего размера локальной базы.

Первоначальный Linux/Python 3.13 прогон до review: **767 passed, 1 skipped**;
skip — прежний Windows junction contract. Добавлено 28 reporting/export/UI
tests. Ruff format/check (**259 files**), pip check, Repository safety
worktree/history/staged и git diff checks — **PASS**. GitHub Repository safety
и Windows/Python 3.12 Quality проверяются на опубликованном PR; результат
фиксируется в PR checks и финальном сообщении.

Проверен сборочный wheel: четыре reporting modules, индекс из 21 статьи
и `reporting.md` присутствуют в package. Для build isolation используется
уже объявленный `setuptools==84.0.0`, runtime/development lock files не меняются.

В данной Linux sandbox `/tmp` содержит служебный Git marker; прежний
`ensure_outside_repository` закономерно отклоняет application roots внутри
него. Полный pytest запускается с TMPDIR/`--basetemp` в отдельном
`/dev/shm/studium-reporting-tests`, без отключения production/repository guards.
На Windows CI используются обычные pytest temporary roots.
Windows offscreen не обнаруживает системные шрифты: общий Qt test fixture
загружает установленные Arial/Segoe UI, как существующий preview harness.
Шрифты не копируются и не добавляются в package/repository. Это позволяет
проверять настоящее Unicode text embedding вместо fallback glyph boxes.
Quality сначала выполняет reporting export regression, затем полный pytest
с остановкой на первой ошибке для сохранения traceback. Лимит Windows job
по отдельному разрешению пользователя увеличен с 45 до 90 минут после двух
отмен по прежнему лимиту. Оба запуска pytest выводят 20 самых медленных
тестовых фаз через `--durations=20`; существующие проверки сохранены.
Если полный pytest не завершится за 90 минут, требуется исследование
замедления без повторного увеличения лимита. Этот follow-up меняет только
CI configuration и записи документации; tests/product/dependencies/Bender

## Изменённые файлы

- `src/studium/application/report_models.py`, `reporting.py`: DTO и reporting queries.
- `src/studium/application/analytics.py`, `services.py`: опциональный historical snapshot и mixin.
- `src/studium/presentation/desktop/reports.py`, `report_export.py`: workspace, CSV/PDF.
- `src/studium/presentation/desktop/main_window.py`, `navigation.py`: существующие routes/sidebar.
- `src/studium/presentation/desktop/help_articles/reporting.md`, `index.json`: offline Help.
- `tests/integration/test_reporting.py`, `test_report_exports.py`, `test_reports_desktop.py`: новые regression scenarios.
- `tests/integration/test_desktop.py`, `test_iteration3_desktop.py`, `test_workflow_desktop.py`: существующие navigation expectations (пять разделов).
- `tests/integration/test_iteration4_workflows.py`: существующая Help проверка (21 статья).
- `docs/iteration5a-reporting.md`, `done.md`, `todo.md`: отчёт и оставшаяся приёмка.
- `.github/workflows/quality.yml`: ранняя export regression, fail-fast diagnostics и Windows timeout budget.

## Ограничения и оставшаяся ручная приёмка

Исторический режим показывает сохранённые текущие facts архивного контекста;
cutoff прежней аналитики не реконструирует audit snapshot старых редакций.
CSV сохраняет одну секцию за раз; PDF содержит весь отчёт. Большие отчёты
строятся синхронно, без фонового задания или persistent cache. Пользователь
сам отвечает за дальнейшее хранение экспортированных файлов вне Studium.

Qt/offscreen Linux checks не заменяют actual Windows exe smoke,
native Save File dialog acceptance, Windows printer/PDF viewer behavior,
ручную DPI/keyboard приёмку и PyInstaller Windows package acceptance.
Эти проверки остаются для локального Windows. PR не merge автоматически.
