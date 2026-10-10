> Документ относится к Studium как независимому локальному приложению.
> Bender — отдельный проект; будущая интеграция использует локальный JSON-RPC
> 2.0 over stdio. Прямые импорты Bender, API/client, облачный сервер и новые
> возможности этим переносом не реализованы. Описания прежних фаз сохраняют
> технические требования; их проверки и acceptance не подтверждены этим текстом.

Продолжаем разработку Studium в:


Это ITERATION 2.5 — VISUAL POLISH / UI CONSOLIDATION.

Iteration 2 уже реализована, собрана и технически проверена:
- HEAD перед Iteration 2: [историческая ссылка опущена]
- migration 0007_work_programs
- 577 tests PASS
- Ruff PASS
- pip check PASS
- packaged build PASS
- docs/iteration2-review.md
- screenshots:

Пользователь ещё НЕ проводил полноценную ручную acceptance-проверку Iteration 2.

Причина запуска Iteration 2.5 сейчас:
пользователь хочет проводить ручную приёмку уже на новом, современном интерфейсе, а не тестировать UI, который всё равно планируется заметно переработать.

============================================================
0. КРИТИЧЕСКОЕ ОГРАНИЧЕНИЕ
============================================================

Iteration 2.5 — НЕ новая функциональная итерация.

НЕ добавлять:
- новые domain entities;
- новую бизнес-логику;
- новые Alembic migrations;
- изменения схемы БД;
- AI;
- OCR;
- server/sync;
- mobile/tablet;
- новые внешние integrations;
- student portal;
- новые analytics formulas;
- новые крупные workflows.

Основная задача:
переработать PRESENTATION / UI / UX COMPOSITION уже существующего функционала.

Допустимы только небольшие технические изменения application/UI слоя,
если они объективно нужны для корректного отображения уже существующих данных.

Если для визуальной задачи внезапно требуется изменение domain model —
НЕ делай его.
Зафиксируй как deferred / Iteration 3.

============================================================
1. СНАЧАЛА СОЗДАЙ БЕЗОПАСНУЮ ТОЧКУ ITERATION 2
============================================================

Сначала:

git status
git diff --stat
git log --oneline -10

Проверь, что текущее рабочее дерево соответствует завершённой Iteration 2,
описанной в docs/iteration2-review.md.

ВАЖНО:
не делай reset/checkout существующих изменений.

Если с момента финального успешного отчёта Iteration 2 код НЕ менялся
и текущие изменения соответствуют именно этой итерации,
не трать лимит повторно на полный regression suite только ради checkpoint.

Создай safety checkpoint commit:

checkpoint: complete iteration 2 before visual polish

Этот commit НЕ означает пользовательскую acceptance Iteration 2.
Это только техническая точка возврата перед большим UI refactor.

Если после последнего успешного full test run код всё-таки менялся —
перед checkpoint выполни:

pytest -q

и только при PASS создай checkpoint.

После checkpoint начинай Iteration 2.5.

Финальный commit самой Iteration 2.5 НЕ создавать.
После UI redesign пользователь сначала проведёт ручную приёмку.

============================================================
2. TOKEN / AGENT BUDGET POLICY
============================================================

Нужно экономно расходовать Codex quota без снижения качества.

Во время реализации:

- НЕ запускай все ~577 tests после каждой UI-правки.
- Используй только минимальный relevant test subset.
- Используй pytest -q.
- При failure сначала запускай конкретный failing test.
- Verbose output использовать только для диагностики failure.
- Ruff во время работы запускать только для затронутых файлов/пакетов.
- Полный pytest + полный Ruff — только в финальной контрольной точке.
- pip check — только в финале.
- Не запускай coverage без необходимости.
- Не перечитывай повторно большие docs/files, если уже извлёк нужную информацию.
- Не делай повторный полный screenshot sweep после каждой мелкой правки.

Полный regression suite обязателен в финале,
но не должен выполняться десятки раз в процессе.

