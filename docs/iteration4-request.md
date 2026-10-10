> Документ относится к Studium как независимому локальному приложению.
> Bender — отдельный проект; будущая интеграция использует локальный JSON-RPC
> 2.0 over stdio. Прямые импорты Bender, API/client, облачный сервер и новые
> возможности этим переносом не реализованы. Описания прежних фаз сохраняют
> технические требования; их проверки и acceptance не подтверждены этим текстом.

Продолжаем разработку Studium в:


Это ITERATION 4 — DATA SAFETY + DAILY WORKFLOW + HELP CENTER.

Iteration 3 уже реализована, после неё проведена ручная приёмка.
Во время приёмки выявлен следующий законченный пакет требований.

Главная цель Iteration 4:

1. сделать хранение пользовательских данных и файлов надёжным;
2. завершить важные ежедневные преподавательские workflow;
3. убрать несколько оставшихся UX-антипаттернов;
4. сделать полноценную карточку работ студента;
5. добавить первую встроенную Справку Studium.

НЕ пытайся в этой итерации чинить всё приложение вообще.
Все новые замечания после начала Iteration 4 пойдут уже в Iteration 5.

============================================================
0. BASELINE / SAFETY CHECKPOINT
============================================================

Сначала изучи текущее фактическое состояние проекта:

git status
git diff --stat
git log --oneline -10

alembic current / head либо соответствующий внутренний способ
определения текущей schema revision.

По ручной приёмке приложение уже содержит результаты Iteration 3.
На одном из acceptance screens schema отображалась как:

0008_problem_variants

Но НЕ полагайся слепо на это:
проверь актуальный Alembic head.

Запусти только минимальный baseline smoke / targeted tests,
не полный suite, если рабочее дерево соответствует завершённой
Iteration 3 и последний full regression уже был успешным.

Если состояние чистое/понятное —
создай safety checkpoint commit:

checkpoint: iteration 3 accepted baseline before iteration 4

Если есть непонятные сторонние изменения:
НЕ reset / checkout / clean.
Остановись и сообщи.

Финальный commit Iteration 4 НЕ создавать.
После реализации будет ручная приёмка.

============================================================
1. CODEX QUOTA POLICY
============================================================

Экономить agent/token quota без снижения качества.

Работать пакетами:

BATCH A
File storage + file opening + deletion/data safety

BATCH B
Teaching workflows:
attendance / seminars / student works / progress / Problem Bank preview

BATCH C
UX cleanup:
sidebar / settings / forms / tables / hierarchy / Journal

BATCH D
Help Center

BATCH E
final regression / package / docs

Во время разработки:

- НЕ запускать полный pytest после каждой правки;
- запускать targeted tests по изменённой области;
- использовать pytest -q;
- failing test диагностировать отдельно;
- Ruff только для затронутых файлов во время работы;
- полный Ruff/full pytest только в финале;
- PyInstaller только в финале;
- не делать десятки screenshots;
- не перечитывать весь docs tree;
- не делать unrelated refactor;
- не менять стабильные доменные модели без необходимости.

============================================================
2. DATA SAFETY: УДАЛЕНИЕ СОЗДАННЫХ СУЩНОСТЕЙ
============================================================

Пользователь должен иметь возможность удалить
любую созданную им сущность из нормального UI.

Минимум:

- AcademicTerm / учебный период;
- Discipline;
- WorkProgram;
- Group;
- Student;
- Library materials;
- Problem / ProblemFamily / ProblemVariant;
- Homework materials / packs;
- RK sets;
- Seminar;
- Lecture;
- Literature;
- MethodicalMaterial;
- Knowledge entries;
- другие user-created entities,
  если сейчас их невозможно удалить.

ВАЖНО:
«Удалить» в UI не означает обязательно физический SQL DELETE.

Для сущностей с историей использовать существующую
soft-delete/archive архитектуру,
если это безопаснее.

Но пользователь должен видеть понятное действие:

Удалить

а не быть вынужденным разбираться,
что технически означает archive/revision.

------------------------------------------------------------
2.1 NO DESTRUCTIVE CASCADE
------------------------------------------------------------

Удаление Discipline или Group
НЕ должно автоматически удалять reusable Library content.

Например удалили Discipline:

НЕ удалять автоматически:
- Problem Bank tasks;
- Homework condition sets;
- RK sets;
- Literature;
- Methodical materials;
- PDF;
- FileAsset;
- Seminar reusable content;
- Lecture reusable content.

