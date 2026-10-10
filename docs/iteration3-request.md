> Документ относится к Studium как независимому локальному приложению.
> Bender — отдельный проект; будущая интеграция использует локальный JSON-RPC
> 2.0 over stdio. Прямые импорты Bender, API/client, облачный сервер и новые
> возможности этим переносом не реализованы. Описания прежних фаз сохраняют
> технические требования; их проверки и acceptance не подтверждены этим текстом.

Продолжаем разработку Studium в:


Это ITERATION 3 — ACCEPTANCE FIXES + UX CONSOLIDATION.

Iteration 2 / 2.5 / visual match pass уже реализованы.
Пользователь начал ручную приёмку и собрал конкретный пакет замечаний.

Главная цель Iteration 3:

НЕ добавлять очередной большой слой функциональности,
а сделать уже существующий Studium логичным, цельным и удобным
в реальном преподавательском workflow.

Основные направления:
- навигация;
- Home;
- sidebar;
- Journal;
- Library;
- Problem Bank;
- responsive layouts;
- устранение неоднозначных/дублирующих элементов;
- минимальное расширение модели задач РК там, где это действительно нужно.

Сохраняй visual direction:
docs/design/studium-ui-reference.png

Стиль:
Linear Academic / calm modern academic UI.

Не откатывай visual match pass.

============================================================
0. SAFETY CHECKPOINT ПЕРЕД ITERATION 3
============================================================

Сначала:

git status
git diff --stat
git log --oneline -8

Текущее технически проверенное состояние перед Iteration 3:

- HEAD baseline:
  [историческая ссылка опущена]
- 585 tests PASS;
- Ruff PASS;
- pip check PASS;
- packaged smoke PASS;
- latest migration:
  0007_work_programs;
- свежий visual match pass уже находится в working tree;
- финальный пользовательский acceptance commit ещё не создавался.

Изучи только необходимые отчёты:

docs/iteration2-review.md
docs/iteration2_5-visual-review.md
docs/visual_match_pass.md

и текущий git diff.

НЕ перечитывай без необходимости весь docs tree
и все исторические документы.

Если рабочее дерево соответствует именно завершённым
Iteration 2.5 + visual match changes
и после последнего успешного full regression приложение не менялось,
создай safety checkpoint commit:

checkpoint: iteration 2.5 visual baseline before iteration 3

Не гоняй ради этого заново полный pytest,
если код после подтверждённого full PASS не менялся.

Если обнаружишь непонятные посторонние изменения —
не reset/checkout.
Сначала остановись и сообщи.

Финальный commit Iteration 3 НЕ создавать.
Сначала пользователь снова проведёт ручную приёмку.

============================================================
1. TOKEN / AGENT BUDGET POLICY
============================================================

Очень важно экономить Codex quota БЕЗ снижения качества.

Работай пакетами.

BATCH A:
Navigation + Home + Sidebar

BATCH B:
Library + Problem Bank + RK workflow

BATCH C:
Journal + forms + responsive UI

BATCH D:
migration/regression/package/docs

Во время разработки:

- НЕ запускай все ~585 tests после каждой правки;
- запускай только минимальный relevant test subset;
- используй pytest -q;
- при failure сначала запускай конкретный failing test;
- verbose только для диагностики;
- Ruff во время работы только по изменённым файлам;
- не запускай coverage;
- не делай PyInstaller build до финала;
- не делай десятки screenshot passes;
- не перечитывай крупные файлы повторно, если уже понял их структуру;
- избегай unrelated refactor.

Полный regression:
pytest -q

запустить один раз в финале.

Повторить полный suite только если после него пришлось менять
код, способный вызвать общий regression.

============================================================
2. НЕ РАСШИРЯТЬ SCOPE
============================================================

Не делать сейчас:

- AI;
- OCR;
- cloud;
- server;
- sync;
- tablet/mobile;
- student portal;
- email/Telegram integrations;
- prediction/mastery/ranking;
- новый экспортный subsystem;
- новый backup subsystem;
- автоматическое клонирование семестров;
- новые сложные analytics formulas;
- глубокий redesign всего приложения.

AI остаётся далеко в roadmap,
после зрелой desktop-версии и будущей tablet-версии.

Studium сейчас используется ТОЛЬКО преподавателем.

Student-facing workflows не нужны.