============================================================
3. ВИЗУАЛЬНОЕ НАПРАВЛЕНИЕ
============================================================

Выбран visual direction:

"Linear Academic"
с небольшими элементами современного Fluent UI.

НЕ копировать конкретный коммерческий продукт буквально.

Нужен собственный стиль Studium:

- современный;
- минималистичный;
- спокойный;
- профессиональный;
- академический;
- Windows-native feeling;
- высокая информационная плотность там, где она нужна;
- много воздуха там, где пользователь читает/настраивает;
- без ощущения бухгалтерской программы;
- без ощущения CRUD/admin panel;
- без визуального перегруза.

Главный принцип:

LESS FORM, MORE PRODUCT INTERFACE.

То есть вместо:

Label
ComboBox
Label
LineEdit
GroupBox
GroupBox
GroupBox

стремиться к предметным экранам, где пользователь видит:

ДЗ1
Темы
Навыки
Условия
Части работы
История
и понятные actions.

============================================================
4. DESIGN SYSTEM
============================================================

Сначала создай единый UI design system,
а не стилизуй каждый экран отдельно.

Нужно определить reusable tokens:

Typography:
- page title;
- section title;
- body;
- secondary;
- caption;
- table text.

Spacing:
- XS / S / M / L / XL.

Radii:
- умеренные;
- не превращать всё в pill/card UI.

Surfaces:
- app background;
- navigation;
- primary surface;
- secondary surface;
- elevated dialog/popup.

Borders:
- лёгкие;
- использовать только там, где они помогают структуре.

Colors:
- neutral-first;
- один основной accent;
- restrained semantic colors.

States:
- normal;
- hover;
- pressed;
- selected;
- focus;
- disabled.

Semantic states:
- success;
- warning/revision;
- error;
- informational.

Не использовать десятки разных цветов.

============================================================
5. LIGHT / DARK
============================================================

Iteration 2 уже содержит Light/Dark поддержку.

Теперь сделать обе темы полноценными.

Не должно быть экранов,
которые просто "инвертировали фон".

Проверить:

- MainWindow;
- sidebar;
- Home;
- cards;
- tables;
- dialogs;
- ComboBox;
- popup lists;
- calendar;
- scrollbars;
- tabs;
- tooltips;
- charts;
- empty states;
- file previews;
- selection;
- disabled elements;
- hover;
- focus.

Dark mode должен быть аккуратным,
не pure black everywhere.

============================================================
6. MAIN WINDOW / SHELL
============================================================

Создать цельный application shell.

Главная структура:

LEFT NAVIGATION
+
CONTENT AREA

Global navigation:

Главная
Работа
Дисциплины
Библиотека
Добавить
Настройки

Sidebar:
- компактный;
- визуально спокойный;
- понятный selected state;
- нормальные icons;
- не слишком широкий;
- хорошо работает в Light/Dark.

Не делать огромные цветные кнопки.

Использовать icons + text.

============================================================
7. GLOBAL CONTEXT / BREADCRUMBS
============================================================

Внутри приложения пользователь всегда должен понимать,
где находится.

Использовать аккуратные breadcrumbs / context bar.

Пример:

Сопротивление материалов
/
МТ 2026
/
МТ6-31
/
ДЗ1

Breadcrumbs не должны занимать много места.

Под ними:

page title
optional subtitle
primary actions.

============================================================
8. HOME SCREEN
============================================================

Home должен выглядеть как настоящий product start screen.

Основные входы:

РАБОТА
ДИСЦИПЛИНЫ
БИБЛИОТЕКА

Не делать маленькие круглые buttons.

Использовать три крупные современные tiles/cards.

Каждая:
- icon;
- title;
- короткое description;
- click target.

Например:

Работа
Журналы, группы и текущая деятельность

Дисциплины
Рабочие программы, темы, навыки и планы

Библиотека
Задачи, ДЗ, материалы и литература

Также блок:

Продолжить работу

МТ6-31
Сопротивление материалов
7 неделя · Модуль 2

