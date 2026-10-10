# Iteration 4 — Data safety, daily workflow, Help Center

> Документ относится к Studium как независимому локальному приложению.
> Bender — отдельный проект; будущая интеграция использует локальный JSON-RPC
> 2.0 over stdio. Прямые импорты Bender, API/client, облачный сервер и новые
> возможности этим переносом не реализованы. Описания прежних фаз сохраняют
> технические требования; их проверки и acceptance не подтверждены этим текстом.

Работа выполняется по [заданию](iteration4-request.md). Финальный commit запрещён
до ручной приёмки и отдельного разрешения.

## Baseline

- Принятая Iteration 3 сохранена в `[историческая ссылка опущена]`.
- Alembic head проверен: `0008_problem_variants`.
- Минимальный baseline: 7 targeted tests PASS; полный suite не повторялся.
- Исторические миграции и пользовательские данные сохраняются.

## Реализовано и проверено

Batch A–E технически завершены; ручная приёмка остаётся открытой. Пользовательские data roots,
реальные студенты и документы в проверках не использовались.

### A — Удаление и файлы

«Удалить» скрывает выбранную запись из активной работы через `deleted_at` и
optimistic revision. Подтверждение называет запись и объясняет сохранение
истории, файлов и связанных учебных контекстов. Дисциплина, период, группа,
студент, рабочая программа, модуль, работа программы и материалы Library
получили соответствующие действия. Завершение Enrollment остаётся отдельной
операцией. Удаление не вызывает физический cascade: Attempts, результаты,
назначения вариантов, файлы и unrelated Library content сохраняются.
Удалённая дисциплина в прежнем материале отображается с пометкой «удалена».

Импорт копирует содержимое в managed storage Studium. Метаданные и стабильный
FileAsset ID находятся в SQLite; оригинальные immutable bytes — в application
data directory, отдельно от репозитория. Перемещение/удаление исходного файла
после импорта не влияет на сохранённую копию. Отсоединение не уничтожает bytes.
Для недоступной или повреждённой копии выводится понятная ошибка; подмена
содержимого не считается успешным открытием.

Устранён общий Open crash Literature/Homework/Seminar и других материалов:
Problem family logic применяется только к Problem. Большая FileDropZone имеет
центрированную подпись, click по всей площади, chooser/multi-file/drop, состояния
hover и disabled. DOC добавлен рядом с DOCX; встроенный просмотр поддерживает
изображения/PDF, остальные форматы открываются через ассоциации Windows.
Политика описана в ADR-045, история Attachment не переписывается.

### B — Ежедневная работа

Bank показывает список и bounded async preview выбранного image/PDF, включая
общее условие семейства и выбранный вариант. Generation guards отбрасывают
устаревшие ответы при быстром переключении. В узком окне кнопка «Предпросмотр»
открывает содержимое на всю доступную ширину, «Список» возвращает выбор задач.

Seminar содержит вкладки «План / Задачи / Файлы / Темы / Заметки». Прежний
`full_text` сохранён. Из банка выбираются несколько существующих задач с
фильтрами; выбор сохраняется при смене поиска. Создание задачи внутри семинара
сохраняет её в общем Bank с назначением Seminar и связывает с семинаром.
У нового семинара pending links сохраняются вместе с материалом в транзакции.

Journal поддерживает Ctrl/Shift и выбор нескольких attendance cells одной
недели. «Отметить выбранных (N)» изменяет только выбранных студентов; другие
остаются прежними. Статус Qt combo явно преобразуется в AttendanceStatus:
native проверка выявила строковый QVariant, который прежний тест с прямой
передачей enum не покрывал; regression теперь нажимает настоящую кнопку.

Student → Works: Homework / RK / Exam → конкретная работа → полная история
Attempts → её файлы. Просмотр не создаёт Attempt, StudentWork или результат.
Для новой сдачи существует явное действие записи попытки. Student → Progress
показывает отдельные категории и фактические сведения по каждой работе:
первая/последняя сдача, принятие, количество попыток, статус и отношение к сроку.
Формулы аналитики сохранены; придуманные оценки, прогнозы и рейтинги не добавлены.

### C — Структура и UX

Каталог: рабочая программа/период → модуль → тема → подтема → связанные навыки.
Тема может входить в несколько модулей; вложенная тема сохраняет контекст
предков. Неразмещённые темы остаются доступными. Порядок вверх/вниз не выдаётся
за иерархию. Period CRUD перенесён из Settings в «Управление периодами…»
верхнего selector; удаление другого периода сохраняет активный контекст.