============================================================
3. НАВИГАЦИЯ BACK — HISTORY-BASED
============================================================

Сейчас Back работает непоследовательно.

Пример текущей проблемы:

Home
→ Недавняя группа
→ Group

Back сейчас отправляет пользователя в список групп Work,
хотя он пришёл с Home.

После этого второй Back может вообще ничего не делать.

Исправить navigation stack.

Правило:

Back возвращает на ФАКТИЧЕСКИ предыдущий экран,
из которого пользователь пришёл.

Примеры:

Home
→ recent group
→ Group
→ Back
= Home

Work
→ список групп
→ Group
→ Back
= список групп

Group
→ Student
→ Homework
→ Back
= Student
→ Back
= Group

Global sidebar items:

Home
Work
Disciplines
Library

считать root navigation.

При явном переходе через sidebar
можно начинать новый root stack,
чтобы история не превращалась в длинную бессмысленную цепочку.

На HOME Back вообще НЕ показывать.

Back button должен отображаться только тогда,
когда navigation history реально содержит предыдущий screen.

Добавить navigation regression tests.

============================================================
4. HOME — УПРОСТИТЬ
============================================================

Сейчас блоки:

«Продолжить работу»
и
«Недавние группы»

по смыслу дублируются.

Объединить их в ОДИН блок:

«Продолжить работу»

Внутри:

A. последняя активная группа — наиболее заметна;

B. ниже компактный список последних 2–4 групп.

Пример:

Продолжить работу

МТ6-31
Сопротивление материалов
7 неделя · Модуль 2

[последняя активная]

Недавние:
МТ6-32
МТ6-33

Клик на группу сразу открывает её рабочий контекст / Journal.

Отдельный блок «Недавние группы» убрать.

------------------------------------------------------------
4.1 Убрать дублирующее действие
------------------------------------------------------------

Сейчас строка recent group кликабельна,
но также существует кнопка «Открыть группу».

Кнопку убрать.

Оставить один obvious click target:
сама строка / карточка группы.

Добавить понятный hover state.

------------------------------------------------------------
4.2 Home Back
------------------------------------------------------------

Home — root screen.

Не показывать:
«Назад».

============================================================
5. GLOBAL SIDEBAR
============================================================

Текущий верхний уровень сохранить:

Главная
Работа
Дисциплины
Библиотека

Но сделать sections раскрываемыми на ОДИН уровень,
чтобы ускорить переходы.

НЕ превращать sidebar в большое tree view.

Пример:

Главная

▾ Работа
   МТ6-31
   МТ6-32
   Все группы

▸ Дисциплины

▾ Библиотека
   Домашнее задание
   Банк задач
   Рубежный контроль
   Семинары
   Лекции
   Литература
   Методические материалы

------------------------------------------------------------
5.1 Работа
------------------------------------------------------------

Показывать:
- максимум 2–4 recent groups;
- «Все группы».

Не показывать:
- студентов;
- ДЗ;
- отдельные работы;
- глубокую hierarchy.

------------------------------------------------------------
5.2 Дисциплины
------------------------------------------------------------

Показывать:
- максимум 2–4 recent/pinned disciplines;
- «Все дисциплины».

Не показывать WorkProgram/module hierarchy прямо в sidebar.

------------------------------------------------------------
5.3 Library
------------------------------------------------------------

Прямые быстрые переходы:

Домашнее задание
Банк задач
Рубежный контроль
Семинары
Лекции
Литература
Методические материалы

Запоминать expanded/collapsed state,
если это просто и не требует лишнего domain complexity.

============================================================
6. УБРАТЬ GLOBAL «ДОБАВИТЬ»
============================================================

Сейчас внизу sidebar есть глобальная кнопка:

+ Добавить

На текущем этапе она слишком абстрактна.

Убрать её из постоянного sidebar.

Основные create actions должны быть контекстными:

Disciplines:
+ Добавить дисциплину

Discipline:
+ Добавить рабочую программу
+ Добавить тему
+ Добавить навык

Work / Groups:
+ Добавить группу

WorkProgram:
+ Добавить модуль
+ Добавить домашнее задание
+ Добавить рубежный контроль

Problem Bank:
+ Добавить задачу

Library section:
+ Создать материал

И т.д.

Будущий global Quick Create
можно оставить как deferred design idea,
но сейчас не реализовывать.

