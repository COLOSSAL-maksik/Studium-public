> Документ относится к Studium как независимому локальному приложению.
> Bender — отдельный проект; будущая интеграция использует локальный JSON-RPC
> 2.0 over stdio. Прямые импорты Bender, API/client, облачный сервер и новые
> возможности этим переносом не реализованы. Описания прежних фаз сохраняют
> технические требования; их проверки и acceptance не подтверждены этим текстом.

Начинаем первую итерацию пользовательских доработок Studium.

Назови её:

Phase 6.6 — Workflow, Content Libraries & UX Iteration 1

КОНТЕКСТ

Phase 0–6 завершены.
Phase 6.5 технически завершена и прошла проверки:

- 475 tests PASS;
- Ruff PASS;
- native Windows smoke PASS;
- packaged Studium.exe PASS;
- DPI 100/125/150% PASS.

Но Phase 6.5 ещё не закоммичена.

После ручного использования приложения сформирован первый пакет
пользовательских требований.

Главная цель этой итерации:

1. сделать навигацию Studium понятнее;
2. убрать ощущение множества отдельных окон;
3. упростить и осовременить интерфейс без потери возможностей;
4. добавить базы учебных материалов;
5. добавить банк задач и генератор вариантов;
6. улучшить работу со сроками/учебными неделями;
7. расширить посещаемость лекциями;
8. добавить визуальные графики аналитики;
9. сохранить Studium offline-first.

Не начинать server/sync/mobile/AI phase.

==================================================
0. СНАЧАЛА ЗАФИКСИРОВАТЬ PHASE 6.5
==================================================

До любых изменений:

1. Прочитай:
   - AGENTS.md
   - README.md
   - docs/architecture.md
   - docs/data-model.md
   - docs/ui-navigation.md
   - docs/analytics.md
   - docs/decisions.md
   - docs/phase65-review.md
   - docs/done.md
   - docs/todo.md

2. Выполни:
   git status

3. Убедись, что текущие незакоммиченные изменения действительно
   соответствуют завершённой Phase 6.5.

4. Повторно выполни:

   ruff format --check .
   ruff check .
   pytest

5. Если baseline зелёный, БЕЗ каких-либо изменений содержимого создай commit:

   feat: complete Studium phase 6.5 desktop UX

6. Remote не создавать.

После этого Phase 6.6 начинается с чистого working tree.

==================================================
1. ЗАФИКСИРОВАТЬ СТРАТЕГИЮ ПРОЕКТА
==================================================

Studium остаётся:

- Windows-first;
- local-first;
- offline-first.

В этой итерации НЕ подключать:

- AI;
- LLM;
- AI agents;
- OCR;
- cloud;
- FastAPI;
- PostgreSQL;
- synchronization;
- Android/tablet client;
- Telegram API;
- email API;
- Gmail;
- IMAP.

Вопросы по Telegram и email остаются ТОЛЬКО ручным вводом.

Не удалять существующие channel enum EMAIL/TELEGRAM:
они обозначают происхождение вручную внесённого сообщения.

Обновить roadmap/decisions так, чтобы AI,
live communications и server были явно отложенными возможностями,
а не ближайшими задачами.

==================================================
2. ЕДИНОЕ ГЛАВНОЕ ОКНО
==================================================

Текущая проблема:

слишком много действий открывают отдельные самостоятельные окна/dialogs.

Пользователь хочет модель:

нажал -> перешёл глубже;
Back -> вернулся.

Основная навигация должна происходить ВНУТРИ одного MainWindow.

Реализовать navigation stack / router для desktop presentation.

Пример:

Группы
  -> МТ5-31
      -> Иванов
          -> ДЗ №3
              -> Попытка №2

Кнопка Назад:

Попытка -> ДЗ -> Иванов -> группа.

Использовать dialogs только там, где dialog действительно естественен:

- подтверждение;
- маленький быстрый ввод;
- file picker fallback;
- критическая ошибка.

Не открывать отдельные большие top-level окна
для карточек студента, работ, тем, занятий, файлов и т.п.