[Открыть журнал]

Не перегружать Home аналитикой.

============================================================
9. DENSITY STRATEGY
============================================================

Очень важно:

разным экранам нужна разная плотность.

HOME / DISCIPLINE / WORK PROGRAM:
больше воздуха.

JOURNAL:
очень плотный профессиональный рабочий экран.

ANALYTICS:
средняя плотность + пространство для графиков.

FORMS:
умеренная плотность,
progressive disclosure.

Не использовать одинаковый "card layout" везде.

============================================================
10. GROUP JOURNAL
============================================================

Journal — главный ежедневный экран.

Он должен быть наиболее функционально плотным,
но визуально чистым.

Сохранить текущую Iteration 2 функциональность:

- Modules;
- Attendance;
- Homework;
- RK;
- students rows;
- planned empty cells;
- sticky FIO;
- filters;
- module collapse;
- click actions.

Визуально:

- минимизировать лишние borders;
- grouping Modules делать через header bands;
- явная hierarchy:
  Module
    Attendance
    Homework
    RK

- компактные status cells;
- хороший row hover;
- выбранная cell;
- selected student row;
- sticky left student column;
- sticky headers;
- readable horizontal scroll.

Не превращать Journal в карточки.

Journal должен выглядеть как современный data grid.

Основные состояния ячеек должны читаться быстро,
но semantic color использовать экономно.

============================================================
11. DISCIPLINE SCREEN
============================================================

Экран Discipline должен ощущаться как workspace курса.

Пример composition:

Сопротивление материалов

[краткое описание / metadata]

Рабочие программы
3 программы

Темы и навыки
...

Банк задач
...

Методические материалы
...

Литература
...

Не обязательно все блоки делать cards.

Можно использовать:
- sections;
- lists;
- counters;
- quick links.

============================================================
12. WORK PROGRAM SCREEN
============================================================

WorkProgram — "план семестра".

Визуально показать:

- Semester;
- duration;
- modules;
- official PDF;
- Homework/RK;
- Topics;
- seminar/lecture materials;
- Literature;
- groups using program.

Module structure желательно визуально показать
как спокойную горизонтальную/вертикальную timeline-like hierarchy,
но без сложной custom graphics,
если это увеличит риск/стоимость.

============================================================
13. WORK / HOMEWORK SCREEN
============================================================

Использовать предметный интерфейс.

Вместо огромного form layout:

ДЗ1

Структура работы

Темы
[Изгиб] [Плоский изгиб]
+ Добавить

Навыки
[Эпюра Q] [Эпюра M]
+ Добавить

Условия
dz_semester.pdf
Открыть

Части работы
1. Реакции опор
2. Эпюра Q
3. Эпюра M

То есть информация сначала читается,
редактирование вызывается понятными actions.

============================================================
14. STUDENT × WORK / ATTEMPTS
============================================================

Особенно тщательно переработать этот экран.

Он был визуально перегружен.

Нужна композиция:

Иванов Иван Иванович
ДЗ1

Current state:
Зачтено
Попыток: 3
Балл: —

Primary action:
+ Новая попытка

История попыток

№   Дата   Результат   Балл   Комментарий

Selected attempt detail:
- статус;
- comment;
- files.

Не держать огромный file area постоянно раскрытым.

Исправить все layout overlap bugs.

============================================================
15. CONTROL WORK CHECKING
============================================================

РК должен выглядеть как review workspace.

Например:

РК1
Иванов Иван Иванович

Задача 1
✓ зачтена
Навыки:
✓ реакции опор
✓ эпюра Q
✕ эпюра M

Задача 2
...

Сохранять существующую бизнес-логику.

Сделать результат визуально понятным без чтения длинных таблиц.

Не использовать green/red background на всю карточку.
Semantic color применять локально.

============================================================
16. ANALYTICS
============================================================

Analytics должна стать визуально сильным экраном.

Но:
не превращать её в BI dashboard.

