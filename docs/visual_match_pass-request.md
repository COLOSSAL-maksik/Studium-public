> Документ относится к Studium как независимому локальному приложению.
> Bender — отдельный проект; будущая интеграция использует локальный JSON-RPC
> 2.0 over stdio. Прямые импорты Bender, API/client, облачный сервер и новые
> возможности этим переносом не реализованы. Описания прежних фаз сохраняют
> технические требования; их проверки и acceptance не подтверждены этим текстом.

Продолжаем проект Studium в:


Это отдельный короткий шаг:
STRICT VISUAL MATCH PASS

Цель:
не заниматься сейчас ручной приёмкой функционала,
а максимально приблизить интерфейс Studium к приложенному визуальному референсу.

Файл-референс:

============================================================
1. ГЛАВНОЕ ПРАВИЛО
============================================================

Приложенный PNG — это не просто inspiration.
Это AUTHORITATIVE VISUAL REFERENCE.

Нужно не свободно интерпретировать “современный минимализм”,
а максимально близко воспроизвести визуальный язык референса
настолько, насколько это разумно возможно в PySide6/QSS.

Это не новый функциональный этап.
Это visual matching pass.

НЕ добавлять:
- новые domain entities;
- новые migrations;
- новую бизнес-логику;
- новые workflows;
- новые analytics rules;
- новые файлы БД/схемы.

Если для визуальной задачи внезапно нужен большой архитектурный refactor —
не делай его. Оставь как deferred.

============================================================
2. БЮДЖЕТ ЛИМИТА
============================================================

У нас ограниченный остаток квоты.

Работай экономно:
- не запускай полный suite после каждой правки;
- не перечитывай весь проект без необходимости;
- используй уже существующую Iteration 2.5 baseline;
- локально меняй UI и presentation слой;
- full pytest/ruff/pip check — только в финале этого шага;
- во время работы запускай только точечные smoke/targeted tests;
- используй pytest -q;
- verbose только если реально есть failure.

Если лимит закончится до завершения —
остановись в консистентной точке и отчитайся, что уже приведено к референсу, а что нет.

============================================================
3. ПРИОРИТЕТ ЭКРАНОВ
============================================================

Сначала привести к референсу следующие ключевые экраны:

PRIORITY A
1. App shell / Main window / global sidebar
2. Home
3. Discipline screen
4. Group Journal

PRIORITY B
5. WorkProgram
6. Homework / Work structure
7. Student × Work / Attempts
8. Analytics
9. Library / Problem Bank

PRIORITY C
10. Dialogs
11. Calendar
12. ComboBox popups
13. Topic/Skill pickers
14. Knowledge Base

Если не хватает времени/лимита:
сначала доведи Priority A до действительно близкого визуального результата,
а потом переходи дальше.

============================================================
4. ЧТО ИМЕННО НУЖНО СОВПАСТЬ ПО СТИЛЮ
============================================================

Смотри на референс и максимально повтори:

- общую композицию;
- proportions;
- spacing;
- typography hierarchy;
- sidebar width and feel;
- page padding;
- card geometry;
- border softness;
- surface layering;
- color calmness;
- compact but elegant tables;
- clean analytics blocks;
- modern header/breadcrumb feel;
- overall “product” look instead of CRUD/forms.

Нужный стиль:
- clean;
- calm;
- premium but restrained;
- academic;
- minimal;
- modern;
- not flashy;
- not enterprise-gray;
- not default Qt.

============================================================
5. ВИЗУАЛЬНЫЕ ПАРАМЕТРЫ
============================================================

Ориентировочно соблюдай такие параметры:

- sidebar width: ~220–240 px
- content max breathing padding: ~28–32 px
- page title size: ~26–30 px
- section title size: ~18–20 px
- body text: ~13–14 px
- secondary text: ~12–13 px
- card radius: ~10–12 px
- control radius: ~8 px
- border thickness: mostly 1 px, subtle
- very restrained shadow/elevation
- accent color used selectively, not everywhere
- whitespace generous on Home / Discipline / WorkProgram
- dense grid/table feel only in Journal

============================================================
6. LIGHT / DARK
============================================================

Обе темы должны выглядеть как единый продуманный дизайн,
а не как “светлая версия нормальная, тёмная вторичная”.

Проверить и довести:
- surfaces;
- text contrast;
- sidebar;
- cards;
- buttons;
- tabs;
- tables;
- selected states;
- hover;
- focus;
- calendar;
- combo popups;
- charts.

Dark theme:
не pure black,
а layered dark gray surfaces.

============================================================
7. APP SHELL
============================================================

Переделай глобальный shell максимально близко к референсу:

- левый sidebar;
- аккуратные icons;
- selected nav item;
- спокойный фон;
- качественная иерархия текста;
- content area с правильным воздухом;
- header/breadcrumb line.

Не делай грубые group boxes и тяжёлые рамки.