Предпочитать:
- page inside main content area;
- details page;
- tabs inside context page.

Не ломать application/domain boundary.

==================================================
3. ЛЕВАЯ НАВИГАЦИЯ
==================================================

Перестроить sidebar.

Предпочтительно:

Обзор

Группы ▾
    МТ5-31
    МТ5-32
    ...

Материалы / Библиотека
Добавить
Настройки

Группы должны быть раскрываемыми прямо в sidebar,
чтобы пользователь мог одним нажатием открыть конкретную группу.

Группы отображать в контексте активного периода/дисциплины
понятным образом.

Глобальный пункт:

Вопросы

из левого sidebar УБРАТЬ.

Вопросы остаются доступны:

- внутри группы;
- внутри карточки студента;
- в контексте работы/попытки, если есть связь.

Не удалять communication domain.

==================================================
4. КНОПКА "ДОБАВИТЬ"
==================================================

Создание:

- AcademicTerm;
- Course;
- StudentGroup;

используется редко.

Убрать постоянно видимые большие кнопки
"Новый период", "Новая группа", "Новая дисциплина"
с главных ежедневных экранов.

Добавить единый navigation item/action:

Добавить

Он открывает внутреннюю страницу:

Добавить

- Учебный период
- Дисциплину
- Группу
- при необходимости другие редко создаваемые базовые сущности.

Эта страница должна быть простой и понятной.

Главный интерфейс не должен быть засорён administrative CRUD actions.

==================================================
5. ВИЗУАЛЬНОЕ УПРОЩЕНИЕ
==================================================

Общий интерфейс сделать современнее и визуально проще
БЕЗ потери функциональности.

Не делать декоративный redesign ради красоты.

Принципы:

- меньше постоянно видимых второстепенных кнопок;
- больше контекстных действий;
- понятная hierarchy;
- больше внутренней навигации;
- стабильные header/breadcrumb/back;
- меньше визуального шума;
- одинаковая логика экранов.

Продолжать использовать PySide6/Qt.
Не подключать сторонний UI framework.

Развивать существующий централизованный QSS/theme.

==================================================
6. ИСПРАВИТЬ QCOMBOBOX / DROPDOWN BUG
==================================================

Есть подтверждённый UI bug:

в выпадающих списках текущий выбранный элемент читается,
но некоторые другие элементы dropdown имеют чёрную заливку,
из-за чего текст становится практически невидимым.

Исправить QSS/palette для:

- QComboBox;
- QAbstractItemView popup;
- normal item;
- selected item;
- hover item;
- focus;
- disabled state.

Проверить в light theme на Windows.

Все пункты списка должны иметь читаемый foreground/background.

Добавить Qt smoke/component test насколько это разумно.

==================================================
7. DATE PICKER
==================================================

Текущий календарь выбора даты:

- визуально выглядит плохо;
- выбор даты неочевиден;
- дата воспринимается выбранной только после дополнительного действия.

Исправить date picker:

- нормальный единый QSS;
- понятный selected day;
- обычный клик по дню должен выбирать значение;
- значение в форме должно сразу обновляться;
- popup должен вести себя естественно;
- не требовать дополнительного клика по строке/полю после выбора.

Но см. раздел об учебных неделях:
для плановой выдачи/сдачи работ основной UI должен перейти на week selector.

Date picker остаётся для фактических календарных дат там,
где календарная дата действительно нужна.

==================================================
8. УЧЕБНЫЕ НЕДЕЛИ
==================================================

Добавить first-class понятие учебной недели.

Нумерация:

1, 2, 3, ...

Правило:

нечётные недели:
"числитель"

чётные недели:
"знаменатель"

UI label:

1 неделя — числитель
2 неделя — знаменатель
5 неделя — числитель
6 неделя — знаменатель

Создать domain/value object или эквивалентную чистую модель:

AcademicWeekNumber

с validation >= 1.

Не хранить текст "числитель/знаменатель" отдельно,
он вычисляется из номера недели.