Если материал был связан только с удалённой Discipline,
он должен сохраниться в Library
и потерять/пометить недействительную связь,
а не исчезнуть.

Удаление Group также НЕ должно уничтожать:
- Library;
- Problem Bank;
- shared files;
- WorkProgram definitions.

------------------------------------------------------------
2.2 DELETE CONFIRMATION
------------------------------------------------------------

Перед удалением показывать понятное подтверждение.

Если есть зависимости,
описать пользователю последствия.

Пример:

«Удалить дисциплину
“Сопротивление материалов”?

Группы и история останутся в архиве.
Материалы Библиотеки не будут удалены.
12 материалов потеряют привязку к этой дисциплине.»

НЕ показывать технические FK / IDs.

------------------------------------------------------------
2.3 STUDENTS
------------------------------------------------------------

Разобраться с текущим Student / Enrollment design.

Не уничтожать исторические Attempt/Attendance факты
из-за удаления студента из активной работы.

Если уместно разделить:
- удалить из группы / завершить участие;
- удалить студента из активного интерфейса;

сделать это понятным.

Не разрушать append-only Attempts.

============================================================
3. FILE STORAGE — MANAGED INTERNAL STORAGE
============================================================

КРИТИЧЕСКОЕ требование.

Прикрепляемые файлы НЕ должны оставаться ссылками
на исходный путь пользователя.

Сценарий:

Пользователь выбирает:

D:\Учеба\ДЗ1.pdf

После сохранения Studium должен физически импортировать
этот файл в собственное managed storage.

После успешного импорта пользователь может:

- удалить исходный D:\Учеба\ДЗ1.pdf;
- переименовать его;
- переместить;

и файл ВСЁ РАВНО должен открываться из Studium.

Использовать существующую архитектуру FileAsset,
если она уже рассчитана на это.

Предпочтительная модель:

%LOCALAPPDATA%\Studium\files\<UUID-prefix>\<UUID>.<ext>

SQLite хранит:

- FileAsset UUID;
- original filename;
- extension / MIME;
- byte size;
- hash, если уже предусмотрен;
- storage_key;
- timestamps;
- links to entities.

НЕ хранить большие PDF/DOC/images непосредственно как BLOB
в SQLite без крайней необходимости.

Файловое хранилище + metadata в SQLite — предпочтительный вариант.

============================================================
4. FIX GLOBAL FILE OPENING BUG
============================================================

В ручной приёмке воспроизводится общий баг:

Library → Literature
→ добавить учебник
→ материал появляется
→ Open
→ generic error:

«Не удалось выполнить действие...
проверьте доступ к папке данных»

Та же ошибка:

Library → Домашнее задание
→ material
→ Open
→ та же ошибка.

Это указывает на общий дефект FileAsset/open pipeline.

Исправить ОБЩИЙ механизм,
не делать отдельные hacks для Literature/Homework.

Проверить:

- import/copy;
- storage_key;
- absolute resolution;
- file existence;
- extension;
- packaged application path;
- QDesktopServices / platform open;
- permissions;
- Unicode/Cyrillic filenames;
- reopen after app restart.

------------------------------------------------------------
4.1 ERROR MESSAGES
------------------------------------------------------------

Убрать generic message,
если можно определить причину.

Показывать, например:

«Файл не найден во внутреннем хранилище Studium.»

«Нет доступа к файлу.»

«Windows не удалось открыть файл приложением по умолчанию.»

«Файл повреждён или недоступен.»

Техническую exception информацию можно писать в log,
но не показывать обычному пользователю traceback.

------------------------------------------------------------
4.2 REGRESSION MATRIX
------------------------------------------------------------

Проверить:

- Literature;
- Homework;
- Methodical materials;
- Seminar attachments;
- Lecture attachments;
- Problem attachments;
- ProblemVariant scheme;
- Attempt attachments;
- Message attachments,
  если они используют тот же FileAsset.

Тест:

import
→ save entity
→ verify internal copy exists
→ remove/move original source
→ reopen application/service
→ open/resolve internal file successfully.

============================================================
5. GLOBAL FILE DROP ZONE
============================================================

Во всех формах с файлами текущая drop zone слишком маленькая.

Сделать единый reusable component:

FileDropZone

Она должна быть ощутимо выше,
а не узкой полоской.