Использовать:
- крупные key numbers;
- 2–4 основных графика;
- tabs/filters;
- radial/line switch;
- Topics/Skills evidence.

Radial chart:
оставить главным distinctive visualization.

Line chart:
чистый минималистичный style.

Charts должны хорошо выглядеть Light/Dark.

Cards вокруг каждого графика не обязательны,
если hierarchy и так понятна.

============================================================
17. FORMS / DIALOGS
============================================================

Все forms пересмотреть.

Убрать ощущение:

"30 полей одновременно".

Использовать progressive disclosure.

Сразу показывать только основные поля.

Rare/advanced:
"Дополнительно"

Dialogs:
- нормальный max width;
- понятный title;
- compact action area;
- primary button;
- secondary Cancel;
- не растягивать на всё окно без необходимости.

============================================================
18. DATE / CALENDAR
============================================================

Сделать Calendar визуально современным.

Проверить:

- month navigation;
- year selector;
- weekday names;
- selected;
- today;
- hover;
- focus;
- weekends;
- light;
- dark.

Убрать ощущение default Qt widget.

Не ломать keyboard accessibility.

============================================================
19. COMBOBOX / POPUPS
============================================================

Стилизовать все dropdown/popups consistently.

Проверить:
- text contrast;
- hovered option;
- selected;
- disabled;
- popup border;
- scroll;
- Light/Dark.

Не должно быть:
black unreadable dropdown
или системного popup, выбивающегося из интерфейса.

============================================================
20. TOPIC / SKILL PICKERS
============================================================

Iteration 2 уже должна исправлять функциональность pickers.

Теперь сделать их визуально понятными.

Selected values:
chip/tag-like elements,
но не слишком pill-heavy.

Actions:
+ Добавить
Удалить связь
Создать новый

Empty state должен быть визуально явным.

============================================================
21. LIBRARY
============================================================

Library должна ощущаться как content browser.

Sections:

Банк задач
Комплекты ДЗ
РК / варианты
Методические материалы
Семинары / лекции
Литература

Для Problem Bank:
можно использовать compact cards/list hybrid.

Карточка Problem:
№
название
Topics
tags
collection
attachments indicator.

Не показывать все metadata сразу.

============================================================
22. KNOWLEDGE BASE
============================================================

Knowledge Base визуально сделать похожей
на хорошо организованную справочную систему,
а не CRUD table.

List:
title
type
Topic
occurrences

Detail:
canonical question/error
answer/explanation
Topics
Skills
related materials
sources count.

============================================================
23. EMPTY STATES
============================================================

Unified empty state system.

Например:

Навыков пока нет
Создайте первый навык для дисциплины.

[Создать навык]

Не использовать огромные серые пустые widgets.

============================================================
24. ICONOGRAPHY
============================================================

Использовать один coherent icon set,
доступный без проблем с лицензированием/packaging.

Не смешивать:
- emoji;
- random Qt icons;
- bitmap icons разных стилей.

Icons должны быть простыми line-style / modern.

Не увеличивать существенно dist size ради icons.

============================================================
25. TYPOGRAPHY
============================================================

Не добавлять внешние proprietary fonts.

Использовать хороший системный Windows font stack,
предпочтительно Segoe UI / Segoe UI Variable где доступно.

Определить hierarchy:
Page title
Section
Body
Secondary
Caption

Не использовать слишком много bold.

============================================================
26. ANIMATIONS
============================================================

Минимально.

Допустимы:
- лёгкий hover;
- selection transition;
- collapse/expand если просто и стабильно.

Не добавлять сложные animations,
которые могут тормозить PySide6 UI.

============================================================
27. ACCESSIBILITY / KEYBOARD
============================================================

Не потерять существующую keyboard navigation.

Проверить:
- Tab order;
- focus ring;
- Enter;
- Escape;
- table keyboard;
- dialog actions.

Focus state должен быть видимым,
но не кричащим.

============================================================
28. DPI / WINDOW SIZES
============================================================

Обязательно проверить:

100%
125%
150%