==================================================
9. ПЛАНОВЫЕ НЕДЕЛИ ДЛЯ РАБОТ
==================================================

Для Homework / Control work и других подходящих Assessment
планирование должно происходить прежде всего по УЧЕБНОЙ НЕДЕЛЕ,
а не через обязательную календарную дату.

Добавить:

planned_issue_week nullable
planned_due_week nullable

или эквивалентную модель.

UI:

Выдача:
[5 неделя — числитель]

Сдача:
[7 неделя — числитель]

Не заставлять пользователя выбирать точную дату.

Старые date fields не уничтожать молча.

Нужно:

- сохранить backward compatibility;
- документировать legacy/fallback semantics;
- мигрировать schema безопасно.

Если exact issue/deadline date существует,
она может остаться optional для специальных случаев.

Для обычного workflow приоритет — academic week.

==================================================
10. АНАЛИТИКА СРОКОВ ПО НЕДЕЛЯМ
==================================================

Обновить analytics semantics.

Если Assessment имеет planned_due_week,
своевременность рассчитывать относительно учебной недели.

Фактическая Attempt имеет календарный timestamp.

Определять academic week фактического предъявления
относительно AcademicTerm start date.

Если exact deadline задан явно,
необходимо определить documented priority rule.

Предпочтительно:

explicit exact deadline > planned week

или другой безопасный вариант,
но обязательно документировать.

Не ломать историческую аналитику старых данных.

==================================================
11. ЛЕКЦИИ И СЕМИНАРЫ
==================================================

Сейчас Lesson нужно расширить типом занятия.

Добавить:

LessonType

минимум:

SEMINAR
LECTURE

Русский UI:

Семинар
Лекция

Посещаемость лекций может вводиться вручную
по информации, полученной пользователем от лектора.

В UI пользователь должен уметь:

- создать лекцию;
- создать семинар;
- отметить attendance одинаковым существующим механизмом.

Analytics attendance должна позволять:

- общую посещаемость;
- отдельно семинары;
- отдельно лекции.

Не создавать отдельную параллельную attendance subsystem.

==================================================
12. БАЗА ДОМАШНИХ ЗАДАНИЙ
==================================================

Добавить библиотеку/банк выданных домашних заданий.

Это НЕ StudentWork и НЕ Attempt.

Нужен reusable учебный материал/шаблон условия.

Например:

HomeworkDefinition / HomeworkTemplate
или другое согласованное имя.

Минимально:

- id UUID;
- Course;
- title;
- number/label optional;
- description/text;
- tags;
- files;
- notes;
- archive metadata.

Пример:

ДЗ №3
"Построение эпюр Q и M для балки"

Условие может содержать:

- текст;
- изображения;
- PDF;
- другие файлы.

Использовать существующий FileAsset storage pipeline.

Не дублировать файловое хранилище.

Assessment должен уметь ссылаться
на выбранное HomeworkDefinition/Template,
если работа была выдана из базы.

При этом historical Assessment остаётся самостоятельным фактом.

==================================================
13. БАНК КОНТРОЛЬНЫХ / БАНК ЗАДАЧ
==================================================

Создать полноценный Problem Bank.

Это одна из ключевых новых функций.

Domain entity:

Problem / TaskDefinition
или согласованное имя.

Каждая задача должна иметь минимум:

- UUID;
- Course;
- title;
- statement text;
- tags;
- difficulty/set/group labels при необходимости;
- notes;
- metadata;
- attachments.

Примеры tags:

балки
рамы
фермы
изгиб
кручение

Нужна возможность создавать пользовательские наборы/collections.

Например:

"как в ДЗ"
"повышенная сложность"
"РК1"
"базовые балки"

Одна задача может находиться в нескольких наборах.

==================================================
14. ЭТАЛОННЫЙ ОТВЕТ ЗАДАЧИ
==================================================

В карточке Problem должны быть отдельные области:

Условие

Правильный ответ

Эталонные эпюры / изображения

Дополнительное решение / комментарий optional.

Правильный ответ не смешивать с условием.

Эталонные эпюры хранить через FileAsset.