============================================================
7. GROUP SCREEN — УБРАТЬ «КОНТЕКСТ»
============================================================

Справа сверху Group screen сейчас есть dropdown:

«Контекст»

с действием:
«Добавить дисциплину группе».

Для реального workflow пользователя
у группы почти всегда одна дисциплина в текущем рабочем контексте.

Этот permanent dropdown загромождает Group screen.

Убрать его из основной шапки.

Редкое действие:
«Добавить / изменить дисциплину группы»

перенести:

- в Group settings;
или
- в secondary overflow/rare actions menu.

Не держать его постоянно на виду.

============================================================
8. ТЕРМИНОЛОГИЯ
============================================================

В основных экранах использовать полные названия:

«Домашнее задание»

вместо:
«ДЗ»

«Рубежный контроль»

вместо:
«РК»

Исключение:
в очень плотном Journal допускаются сокращения:

ДЗ
РК

если полная форма ухудшает читаемость.

Проверить основные:
- Library tabs;
- headers;
- WorkProgram;
- dialogs;
- empty states;
- actions.

============================================================
9. LIBRARY — НОВАЯ ИНФОРМАЦИОННАЯ СТРУКТУРА
============================================================

Сейчас Library содержит дублирующиеся/неясные tabs:

«ДЗ и РК»
«Комплекты ДЗ»
«Семинары / лекции»

Перестроить Library tabs:

Домашнее задание
Банк задач
Рубежный контроль
Семинары
Лекции
Литература
Методические материалы

============================================================
10. LIBRARY → ДОМАШНЕЕ ЗАДАНИЕ
============================================================

Объединить текущие:

«ДЗ и РК»
+
«Комплекты ДЗ»

в части Homework.

Создать одну понятную вкладку:

«Домашнее задание»

Здесь хранить:

- комплекты условий Homework;
- общий PDF семестровых Homework;
- отдельные Homework condition files;
- связанные metadata;
- Discipline;
- Topics/tags при необходимости.

Не дублировать физически FileAsset.

Существующий HomeworkPack переиспользовать,
а не создавать параллельную модель,
если он уже решает задачу.

============================================================
11. LIBRARY → РУБЕЖНЫЙ КОНТРОЛЬ
============================================================

Очень важно разделить:

Problem Bank
и
готовые RK sets.

Problem Bank = исходные задачи.

«Рубежный контроль» = уже сформированные комплекты / наборы вариантов,
собранные ИЗ Problem Bank.

Workflow:

Problem Bank
→ фильтр задач для RK
→ выбрать задачи
→ сформировать набор вариантов
→ сохранить RK set
→ назначить группе / студентам.

Использовать существующие:
TicketSet
generator
snapshots
student assignment

если они уже соответствуют этой логике.

НЕ переписывать generator с нуля.

В Library → «Рубежный контроль»
показывать именно готовые наборы/варианты,
а не raw Problem items.

============================================================
12. PROBLEM BANK — PURPOSE / НАЗНАЧЕНИЕ ЗАДАЧ
============================================================

Задачи банка могут использоваться для разных целей:

- Семинар;
- Рубежный контроль;
- Экзамен;
- Консультация.

Одна задача МОЖЕТ иметь несколько назначений.

Например одна задача может использоваться:
- на семинаре;
- и в рубежном контроле.

Добавить/довести semantic field:

ProblemPurpose / UsageType

many-to-many / multi-select,
если текущая архитектура это позволяет.

Не использовать обычный free-form tag
вместо этого смысла,
если требуется явная бизнес-классификация.

Но:
сначала изучи существующий Problem model.

Если аналогичная semantic classification уже есть —
переиспользуй её.

Не плодить duplicate concept.

Filters Problem Bank должны включать:

- Discipline;
- Purpose;
- Topic;
- Skill;
- tag;
- collection;
- identifier/title.

============================================================
13. PROBLEM FAMILY / ОБЩЕЕ УСЛОВИЕ + ВАРИАНТЫ СХЕМ
============================================================

Новый реальный workflow пользователя:

есть, например, 20 вариантов одной задачи РК.

У всех:
- одинаковое текстовое условие;

но:
- разные расчётные схемы;
- возможно разные числовые параметры;
- разные ответы.

Не создавать 20 полностью дублированных Problem cards,
если это можно избежать.