Также:
- normal laptop window;
- maximized;
- narrower window.

Не допускать:
- overlap;
- clipped buttons;
- truncated controls;
- unusable horizontal layout.

============================================================
29. SCREENSHOTS / VISUAL REVIEW
============================================================

Используй существующие Iteration 2 screenshots
как BEFORE reference.

После завершения Iteration 2.5 сделать новый screenshot set:

docs\screenshots\iteration2_5

Минимум:

1. Home Light
2. Home Dark
3. Discipline
4. WorkProgram
5. Modules
6. Group Journal
7. Journal with Module collapsed
8. Homework
9. Student × Homework
10. Attempt dialog
11. RK task checking
12. Problem Bank
13. Analytics radial
14. Analytics line
15. Student Progress
16. Knowledge Base
17. Topics/Skills
18. Calendar Light
19. Calendar Dark
20. Library

Также screenshots:
100%
125%
150%

Не надо делать 100+ screenshots без необходимости.
Достаточно хорошего representative set.

============================================================
30. TESTING STRATEGY
============================================================

Во время UI redesign:
использовать targeted tests.

После завершения всей реализации:

pytest -q
ruff format --check .
ruff check .
pip check

Все existing tests должны пройти.

Не удалять tests ради UI refactor.

Если после final full test пришлось менять functional code —
запустить relevant tests,
а затем финальный full pytest ещё один раз.

============================================================
31. PACKAGE
============================================================

Создать свежий PyInstaller onedir build.

Проверить:

- launch;
- Home;
- Light/Dark;
- Discipline;
- WorkProgram;
- Journal;
- Homework;
- Attempt;
- RK checking;
- Analytics;
- Calendar;
- Library;
- reopen.

Проверить upgrade существующей Iteration 2 DB.

Iteration 2.5 НЕ должна создавать новую migration.

============================================================
32. DOCUMENTATION
============================================================

Создать:

docs/iteration2_5-visual-review.md

Описать:

- visual direction;
- design tokens;
- navigation shell;
- page density strategy;
- changed screens;
- Light/Dark;
- remaining visual limitations;
- any places where old widgets remain;
- manual acceptance checklist.

Не переписывать всю architecture documentation без необходимости.

Обновлять только UI/navigation/design docs,
которые реально изменились.

============================================================
33. FINAL REPORT
============================================================

Финальный commit Iteration 2.5 НЕ создавать.

В конце сообщить:

- checkpoint commit hash Iteration 2;
- current HEAD;
- git status;
- изменённые UI files;
- подтверждение: NO NEW MIGRATION;
- test count / PASS;
- Ruff;
- pip check;
- exe path;
- exe size;
- dist size;
- screenshot count/path;
- visual review doc;
- known issues;
- что проверить руками.

============================================================
34. MANUAL ACCEPTANCE AFTER ITERATION 2.5
============================================================

Пользователь будет одновременно принимать:
- Iteration 2 functionality;
- Iteration 2.5 UI.

Подготовь checklist:

Home
→ Работа
→ группа
→ Journal

Discipline
→ WorkProgram
→ Modules

Homework
→ Attempts

Control Work
→ tasks
→ skills

Analytics
→ radial
→ line

Knowledge Base

Light/Dark

Calendar

Explorer drag/drop

Reopen.

============================================================
35. ГЛАВНАЯ ЦЕЛЬ
============================================================

После Iteration 2.5 Studium должен ощущаться как:

современное профессиональное приложение преподавателя,

а НЕ:

набор Qt forms
+
CRUD tables
+
dialogs.

При этом нельзя жертвовать плотностью и скоростью ежедневной работы.

Главное визуальное правило:

CALM OUTSIDE,
DENSE WHERE NEEDED.

Home / Discipline / WorkProgram:
чисто и просторно.

Journal:
плотно и быстро.

Analytics:
визуально и спокойно.

Forms:
только необходимое,
остальное раскрывается по запросу.

Не меняй бизнес-логику Iteration 2 ради красоты.