Примерно:

┌─────────────────────────────────────┐
│                                     │
│      Перетащите файлы сюда          │
│                                     │
│        [ Выбрать файлы… ]           │
│                                     │
└─────────────────────────────────────┘

Requirements:

- большая удобная hit area;
- drag hover feedback;
- click/button file picker;
- multi-file where allowed;
- disabled state;
- same component everywhere;
- usable on smaller window;
- minimum useful height не схлопывается.

Не задавать гигантскую высоту,
но попасть мышью должно быть легко.

============================================================
6. PROBLEM BANK — PREVIEW PANE
============================================================

Большинство условий задач пользователь будет хранить:

- PDF;
- images.

В общем окне Problem Bank
нужен быстрый preview,
не требующий открывать карточку задачи.

Сделать desktop two-pane layout:

LEFT / CENTER:
Problem list

RIGHT:
Preview pane

При выборе Problem:

- image attachment → показать изображение;
- PDF → показать первую страницу / текущую страницу;
- несколько файлов → простой selector / thumbnails;
- ProblemFamily variant → preview выбранной variant scheme;
- нет preview → clean placeholder.

Пример:

[ список задач ] | [ Предпросмотр условия ]

Панель preview можно делать resizable splitter.

На узком окне допустимо:
- скрывать preview;
- открывать его по кнопке.

На обычном desktop окне показывать его сразу.

НЕ загружать огромные PDF целиком синхронно,
если это подвешивает UI.
Использовать существующий thumbnail/preview subsystem.

============================================================
7. SEMINAR WORKFLOW
============================================================

Текущая форма «Новый материал → Семинар»
слишком ограничена.

Семинар может существовать как:

A.
текстовый план;

B.
готовый PDF;

C.
набор задач;

D.
комбинация всего этого.

Переработать создание/редактирование Seminar.

Предпочтительная структура tabs:

План
Задачи
Файлы
Темы
Заметки

------------------------------------------------------------
7.1 FILES
------------------------------------------------------------

В «Файлы»:

- PDF;
- images;
- DOC/DOCX;
- other ordinary attachments.

Использовать общий FileDropZone.

Файлы должны импортироваться
во внутреннее managed storage Studium.

------------------------------------------------------------
7.2 PROBLEMS FROM BANK
------------------------------------------------------------

В «Задачи»:

[ Добавить из банка задач ]

Открывается selector:
- search;
- Discipline;
- Topic;
- Purpose;
- tags;
- multiselect.

Можно выбрать несколько existing Problem items.

Seminar хранит LINKS,
а не копии задач.

------------------------------------------------------------
7.3 CREATE PROBLEM FROM SEMINAR
------------------------------------------------------------

Должна быть возможность:

[ Создать новую задачу ]

прямо из Seminar.

Открыть compact Problem editor/dialog.

После Save:

1. Problem создаётся в Problem Bank;
2. получает Purpose=Seminar по умолчанию,
   если пользователь не изменил;
3. автоматически привязывается к текущему Seminar;
4. пользователь возвращается обратно в Seminar form.

НЕ создавать isolated duplicate,
который существует только внутри Seminar.

============================================================
8. ATTENDANCE — MULTI-SELECT
============================================================

Реальный сценарий:

из группы отсутствуют несколько студентов.

Пользователь НЕ хочет workflow:

«сначала отметить всех присутствующими,
потом исправлять отсутствующих».

Основной bulk workflow должен быть MULTI-SELECT.

В Journal / Attendance:

- выбрать конкретную week/lesson column;
- Ctrl / Shift / checkbox / selection mechanism
  выбрать несколько student cells/rows;
- одним действием назначить выбранным общий статус.

Statuses использовать существующие.

Например:

Присутствовал
Отсутствовал
Опоздал
Уважительная причина

если эти состояния соответствуют текущей domain model.

После multiselect можно:
- context menu;
- compact toolbar;
- keyboard shortcut/menu.

Не делать UX перегруженным.

История/факты посещаемости должны сохраняться корректно.

Добавить regression test:
3 students selected
→ set status
→ только эти 3 изменились.

============================================================
9. STUDENT → WORKS
============================================================

Текущая вкладка Student → Работы
с таблицей:

Название работы
Состояние
Попыток

недостаточно функциональна.

Переделать её в рабочий drill-down interface.

Первый уровень:

Домашнее задание
Рубежный контроль
Экзамен