Поддержать несколько изображений/PDF.

Эти данные предназначены преподавателю
и не должны автоматически попадать в student-facing ticket output.

==================================================
15. DRAG & DROP ФАЙЛОВ ВЕЗДЕ
==================================================

Пользователь хочет добавлять файлы
НЕ только через Windows file picker.

Реализовать reusable drag-and-drop component/zone
на основе существующего file import pipeline.

Использовать её минимум для:

- Attempt attachments;
- Homework definitions;
- Problems/control tasks;
- Seminar materials;
- Literature;
- Question message attachments;
- другие file-enabled формы.

Workflow:

перетащил файл из Explorer
-> drop zone подсветилась
-> отпустил
-> импорт через существующий FileAsset pipeline.

Поддержать multi-file drop.

File picker оставить как доступную альтернативу.

Не создавать отдельный механизм хранения.

==================================================
16. ГЕНЕРАТОР ВАРИАНТОВ / БИЛЕТОВ
==================================================

Добавить Ticket / Variant Generator.

Сценарий:

Группа АА
20 студентов.

Пользователь задаёт критерии:

Тип задач:
балки

Набор:
как в ДЗ

Количество задач в одном билете:
например 1, 2, 3...

Количество вариантов:
по количеству студентов группы
или вручную.

Система формирует набор индивидуальных вариантов.

Минимальные filter criteria:

- Course;
- tags;
- collection/set;
- archived=false.

Предусмотреть возможность комбинации критериев.

==================================================
17. ПРАВИЛА ГЕНЕРАЦИИ БИЛЕТОВ
==================================================

Generator должен быть deterministic/reviewable.

Не использовать AI.

Не использовать "умный подбор".

Нужно:

- получить eligible problem pool;
- проверить, что задач достаточно;
- сформировать requested variants;
- по возможности минимизировать повторение одинаковых комбинаций;
- не молча выдавать плохой результат при недостатке задач.

Если задач недостаточно:
показать понятное сообщение.

Позволить:

- regenerate;
- заменить конкретную задачу;
- сохранить сформированный набор вариантов.

==================================================
18. СОХРАНЁННЫЙ НАБОР БИЛЕТОВ
==================================================

Добавить сущность примерно:

TicketSet / ControlVariantSet

Связи:

CourseOffering
Assessment optional
Group
created_at
criteria snapshot

и:

Ticket / Variant

с ordered Problems.

Нужно сохранять snapshot состава.

Если Problem потом изменится,
состав старого билета не должен незаметно измениться.

Выбрать минимальную безопасную историческую стратегию:
snapshot/revision lock/reference snapshot.

Документировать.

==================================================
19. НАЗНАЧЕНИЕ БИЛЕТОВ СТУДЕНТАМ
==================================================

Для группы должна быть возможность:

20 студентов
-> 20 вариантов.

Поддержать:

- автоматическое назначение по текущему списку Enrollment;
- просмотр:
  Student -> Variant;
- ручную замену варианта;
- вариант без назначения конкретному Student.

Не делать рейтингов/адаптивного выбора задачи по способностям студента.

Все студенты подбираются по одинаковым критериям,
если преподаватель явно не задаёт иное.

==================================================
20. ПЛАН И ТЕКСТЫ СЕМИНАРОВ
==================================================

Добавить базу seminar materials.

Это не то же самое, что фактически состоявшийся Lesson.

Нужны reusable materials для подготовки преподавателя.

Предпочтительная модель:

SeminarMaterial / SeminarPlan

Минимально:

- Course;
- title;
- planned week optional;
- Topic links;
- plan text;
- full seminar text / notes;
- attachments;
- tags;
- metadata.

Пользователь в будущем хочет писать эти материалы на планшете.

Сейчас:
- только Windows/local editing;
- offline-first;
- никакой sync/mobile.

Но storage/model не должны мешать
будущему tablet client.

Текст хранить в переносимом формате
(plain text / Markdown или другой простой формат),
не как Qt-specific serialized rich-text object,
если нет убедительной причины.