Добавить/довести концепцию:

ProblemFamily / ProblemTemplate

с:

- Discipline;
- number/code;
- title;
- shared text statement;
- Topics;
- Skills;
- tags;
- collections;
- purposes.

У семьи:

ProblemVariant 1
ProblemVariant 2
...
ProblemVariant N

Каждый variant может хранить:

- variant number/code;
- scheme image(s);
- variable parameters / notes optional;
- correct answer optional;
- solution/reference files optional.

Главный пользовательский сценарий:

1. преподаватель вручную пишет ОБЩЕЕ условие;
2. добавляет изображение схемы варианта №1;
3. добавляет вариант №2;
4. прикладывает другую схему;
5. и т.д.

Не заставлять повторно вводить shared statement.

------------------------------------------------------------
13.1 Backward compatibility
------------------------------------------------------------

Существующие standalone Problem items НЕ ломать.

Поддержать оба сценария:

A. standalone problem;
B. problem family with variants.

Сначала проверь,
может ли текущая Problem entity быть parent/template,
а variants — children.

Если нужна новая schema:
использовать минимальную additive migration.

Следующий свободный migration number после 0007.

НЕ менять migrations 0001–0007.

============================================================
14. LIBRARY — СЕМИНАРЫ / ЛЕКЦИИ
============================================================

Сейчас:
«Семинары / лекции»

одной вкладкой.

Разделить:

«Семинары»
«Лекции»

Сохранять существующие data/entities.

Если backend уже различает LessonType,
не создавать новую domain model.

Это в основном UI/information architecture fix.

============================================================
15. LIBRARY — УБРАТЬ DUPLICATE CREATE
============================================================

В пустом Library screen сейчас одновременно есть:

«Создать материал»

и ниже:
«Создать»

Они делают одно и то же.

Оставить одно primary action.

Например:

[Создать материал]

или контекстное название:

[Добавить задачу]
[Добавить домашнее задание]
[Создать методический материал]

в зависимости от активной Library tab.

Не показывать duplicate actions.

============================================================
16. «ТЕМЫ, НАВЫКИ И НАБОРЫ» В PROBLEM BANK
============================================================

Сейчас disclosure:

«Темы, навыки и наборы»

висит отдельно посередине страницы.

Он визуально и функционально непонятен.

Убрать этот floating disclosure.

Если это filters:
встроить их в нормальный filter UX.

Предпочтительно:

основная строка:
Search
Discipline
Purpose

дополнительные filters:
Topic
Skill
Tags
Collection

Можно:
- раскрывать «Дополнительные фильтры» рядом со строкой;
или
- использовать compact filter side panel.

Но элемент не должен висеть отдельно
посреди пустого экрана.

В empty state показывать только meaningful actions.

============================================================
17. JOURNAL — FIX FROZEN FIO / HORIZONTAL SCROLL
============================================================

При горизонтальной прокрутке
закреплённая колонка ФИО визуально смещается относительно header/table.

Создаётся ощущение,
что FIO panel живёт отдельно от Journal.

Исправить.

Нужно:
- FIO column остаётся frozen;
- FIO header идеально совпадает с rows;
- row heights совпадают;
- header bands совпадают;
- vertical alignment не расходится;
- scrolling не создаёт seam/offset;
- separator между frozen и scrollable zone выглядит аккуратно.

По возможности воспринимать Journal как ОДИН grid,
даже если технически используются два synchronized views.

Проверить:
- Light;
- Dark;
- long FIO;
- resized window;
- horizontal scroll.

============================================================
18. JOURNAL — «НЕТ ДЗ» / «НЕТ РК»
============================================================

Сейчас в header появляются колонки:

«Нет ДЗ»
«Нет РК»

Это непонятно.

НЕ использовать эти надписи как будто это student status.

При этом сохранить ранее принятое требование:

Journal должен показывать STRUCTURE
Attendance / Homework / RK
даже если в конкретном module ещё нет созданной работы.

То есть не удалять сам структурный раздел.

Вместо «Нет ДЗ» / «Нет РК»:

предпочтительно:
- section header остаётся;
- внутри нет псевдо-work column;
- можно использовать subtle empty indicator в header,
  например «—»
  или небольшой empty hint вне student rows.

НЕ создавать колонку,
которая выглядит как реальная работа.