Не смешивать разные виды работ.

------------------------------------------------------------
9.1 WORK LIST
------------------------------------------------------------

При выборе:

Домашнее задание

показывать:

ДЗ №1
ДЗ №2
ДЗ №3
...

Для RK:

РК №1
РК №2
...

Для Exam:
соответствующие assessment items.

Показывать:
- название;
- current state;
- number of attempts;
- relevant dates.

------------------------------------------------------------
9.2 ATTEMPTS
------------------------------------------------------------

При выборе конкретной работы
открывать карточку истории попыток.

Например:

ДЗ №1

Попытка 1
12.09.2026
Предъявлено
[PDF] [Фото]

Попытка 2
19.09.2026
На доработке
[DOCX] [PDF]

Попытка 3
26.09.2026
Зачтено

Каждая Attempt:
- отдельная historical record;
- append-only;
- date/time;
- status;
- grade/result if applicable;
- teacher note if existing model has it;
- attachments.

Можно открыть Attempt
и посмотреть её Files.

------------------------------------------------------------
9.3 FILE PREVIEW
------------------------------------------------------------

Attempt files:

- image → preview;
- PDF → preview;
- DOC/DOCX → хотя бы открыть через system app,
  если inline preview не реализован;
- unknown → open externally.

Не добавлять сейчас тяжёлый Office renderer.

============================================================
10. STUDENT → PROGRESS
============================================================

Сейчас Progress слишком общий.

Не строить один большой агрегат по всем работам.

Разделить минимум на:

Домашнее задание
Рубежный контроль

и внутри:

Домашнее задание:
- ДЗ №1
- ДЗ №2
- ДЗ №3

Рубежный контроль:
- РК №1
- РК №2

При наличии Exam можно добавить отдельную category,
если это уже поддерживается current domain.

Для каждой работы показывать factual information:

- current state;
- attempts;
- first submission;
- latest submission;
- accepted/completed;
- deadline relation;
- task/skill facts where applicable.

НЕ вводить:
- mastery score;
- risk score;
- ranking;
- prediction.

Это factual analytics only.

Общий summary категории допустим,
но он вторичен.

============================================================
11. TOPIC / CONTENT HIERARCHY
============================================================

Уточнённая предметная структура:

AcademicTerm / Semester
→ Module
→ Topic
→ Subtopic

Skills связаны с Topic/Subtopic.

Skill НЕ является обычным следующим элементом
линейного sortable list.

Текущий UI с кнопками:

Выше
Ниже

создаёт неправильное впечатление.

Сначала проверить,
что именно сейчас делает order_index.

Если это просто visual sorting:
убрать «Выше / Ниже» из основного UI.

Показывать структуру как hierarchy/tree.

Пример:

Модуль 1

  Тема 1
    Подтема 1.1
      Навыки:
        ...
    Подтема 1.2

  Тема 2

Actions:

Добавить тему
Добавить подтему
Добавить навык
Изменить
Удалить / архивировать

Если педагогический порядок тем внутри Module
реально хранится в order_index,
можно сохранить его автоматически.

Не показывать raw technical sort fields.

============================================================
12. SETTINGS — ACADEMIC PERIOD
============================================================

Сейчас Settings содержит:

Добавить учебный период
Изменить активный период

Это неправильная IA.

Academic period — рабочий academic context,
а не technical application setting.

Убрать эти actions из Settings.

Использовать уже существующий selector
справа сверху:

2026/2027

Dropdown должен показывать:

2026/2027 ✓
2025/2026
...

────────────
Управление учебными периодами…

В management screen/dialog:

- создать;
- изменить;
- сделать активным;
- архивировать/удалить безопасно.

Settings оставить для:

- Theme;
- storage;
- future backup/sync;
- diagnostics/version;
- app settings.

============================================================
13. GROUP HEADER — REMOVE TOP-RIGHT ELLIPSIS
============================================================

На Group screen справа сверху есть permanent button:

...

с actions:
- Изменить группу;
- Добавить дисциплину группе.

Удалить trigger из основной шапки.

Это редкие administrative actions.

Перенести их в понятное место:

Group settings / Edit group.

Шапка ежедневной работы должна оставаться чистой.

============================================================
14. SIDEBAR SELECTED STATE
============================================================

Сейчас active sidebar item одновременно имеет:

- blue/light background;
- blue text/icon;
- отдельную яркую вертикальную синюю полоску слева.

Вертикальную accent bar убрать.

Selected state:

- subtle background;
- accent text/icon;
- возможно medium font weight.

Один понятный accent,
а не несколько одновременно.

Применить к root items
и nested sidebar items.

Light + Dark.

============================================================
15. TABLE COLUMN RESIZING
============================================================

Основные таблицы Studium не должны иметь жёстко
заблокированные ширины колонок без необходимости.

Пример:

Group → Students:

ФИО
Характеристика / заметки
Участие

Пользователь должен менять ширину колонок
dragging header separators.

Сделать reusable preference mechanism,
если это не слишком сложно.

Желательно сохранять widths
между запусками приложения,
например через QSettings/UI preferences.

Проверить другие основные grids.

Особенно:
- Students;
- Library lists;
- Work lists;
- attempts where table is used.

Не ломать frozen FIO implementation Journal.

============================================================
16. JOURNAL HEADER ELISION
============================================================

При narrow Homework columns
сейчас появляется бессмысленный обрезок типа:

«кт ДЗ для»

вероятно из полного названия
«Комплект ДЗ для ...».

Это недопустимо.

В dense Journal использовать semantic short labels:

ДЗ №1
ДЗ №2
РК №1

Полное название:
tooltip / details.

Если нужен text elide:
использовать нормальное end ellipsis:

«Комплект ДЗ…»

а не показывать бессмысленный хвост строки.

Проверить header sizing after horizontal scroll.

============================================================
17. REMOVE UNNECESSARY «ДОПОЛНИТЕЛЬНО»
============================================================

Во время приёмки обнаружено много collapsible blocks,
которые только скрывают обычные поля.

General rule:

Если поля спокойно помещаются на desktop form,
НЕ прятать их за «Дополнительно».

Progressive disclosure использовать только
для действительно редких/сложных параметров.

------------------------------------------------------------
17.1 NEW GROUP
------------------------------------------------------------

В форме «Новая группа» показывать сразу:

- Номер / название;
- Кафедра;
- Факультет;
- Сокращение факультета;
- Характеристика / заметки.

Убрать accordion «Дополнительно».

------------------------------------------------------------
17.2 PROBLEM EDITOR
------------------------------------------------------------

В Problem create/edit
сразу показывать:

- Tags;
- Complexity / level;
- другие обычные metadata,
  которые сейчас спрятаны под «Дополнительно».

------------------------------------------------------------
17.3 PROBLEM BANK FILTERS
------------------------------------------------------------

На обычном desktop width
сразу показывать:

- Topic;
- Skill;
- Tags;
- Collection.

Убрать «Дополнительные фильтры» accordion.

На реально узком viewport
можно adaptive collapse.

------------------------------------------------------------
17.4 AUDIT
------------------------------------------------------------

Быстро проверить другие формы.

Не устраивать global rewrite,
но если visible аналогичный бессмысленный accordion
с 2–4 обычными полями,
убрать его.

============================================================
18. HELP CENTER — FIRST VERSION
============================================================

После acceptance fixes реализовать первую встроенную
Справку Studium.

Это отдельная feature внутри Iteration 4.

------------------------------------------------------------
18.1 ENTRY POINT
------------------------------------------------------------

В sidebar внизу:

? Справка
⚙ Настройки

Справка НЕ должна быть единственным пунктом
в отдельном верхнем classic menu bar.

Открывать Help Center внутри MainWindow.

------------------------------------------------------------
18.2 HELP UI
------------------------------------------------------------

Сделать современный Help Center
в visual language Studium.

Пример layout:

Справка

[ Поиск по справке... ]

Начало работы
Работа с группами
Дисциплины
Рабочие программы
Журнал
Домашнее задание
Рубежный контроль
Банк задач
Семинары и лекции
Карточка студента
Файлы
Аналитика
Библиотека
Настройки

LEFT:
article navigation

RIGHT:
article content

или другой clean responsive layout.

------------------------------------------------------------
18.3 CONTENT STORAGE
------------------------------------------------------------

Справку хранить модульно.

Например:

docs/help/
  index.md
  getting-started.md
  academic-periods.md
  disciplines.md
  work-programs.md
  groups.md
  journal.md
  attendance.md
  homework.md
  control-work.md
  problem-bank.md
  seminars.md
  lectures.md
  students.md
  attempts.md
  analytics.md
  library.md
  files.md
  settings.md