==================================================
21. БАЗА ЛИТЕРАТУРЫ
==================================================

Добавить Literature Library.

Минимум:

LiteratureItem

- UUID;
- Course optional;
- title;
- author(s) optional;
- year optional;
- type;
- notes;
- tags;
- metadata.

Типы минимум:

- Учебник;
- Учебное пособие;
- Методическое пособие;
- Статья;
- Другое.

LiteratureItem может иметь один или несколько FileAsset.

Например:

Учебник.pdf
Приложение.pdf

Drag-and-drop поддержать.

Все данные остаются локальными.

==================================================
22. ЕДИНЫЙ РАЗДЕЛ МАТЕРИАЛОВ
==================================================

Не создавать хаотично 10 новых глобальных sidebar sections.

Продумать единый раздел:

Материалы / Библиотека

Внутри tabs/pages, например:

- Домашние задания
- Банк задач
- Семинары
- Литература

Если есть более понятная информационная архитектура —
использовать её и документировать.

Главная цель:
новые базы должны быть доступны,
но не перегружать основной sidebar.

==================================================
23. FAQ FOUNDATION
==================================================

Глобальный раздел Questions из sidebar убирается,
но QuestionCase domain остаётся.

В будущем пользователь хочет собирать
из вопросов и ответов FAQ для всех студентов.

В этой итерации:

НЕ делать AI FAQ generation.

Минимально предусмотреть архитектуру,
чтобы Teacher Message / QuestionCase можно было
позже вручную превратить в FAQ entry.

Допустимо реализовать простую сущность FAQEntry сейчас,
если это не раздувает scope:

- question;
- answer;
- Course optional;
- Topic links optional;
- source_question_case_id optional;
- published/active flag;
- metadata.

Но не строить student portal.

Если реализацию FAQ разумнее отложить,
зафиксировать готовый contract/ADR
без тяжёлой инфраструктуры.

==================================================
24. ВИЗУАЛЬНАЯ АНАЛИТИКА
==================================================

Текущая Phase 6 analytics должна сохраняться.

Добавить графики/диаграммы для:

- Student analytics;
- Group analytics;
- сроки/динамика сдачи;
- attendance;
- Attempts/results where useful.

Не заменять числа графиками полностью.

График — дополнительное представление тех же FACT-derived metrics.

Подходящие примеры:

Student:
- динамика выполнения по неделям;
- своевременность;
- посещаемость lectures/seminars;
- attempts over time.

Group:
- выполнение работ;
- распределение состояний Assessment;
- динамика сдач по учебным неделям;
- attendance по неделям.

Deadlines/weeks:
- planned week vs actual submission week;
- number of submissions per week;
- overdue counts.

Использовать Qt-native chart solution,
предпочтительно PySide6 QtCharts,
если она доступна в установленной версии.

Не добавлять web dashboard
или тяжёлый сторонний plotting stack без необходимости.

Не создавать педагогических выводов.

==================================================
25. ВОПРОСЫ ВНУТРИ ГРУППЫ/СТУДЕНТА
==================================================

QuestionCase остаётся ручным local-first workflow.

У группы можно добавить вкладку/подраздел:

Вопросы

с вопросами студентов этой группы.

У Student card уже остаётся:
Вопросы.

Не делать global primary navigation для Questions.

Можно предусмотреть небольшой indicator:
"3 вопроса ожидают ответа"
в Group header/Overview,
если это не перегружает UI.

==================================================
26. MIGRATION
==================================================

Эта итерация почти наверняка требует новой schema migration.

Создать:

0006_content_workflow

или несколько последовательных migrations,
если одна станет слишком большой.

НЕ изменять исторические:

0001–0005.

Новые таблицы/колонки должны иметь:

- FK;
- constraints;
- indexes;
- UUID;
- standard metadata;
- soft-delete policy там, где применимо.

Проверить:

v1 -> latest
v2 -> latest
v3 -> latest
v4 -> latest
v5 -> latest
fresh -> latest

На populated copy.

==================================================
27. EXISTING USER DATA
==================================================