============================================================
19. UI RESPONSIVENESS / WINDOW RESIZE
============================================================

Обнаружена системная проблема:

некоторые screens/forms нормально видны только
при maximized/fullscreen window.

Это недопустимо.

Studium должен быть usable и в меньшем окне.

Проверить особенно:

- New Material;
- Work forms;
- WorkProgram dialogs;
- Attempt dialog;
- Topic/Skill screens;
- Library forms.

Правило:

если content помещается —
layout адаптируется;

если не помещается —
использовать ScrollArea.

Forms:
vertical scrolling.

Data grids:
horizontal scrolling при необходимости.

Нельзя:
- silently clip fields;
- терять Save/Cancel;
- перекрывать content;
- делать fullscreen обязательным.

Проверить минимум:

960×620
1240×780
maximized

и DPI:

100%
125%
150%.

Не делать полный screenshot set на каждом DPI.
Достаточно automated geometry checks + representative screenshots.

============================================================
20. NEW MATERIAL → «ДОПОЛНИТЕЛЬНО» LAYOUT BUG
============================================================

В форме:
Library → Новый материал

после раскрытия:
«Дополнительно»

часть содержимого / text area становится обрезана.

Исправить layout.

Expansion должен корректно:
- увеличивать content;
- перераскладывать controls;
- включать scroll при нехватке высоты.

Проверить:
- normal window;
- maximized;
- Light;
- Dark.

============================================================
21. FIELD «ПОРЯДОК»
============================================================

В нескольких forms есть числовое поле:

«Порядок»

Пользователь не понимает его смысла.

Сначала найди ВСЕ места,
где это поле присутствует,
и выясни его фактическую domain semantics.

Если это internal sort/order_index:

НЕ показывать его обычному пользователю как raw number.

Technical field можно оставить в domain/DB.

UI:

порядок определять автоматически по:
- module;
- week;
- item type;
- creation/order rules;

или менять через понятное действие:

Выше
Ниже

или drag-and-drop/reordering,
если это уже поддерживается просто.

Не добавлять сложный drag/drop subsystem,
если «Выше / Ниже» достаточно.

Если где-то поле «Порядок» имеет другой реальный business meaning —
не удаляй его автоматически.
Переименуй в понятный термин
или документируй отдельно.

============================================================
22. VISUAL LANGUAGE
============================================================

Сохранять текущий visual reference:

docs/design/studium-ui-reference.png

НЕ устраивать новый global redesign.

Iteration 3 должна:
- исправлять inconsistencies;
- улучшать responsiveness;
- сохранять Linear Academic language.

Не откатывать:
- sidebar style;
- typography;
- spacing;
- light/dark palette;
- current Home/Discipline visual language.

Library и forms можно подтянуть ближе к нему,
но без отдельного большого visual rewrite.

============================================================
23. MIGRATION STRATEGY
============================================================

Большинство Iteration 3 должно быть UI/application changes.

Новая migration допустима ТОЛЬКО если она действительно нужна для:

- Problem purpose classification;
- Problem family / variants.

Сначала максимально переиспользуй existing schema.

Если migration нужна:
- additive only;
- next free revision after 0007;
- preserve all old Problem items;
- preserve TicketSets;
- preserve files;
- preserve assignments;
- preserve generator snapshots.

No destructive migration.

Test:
fresh DB;
upgrade from current v7;
populated v7.

============================================================
24. TESTING — TARGETED DURING DEVELOPMENT
============================================================

Добавить targeted regression tests на:

Navigation:
- Home → recent group → Back → Home;
- Work → group → Back → Work;
- Home no Back;
- sidebar root navigation.

Home:
- merged Continue/Recent block;
- group row opens group;
- no duplicate Open button.

Sidebar:
- one-level expansion;
- recent group shortcuts;
- Library shortcuts.

Library:
- tab structure;
- no duplicate Create;
- Seminar/Lecture split;
- Homework consolidated;
- RK sets separate from Problem Bank.

Problem Bank:
- purpose filters;
- multi-purpose problem;
- standalone problem still works;
- family/shared statement;
- multiple variants;
- variant scheme attachments;
- old Problem records preserved.

Journal:
- no «Нет ДЗ/Нет РК» fake work columns;
- structural headers preserved;
- frozen FIO alignment;
- horizontal scroll.