Group header без ellipsis, действия расположены в «Настройки группы».
Основные metadata видны без дополнительного accordion. Таблицы позволяют
изменять ширины и сохраняют их в preferences по составу колонок; полные
заголовки доступны в tooltip. Sidebar без отдельной синей полосы selected
branch. Journal использует смысловые «ДЗ №… / РК №…» и корректный end ellipsis.

### D — Offline Help Center

В footer расположен пункт «Справка». **20 отдельных Markdown статей** и
`index.json` хранятся в package resources. Поиск локальный: название, раздел,
текст. Работают навигация, `help:` links и fallback неизвестного article ID.
API: `MainWindow.open_help(article_id)` / `help_center.open_help(owner, id)`.
Сеть, web engine и новые dependencies не требуются.

Setuptools package data и PyInstaller включают ресурсы. Для динамического
`importlib.resources` package добавлен явный hidden import; его отсутствие
выявлено и исправлено при actual EXE startup QA. [Help maintenance DoD](help-maintenance.md)
и ADR-046 требуют обновлять только статьи затронутых пользовательских workflows.

## Миграция и сохранность

Head — **`0009_daily_workflow`**, предыдущий — `0008_problem_variants`.
Добавлены `seminar_problems` и `module_topics`: UUID/UTC/revision/soft-delete,
unique endpoints, FK RESTRICT и guards контекста/identity/physical deletion.
Схема содержит 79 пользовательских таблиц, 80 с Alembic version.

По прямому разрешению пользователя FileAsset пересоздаётся для расширения CHECK
на DOC. Исходный CREATE TABLE меняется только в allowlist; rows копируются,
indexes/triggers восстанавливаются. FK остаются включены, constraint checking
отложен до конца транзакции; count/FK проверяются до commit. Тест поздней ошибки
подтверждает полный rollback schema/rows/version, затем успешный retry.
Populated v8 copy/reopen сохраняют каждую прежнюю строку, Attachment FK,
TicketSets/назначения и immutable bytes. Downgrade с потерей новых фактов запрещён.
Исторические 0001–0008, исходное ТЗ/assets и dependency locks не изменены.

## Проверки

| Проверка | Результат |
| --- | --- |
| `.venv/Scripts/python -m pytest -q` | **639 PASS / 1084.28s**, один полный запуск |
| Набор Iteration 4 после native attendance fix | **34 PASS / 25.88s** |
| Отдельный regression настоящей кнопки attendance | **1 PASS / 1.26s** |
| `ruff format --check` / `ruff check` | **232 files / PASS** |
| `pip check` | **PASS**, no broken requirements |
| Native geometry 100/125/150% | **48 × 3 = 144 checks**, narrow/desktop/maximized |
| Screenshots | **20 PNG**, Light/Dark, [каталог](screenshots/iteration4) |
| Frozen code/resources/protected sources | **37 modules + v9 Python/SQL + 21 resources / 27 protected files PASS** |

Targeted проверки охватывают managed copies всех владельцев, deletion isolation,
fresh/v8 upgrade, rollback/retry, preview race/image/PDF, seminar links, attendance,
read-only Student facts, topic hierarchy, column persistence, Help/search/fallback.
После найденного native дефекта повторён затронутый набор; полный suite не
перезапускался без необходимости. В полной регрессии отсутствуют failures/skips.

## Batch E — Сборка и Git

Свежая сборка `.venv/Scripts/python -m PyInstaller --noconfirm --clean Studium.spec`
**9,979,016 bytes** (9.52 MiB).
Вся onedir папка — **138,326,065 bytes** (131.92 MiB);
передавать её целиком, сохраняя `_internal` рядом с EXE.

Actual EXE запускался из temporary working directory с отдельным LOCALAPPDATA,
без PYTHONPATH и PATH установленной Python/.venv. **Fresh / populated v8 migration /
workflow / reopen — PASS, exit 0**. Проверены Home/sidebar/Group/Journal scroll,
три selected attendance cells, Homework/RK/Exam, полная история Attempts и её PDF,
Student Progress, семь Library разделов, Literature/Homework Open, создание
Seminar (plan + PDF + bank task + new task), managed Bank image после удаления
source, period management, Help/search, Light/Dark и восстановление Dark.