============================================================
8. HOME
============================================================

Home должен стать максимально похожим на референс.

Обязательно:
- три крупные входные tiles/cards:
  Работа
  Дисциплины
  Библиотека
- блок “Продолжить работу”
- современная композиция
- аккуратные counters/secondary text
- много воздуха
- хороший visual hierarchy

Не перегружать Home таблицами.

============================================================
9. DISCIPLINE SCREEN
============================================================

Сделай из него красивый course workspace:

- page title;
- subtitle / metadata;
- аккуратные крупные sections;
- удобные quick links;
- спокойные content blocks;
- не показывать всё как form/table одновременно.

Нужен feel близкий к референсу:
современный продуктовый экран, а не CRUD-detail-page.

============================================================
10. GROUP JOURNAL
============================================================

Это самый сложный экран.

Нельзя потерять плотность и скорость работы,
но визуально нужно сильно приблизить его к референсу/общему языку.

Что сохранить:
- fixed student column;
- modules;
- attendance / homework / RK;
- compact cells;
- planned/empty cells;
- collapse;
- filters.

Что улучшить:
- cleaner header bands;
- lighter table chrome;
- better spacing;
- less visual noise;
- more elegant cell states;
- subtle row hover;
- readable selected state;
- better grouping by module;
- overall modern data-grid look.

Journal не должен стать “воздушным” в ущерб работе.
Здесь принцип:
dense where needed.

============================================================
11. УБРАТЬ ДЕФОЛТНЫЙ QT-ВИД
============================================================

По возможности убрать ощущение default Qt в:

- QGroupBox
- QPushButton
- QToolButton
- QTabWidget/QTabBar
- QComboBox
- popup lists
- QCalendarWidget
- QTableView headers
- dialogs
- scrollbars
- line edits / text edits
- empty states

Если какой-то стандартный widget пока остаётся —
сделай хотя бы максимально близкую стилизацию.

============================================================
12. FORMS / DIALOGS
============================================================

Сделай формы визуально спокойнее и современнее:

- меньше “формальности”;
- лучше секции;
- primary/secondary action hierarchy;
- нормальная ширина;
- не растягивать мелкие диалоги;
- progressive disclosure where possible без изменения логики;
- убрать тяжёлые group box layouts.

============================================================
13. CALENDAR / COMBOBOX
============================================================

Обязательно стилизовать ближе к референсу:

Calendar:
- navigation
- selected day
- today
- hover
- month/year
- borders
- spacing

ComboBox/popup:
- normal
- hover
- selected
- dark mode
- readable contrast

Не оставлять системно-чёрные или визуально чужие popup.

============================================================
14. SCREENSHOT-DRIVEN REVIEW
============================================================

После ключевых изменений сделай screenshots и оцени их именно относительно референса.

Не ограничивайся формулировкой “modernized”.
Сравни visually:
- shell
- Home
- Discipline
- Journal

Если screen явно всё ещё выглядит как обычный Qt-admin UI —
продолжай доводку.

Сделай новый набор screenshots, например:
docs\screenshots\visual_match_pass

Минимум:
- Home light
- Home dark
- Discipline
- Journal
- WorkProgram
- Attempts
- Analytics
- Calendar
- Library

============================================================
15. ДОКУМЕНТИРОВАНИЕ
============================================================

Создай короткий отчёт:

docs/visual_match_pass.md

Укажи:
- что было переделано;
- какие экраны больше всего приблизились к референсу;
- что ещё пока отличается;
- какие default Qt элементы ещё остались;
- что стоит добить следующим шагом после ручной приёмки.

============================================================
16. ФИНАЛЬНЫЕ ПРОВЕРКИ
============================================================

В конце, один раз:

pytest -q
ruff format --check .
ruff check .
pip check

И packaged smoke:
- launch
- Home
- Discipline
- Journal
- theme switch
- reopen

NO NEW MIGRATION.

============================================================
17. ФИНАЛЬНЫЙ ОТЧЁТ
============================================================

В конце не создавай финальный commit.

Сообщи:
- current HEAD
- git status
- какие UI files изменены
- NO NEW MIGRATION confirmed
- pytest result
- Ruff result
- pip check
- exe path and size
- screenshot path/count
- report path
- что ещё заметно отличается от референса
- что обязательно проверить руками

============================================================
18. САМОЕ ВАЖНОЕ
============================================================

Главная цель этого шага:

сделать так, чтобы при первом взгляде на Studium
он воспринимался максимально близко к приложенному референсу,
а не просто как “ещё один улучшенный Qt UI”.

Если нужно выбирать между:
A) слегка расширить покрытие по экранам
и
B) сильнее приблизить Priority A screens к референсу,

выбирай B.

Лучше 4 экрана очень близко к референсу,
чем 12 экранов умеренно улучшены, но всё ещё не попадают в стиль.