Не уничтожить существующие данные.

Особенно:

- old Assessment exact dates;
- Attempts;
- analytics;
- FileAssets;
- QuestionCases;
- Lesson attendance.

Новые week fields должны быть nullable.

Старые записи должны открываться после migration.

==================================================
28. APPLICATION LAYER
==================================================

Добавить application services/queries для новых возможностей.

Не позволять UI работать напрямую с ORM.

Минимальные области:

AcademicWeek planning

Homework Library

Problem Bank

Problem Collections/Tags

Ticket Generator

Ticket Set assignment

Seminar Materials

Literature Library

Drag/drop imports должны вызывать существующий application file pipeline.

==================================================
29. TAG MODEL
==================================================

Не создавать отдельные несовместимые tag systems
для каждой новой библиотеки без причины.

Спроектировать простой reusable tagging contract.

Но не делать чрезмерно сложную universal metadata framework.

Нужно безопасно поддержать:

Problem tags:
балки / рамы / ...

Material tags.

Problem collections ("как в ДЗ") отличать
от обычных tags, если семантика действительно разная.

==================================================
30. SEARCH / FILTER
==================================================

Для новых библиотек добавить минимальный удобный search/filter.

Problem Bank:

- search text;
- tags;
- collection;
- Course.

Homework:

- Course;
- tags;
- search.

Seminar Materials:

- Course;
- week;
- Topic;
- search.

Literature:

- search;
- Course;
- type;
- tags.

Не добавлять FTS engine без необходимости.

==================================================
31. FILE PREVIEW REUSE
==================================================

Не строить новый preview.

Использовать Phase 4:

- image preview;
- PDF preview;
- default Windows app fallback;
- integrity;
- SHA-256;
- thumbnails.

В карточках Homework/Problem/Seminar/Literature
показывать attachments через общий reusable widget/component.

==================================================
32. WINDOWS UX
==================================================

Проверить:

- drag/drop;
- back navigation;
- breadcrumb;
- sidebar group dropdown;
- keyboard;
- 100/125/150 DPI;
- resize;
- long Russian labels;
- long FIO;
- long file names.

Все новые страницы должны жить в одном MainWindow.

==================================================
33. TESTS
==================================================

Все существующие 475 tests должны продолжать проходить.

Добавить tests минимум для:

NAVIGATION / UX:
1. internal navigation push;
2. Back returns previous page;
3. opening Student does not create new top-level window;
4. sidebar Groups expansion;
5. direct group navigation;
6. Questions absent from primary sidebar;
7. Add page;
8. ComboBox readable palette/theme;
9. date picker direct selection;
10. drag/drop file import.

ACADEMIC WEEK:
11. week validation;
12. odd -> numerator;
13. even -> denominator;
14. Assessment planned issue week;
15. Assessment planned due week;
16. old Assessment without weeks;
17. on-time by academic week;
18. overdue by academic week;
19. exact deadline fallback/priority.

LESSONS:
20. Seminar type;
21. Lecture type;
22. lecture attendance;
23. separate analytics;
24. combined analytics.

HOMEWORK LIBRARY:
25. create;
26. tags;
27. attachments;
28. Assessment -> homework definition;
29. archive;
30. drag/drop.

PROBLEM BANK:
31. Problem creation;
32. tags;
33. collections;
34. correct answer;
35. reference diagram attachments;
36. search/filter.

TICKET GENERATOR:
37. filter pool by tag;
38. filter by collection;
39. N variants for N students;
40. insufficient pool handling;
41. deterministic/reviewable generation;
42. regenerate;
43. replace one problem;
44. save TicketSet;
45. assign to Students;
46. historical snapshot stable after Problem edit.

SEMINAR MATERIALS:
47. plan;
48. text;
49. week;
50. Topic links;
51. files;
52. drag/drop.

LITERATURE:
53. create;
54. file attachment;
55. type;
56. tags;
57. filter;
58. drag/drop.

FAQ FOUNDATION:
59. contract or entity behaviour as implemented.