Responsive:
- important controls accessible at 960×620;
- scroll area where needed.

Order:
- internal order remains valid;
- raw field absent from normal form where appropriate.

============================================================
25. FINAL FULL REGRESSION
============================================================

После завершения всех batches:

pytest -q
ruff format --check .
ruff check .
pip check

Если PASS:

собрать свежий PyInstaller onedir.

Packaged smoke:

- launch;
- Home;
- Back navigation;
- Sidebar;
- Group Journal;
- horizontal scroll;
- Library tabs;
- Homework;
- Problem Bank;
- RK set;
- New Material;
- Light/Dark;
- reopen.

Если новая migration появилась:
добавить packaged upgrade v7 → new revision.

============================================================
26. SCREENSHOTS
============================================================

Не создавать 50–100 screenshots.

Сделать компактный acceptance set,
примерно 12–16 PNG:

1. Home
2. Sidebar expanded Work
3. Sidebar expanded Library
4. Group Journal start position
5. Group Journal horizontally scrolled
6. Library Homework
7. Problem Bank
8. Problem Family detail
9. RK sets
10. Seminars
11. Lectures
12. New Material normal window
13. New Material advanced expanded
14. Dark Journal
15. Dark Library
16. optional narrow window

Сохранять, например:

docs/screenshots/iteration3

============================================================
27. DOCUMENTATION
============================================================

Создать:

docs/iteration3-review.md

Кратко описать:

- navigation stack;
- Home changes;
- sidebar;
- Library structure;
- Problem Bank purposes;
- Problem family/variants;
- Journal fixes;
- responsive fixes;
- «Порядок» audit;
- migration strategy, если migration появилась;
- tests;
- package;
- known limitations;
- manual acceptance checklist.

Не переписывать архитектурные документы целиком,
если изменения локальные.

Если ProblemFamily требует важного domain decision —
добавить один ADR.

============================================================
28. MANUAL ACCEPTANCE CHECKLIST
============================================================

После реализации пользователь должен руками проверить:

HOME
- нет Back;
- Continue + recent groups объединены;
- переход по группе;
- Back возвращает правильно.

SIDEBAR
- раскрывается один уровень;
- не перегружен;
- быстрый переход в группы/Library.

GROUP
- нет постоянного «Контекст»;
- Journal;
- horizontal scroll;
- FIO frozen;
- modules;
- empty Homework/RK state.

LIBRARY
- Домашнее задание;
- Банк задач;
- Рубежный контроль;
- Семинары;
- Лекции;
- Литература;
- Методические материалы.

PROBLEM BANK
- назначение Seminar/RK/Exam/Consultation;
- одна задача в нескольких purposes;
- family;
- common condition;
- 2–3 variants с разными scheme images.

RK
- сформировать set из Problem Bank;
- сохранить;
- открыть;
- student assignments intact.

RESPONSIVE
- 960×620;
- 1240×780;
- maximized;
- Light/Dark.

NEW MATERIAL
- «Дополнительно»;
- scroll;
- Save visible.

REOPEN
- navigation/theme/data preserved as expected.

============================================================
29. FINAL REPORT
============================================================

Финальный commit Iteration 3 НЕ создавать.

Сообщить:

- checkpoint commit hash;
- current HEAD;
- git status;
- migration status;
- changed domain/application/UI files count;
- tests PASS count;
- Ruff;
- pip check;
- exe path;
- exe size;
- dist size;
- screenshot path/count;
- docs/iteration3-review.md;
- known issues;
- deferred items;
- что требует ручной acceptance.

============================================================
30. SUCCESS CRITERIA
============================================================

После Iteration 3 пользователь должен ощущать:

- навигация предсказуема;
- Back всегда делает ожидаемое;
- Home не дублирует действия;
- sidebar ускоряет работу, но не перегружен;
- Library имеет понятную предметную структуру;
- raw Problem Bank отделён от готовых RK sets;
- одинаковые условия задач не приходится копировать 20 раз;
- Journal визуально цельный при horizontal scroll;
- формы работают не только fullscreen;
- технические поля не торчат в пользовательский UX;
- никакая существующая история/файлы/назначения не потеряны.

Главный принцип:

LESS DUPLICATION.
LESS TECHNICAL UI.
MORE CONTEXT.

И при этом:
NO LOSS OF FUNCTIONALITY.