После закрытия: ровно 3 новых attendance facts, другие студенты неизменны;
Seminar имеет 2 задачи и 1 managed PDF, новая задача доступна в Bank. Удалены
synthetic sources; bytes всех прежних managed files сохранены. Каждая прежняя
DB row сохранена; новые записи соответствуют явным QA действиям. На reopen
rows совпали полностью: просмотр не создал новых фактов. Populated v8 migration
сохранила прежние rows/schema objects/TicketSets/assignments/file bytes;
integrity/FK PASS во всех четырёх режимах.

Frozen **37 Python modules**, v9 migration Python/SQL и
**21 Help resources** совпадают с checkout. **27
protected files** (исторические миграции, ТЗ/assets, locks/исходники) совпали с HEAD.
EXE SHA-256: `bb481c974f9ec44e9795e367a213570763a4ecbdf96849c169ad3435be21e28a`.
Packaged evidence,
bundle integrity,
validation.

Git status на момент финальной проверки: **55 modified + 66 untracked = 121 файлов**,
все unstaged; deleted/staged нет. Final commit не создан. Изменённые/новые
файлы по слоям (Help resources относятся к presentation, PNG/JSON — к docs):

| Слой | Файлов |
| --- | ---: |
| domain | 2 |
| application | 8 |
| infrastructure | 7 |
| presentation | 43 |
| tests | 15 |
| scripts | 4 |
| docs | 38 |
| root/config | 4 |
| Всего | 121 |


Native DLL discovery build spec ограничен production Python/Qt и Windows.
При проверке обнаружен захват несовместимой ICU из PATH стороннего Poppler
runtime; такой PATH больше не участвует в упаковке. Зависимости не изменены,
источник runtime DLL проверяется вместе с повторным actual EXE launch.

## Ограничения и deferred

По отдельному прямому разрешению пользователя весь текущий результат Iteration 4
сохраняется техническим safety checkpoint перед Iteration 5. Это точка восстановления,
не пользовательская acceptance и не финальный release commit. В checkpoint входят
исходники, миграция v9, тесты, Help, документация и синтетические QA evidence;
build/dist/tmp, локальные БД, пользовательские файлы и временные логи исключены.
Ручная приёмка остаётся открытой; Iteration 5 этим шагом не начинается.

Подтверждённых незакрытых product defects пока не выявлено; это не заменяет
ручную приёмку на рабочем DPI и пользовательских материалах. Настоящий
Explorer → EXE OLE drag, ассоциации DOC/DOCX и удобство keyboard workflows
проверяются пользователем. Для DOC/DOCX требуется установленное системное
приложение; их встроенный rendering не входит в Iteration 4. Полный browser
архива/restore удалённых записей не добавлен; сохранены исходные факты и связи.

Phase 7, AI/OCR, server/cloud/sync/mobile, live Telegram/email, рейтинги/прогнозы
и новые внешние интеграции остаются deferred. Remote и новые dependencies
не создавались. Финальный Iteration 4 commit не создан.

## Ручная приёмка

- [ ] Удалить дисциплину, группу, студента, рабочую программу и Library item;
  проверить confirmation и сохранность unrelated Library, истории и файлов.
- [ ] В Literature/Homework/Problem/Attempt импортировать PDF, сохранить,
  удалить source на диске и открыть после перезапуска Studium; проверить DOC/DOCX.
- [ ] Попасть мышью в большую FileDropZone; настоящий Explorer drag и несколько файлов.
- [ ] В Bank выбирать image/PDF задачи и варианты, быстро переключать;
  проверить «Предпросмотр / Список» в узком окне.
- [ ] Создать Seminar: план + PDF + несколько задач из Bank + новая задача;
  найти новую задачу в общем Bank и повторно открыть семинар.
- [ ] Ctrl/Shift выбрать нескольких студентов одной недели, выставить статус;
  убедиться, что остальные не изменились.
- [ ] Student Works: Homework/RK/Exam → работа → Attempts 1/2/3 и их файлы;
  открыть конкретную попытку и записать следующую только явным действием.
- [ ] Student Progress: отдельные Homework/RK и фактические строки конкретных работ.
- [ ] Module → Topic → Subtopic/Skills; размещение темы в нескольких модулях.
- [ ] Settings без period CRUD; управление периодами из верхнего selector.
- [ ] Group без ellipsis; настройки группы доступны в соответствующей вкладке.
- [ ] Изменить ширины колонок, перезапустить; проверить Journal labels и sidebar.
- [ ] Справка: поиск/переходы/примеры/offline, Light/Dark, рабочий DPI 100/125/150%.
- [ ] После приёмки отдельно разрешить финальный commit Iteration 4.