ANALYTICS CHARTS:
60. charts use existing analytics DTOs;
61. empty data safe;
62. N/A safe;
63. week series;
64. lecture/seminar series.

MIGRATION:
65. v5 -> latest;
66. v4 -> latest;
67. v1 -> latest;
68. fresh -> latest.

Добавить другие необходимые tests.

==================================================
34. PERFORMANCE
==================================================

Проверить Problem Bank минимум на synthetic:

1000 Problems
multiple tags/collections.

Фильтрация должна быть интерактивной.

Ticket generation для:

30 students
и разумного problem pool

не должна подвешивать UI.

Проверить analytics charts
на существующем synthetic dataset.

==================================================
35. PACKAGING
==================================================

Обновить PyInstaller build,
если появились новые Qt modules/resources.

Собрать packaged Studium.exe.

Проверить:

- QtCharts, если используется;
- migrations;
- file resources;
- QSS;
- drag/drop;
- PDF/image preview.

Packaged app должен оставаться portable как вся папка dist/Studium.

==================================================
36. MANUAL ACCEPTANCE DATASET
==================================================

Создать synthetic demo scenario:

Academic term
Course: Сопротивление материалов
Group: МТ5-31
20 students

Problem Bank:
- 20+ балки
- 20+ рамы
- collection "как в ДЗ"
- reference answers/diagrams

Homework library:
- ДЗ №1–5

Seminar materials:
- weeks 1–5

Literature:
- several synthetic entries

Lessons:
- seminars + lectures

Создать TicketSet:
20 students
tag "балки"
collection "как в ДЗ"

Использовать только synthetic placeholder content,
не реальные copyrighted textbooks.

==================================================
37. DOCUMENTATION
==================================================

Обновить:

README.md
AGENTS.md при необходимости
docs/architecture.md
docs/data-model.md
docs/ui-navigation.md
docs/analytics.md
docs/decisions.md
docs/roadmap.md
docs/todo.md
docs/done.md

Создать отдельный:

docs/iteration1-review.md

с:

- пользовательскими требованиями;
- что сделано;
- screenshots;
- UX flow;
- OPEN items;
- migration details.

==================================================
38. SCREENSHOTS
==================================================

Сделать screenshots:

1. новая главная навигация;
2. раскрытые группы sidebar;
3. internal Student page + Back;
4. Add page;
5. Homework Library;
6. Problem Bank;
7. Problem card with answer/epures;
8. Ticket generator criteria;
9. generated 20 variants;
10. Seminar Materials;
11. Literature;
12. drag/drop state;
13. week selector;
14. lecture attendance;
15. Student analytics charts;
16. Group analytics charts.

==================================================
39. НЕ ДЕЛАТЬ
==================================================

Не реализовывать:

- AI/agents;
- OCR;
- cloud;
- FastAPI;
- PostgreSQL;
- sync;
- tablet client;
- Android;
- automatic Telegram/email import;
- automatic FAQ generation;
- adaptive student difficulty;
- automatic pedagogical recommendations;
- student ranking;
- prediction.

==================================================
40. ЗАВЕРШЕНИЕ
==================================================

НЕ создавать final Phase 6.6 commit без разрешения пользователя.

В конце показать:

1. новую navigation architecture;
2. schema changes;
3. migrations;
4. новые domain entities;
5. новые application services;
6. Homework Library;
7. Problem Bank;
8. Ticket Generator;
9. Seminar Materials;
10. Literature Library;
11. AcademicWeek semantics;
12. lecture attendance;
13. analytics charts;
14. drag/drop architecture;
15. ComboBox/date picker fixes;
16. test count;
17. Ruff;
18. pytest;
19. migration results;
20. Problem Bank performance;
21. packaged exe path/size;
22. screenshots;
23. remaining OPEN;
24. blockers;
25. git status.

Отдельно перечислить:

A. что пользователь должен проверить вручную;
B. какие UI decisions остались спорными;
C. какие идеи намеренно отложены на Iteration 2.

Phase 7 НЕ начинать.
Iteration 2 НЕ начинать.