Можно использовать другой путь,
если архитектурно лучше,
но статьи должны быть отдельными files,
а не hard-coded giant HTML string.

Help должен работать offline.

------------------------------------------------------------
18.4 CODEX WRITES INITIAL HELP
------------------------------------------------------------

Codex должен САМ написать первоначальный текст справки
на основе фактического текущего интерфейса Studium.

Не писать абстрактную документацию.

Описывать реальные workflows.

Например:

«Как создать дисциплину и рабочую программу»

«Как добавить группу»

«Как отметить посещаемость»

«Как добавить и проверить домашнее задание»

«Как сформировать рубежный контроль из Банка задач»

«Как добавить задачу с несколькими вариантами схем»

«Как посмотреть попытки студента»

«Как прикрепляются и хранятся файлы»

Использовать реальные названия текущего UI
после Iteration 4.

------------------------------------------------------------
18.5 CONTEXT HELP
------------------------------------------------------------

Если реализуется недорого:

Help Center API:

open_help(article_id)

чтобы позже экран мог открыть
свою статью напрямую.

Не обязательно расставлять кнопки `?`
на каждом screen сейчас.

Главное заложить clean capability.

------------------------------------------------------------
18.6 HELP MAINTENANCE RULE
------------------------------------------------------------

Добавить в developer docs правило:

При следующих iterations:

если пользовательский workflow изменился —
обновить ТОЛЬКО затронутые help articles.

Не переписывать Help целиком.

Если behavior не изменился —
Help не трогать.

Это часть Definition of Done.

============================================================
19. RESPONSIVENESS
============================================================

Все новые/изменённые screens проверить минимум:

960×620
1240×780
maximized

DPI:
100%
125%
150%

Не нужны screenshots каждого случая.

Forms:
vertical ScrollArea where necessary.

Tables:
horizontal scroll where necessary.

Preview panes:
splitter / adaptive.

Help:
usable in non-maximized window.

============================================================
20. MIGRATION STRATEGY
============================================================

Сначала максимально использовать existing schema.

Большинство Iteration 4 должно реализоваться без новой migration.

Migration допустима,
если реально нужна для:

- Seminar ↔ Problem links;
- missing deletion metadata;
- missing internal storage metadata;
- another unavoidable domain relationship.

Но сначала проверить существующие tables/entities.

Если migration нужна:

- additive only;
- next free revision after current Alembic head;
- do not modify historical migrations;
- preserve existing data;
- preserve FileAsset;
- preserve Attempts;
- preserve ProblemFamily/variants;
- preserve TicketSets.

Tests:
- fresh DB;
- upgrade from previous head;
- populated existing DB.

============================================================
21. TARGETED TESTS DURING DEVELOPMENT
============================================================

BATCH A tests:

- import file copies into Studium storage;
- source file can be deleted;
- internal copy remains usable;
- open resolver works;
- Literature;
- Homework;
- Problem attachment;
- Attempt attachment;
- safe delete;
- no Library cascade.

BATCH B:

- seminar ↔ problems;
- create problem from seminar;
- preview data;
- attendance multi-select;
- Student Works category grouping;
- Attempt history;
- Progress grouping.

BATCH C:

- period manager location;
- no top-right Group menu;
- resizable columns;
- sidebar selected state;
- topic hierarchy behavior;
- no unnecessary accordions;
- semantic Journal labels.

BATCH D:

- Help index loads;
- search works;
- article navigation;
- missing article graceful fallback;
- packaged resource loading.

============================================================
22. FINAL FULL REGRESSION
============================================================

В конце:

pytest -q
ruff format --check .
ruff check .
pip check

После PASS:

PyInstaller onedir build.

Packaged smoke:

- launch;
- Home;
- sidebar;
- Group;
- Journal;
- attendance multiselect;
- Student → Works;
- open Attempt attachment;
- Student → Progress;
- Library;
- Problem Bank preview;
- Seminar create;
- add file;
- add problem from bank;
- create new problem;
- Literature open;
- Homework open;
- source file removed but Studium copy works;
- Academic period selector;
- Help Center;
- search Help;
- Light/Dark;
- reopen.

============================================================
23. SCREENSHOTS
============================================================

Сделать небольшой acceptance set,
не больше примерно 16–20 screenshots.

Пример:

1. Sidebar selected state
2. Academic period dropdown
3. Topic hierarchy
4. Group Students with resized columns
5. Journal
6. Attendance multiselect
7. Problem Bank preview
8. Seminar Problems tab
9. Seminar Files tab
10. Large FileDropZone
11. Student Works categories
12. Student Attempts
13. Student Progress Homework
14. Student Progress RK
15. Delete confirmation
16. Help Center home
17. Help article
18. Help search
19. Dark Help
20. optional narrow layout

Папка:

docs/screenshots/iteration4

============================================================
24. DOCUMENTATION
============================================================

Создать:

docs/iteration4-review.md

Описать:

- delete semantics;
- cascade policy;
- managed file storage;
- file opening fix;
- Problem preview;
- Seminar workflow;
- attendance multiselect;
- Student Works;
- Student Progress;
- topic hierarchy;
- period management;
- UX cleanup;
- Help architecture;
- migrations;
- tests;
- package;
- known limitations;
- manual acceptance checklist.

Если file-storage/delete policy требует ADR —
создать короткий ADR.

Не переписывать всю архитектуру.

============================================================
25. MANUAL ACCEPTANCE CHECKLIST
============================================================

После Iteration 4 пользователь проверит руками:

DELETE
- Discipline;
- Group;
- Student;
- WorkProgram;
- Library item.
- Library content не исчезает неожиданно.

FILES
- attach PDF;
- save;
- delete original source;
- reopen Studium;
- file opens.
- Literature.
- Homework.
- Problem.
- Attempt.

DROP ZONE
- удобно попасть мышью;
- drag works.

PROBLEM BANK
- select task;
- see image/PDF preview;
- switch tasks quickly.

SEMINAR
- text plan;
- PDF attachment;
- choose tasks from bank;
- create new task inside seminar;
- new task appears in Problem Bank.

ATTENDANCE
- select multiple students;
- set status;
- others unchanged.

STUDENT WORKS
- Homework / RK / Exam;
- choose ДЗ №1;
- see Attempt 1 / 2 / 3;
- open files.

STUDENT PROGRESS
- Homework separate;
- RK separate;
- individual works visible.

TOPICS
- Module → Topic → Subtopic;
- Skills linked correctly;
- no confusing «Выше / Ниже».

SETTINGS
- no academic period CRUD.

ACADEMIC PERIOD
- top-right selector;
- manage periods from selector.

GROUP HEADER
- no mysterious top-right ellipsis.

TABLES
- resize columns.

SIDEBAR
- no blue vertical selected bar.

JOURNAL
- no meaningless truncated header fragments.

HELP
- open;
- search;
- navigate;
- examples readable;
- works offline.

============================================================
26. FINAL REPORT
============================================================

Финальный Iteration 4 commit НЕ создавать.

Сообщить:

- checkpoint commit hash;
- current HEAD;
- git status;
- migration status/head;
- changed files count by layer;
- tests PASS count;
- Ruff;
- pip check;
- packaged exe path;
- exe size;
- dist size;
- screenshots path/count;
- docs/iteration4-review.md;
- Help article count;
- known issues;
- deferred items;
- что требует manual acceptance.

============================================================
27. SUCCESS CRITERIA
============================================================

После Iteration 4:

DATA:
- attached files принадлежат Studium;
- удаление исходника на диске их не ломает;
- файлы реально открываются;
- удаления не уничтожают unrelated Library content.

DAILY WORK:
- быстро отмечается посещаемость нескольким студентам;
- Seminar может содержать PDF + задачи;
- Problem Bank быстро показывает preview;
- Student Works показывает полную историю Attempt;
- Progress структурирован по Homework/RK и конкретным работам.

UX:
- меньше скрытых «Дополнительно»;
- таблицы настраиваются;
- sidebar спокойнее;
- академические периоды находятся в правильном месте;
- Group header очищен;
- Journal labels понятны;
- Content hierarchy соответствует реальной учебной структуре.

HELP:
- встроенная Справка существует;
- работает offline;
- Codex написал initial articles;
- Help модульная и дешёвая в дальнейшем сопровождении.

Главный принцип:

DATA MUST NOT DISAPPEAR.
FILES BELONG TO STUDIUM AFTER IMPORT.
DAILY TEACHING WORKFLOWS FIRST.
NO UNNECESSARY CLICKS.
HELP MUST DESCRIBE THE REAL APPLICATION.
