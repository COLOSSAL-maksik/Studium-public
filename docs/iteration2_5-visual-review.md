# Iteration 2.5 — Visual polish / UI consolidation

> Документ относится к Studium как независимому локальному приложению.
> Bender — отдельный проект; будущая интеграция использует локальный JSON-RPC
> 2.0 over stdio. Прямые импорты Bender, API/client, облачный сервер и новые
> возможности этим переносом не реализованы. Описания прежних фаз сохраняют
> технические требования; их проверки и acceptance не подтверждены этим текстом.

Задание и проверка: 4 октября 2026. Источник: [iteration2_5-request.md](iteration2_5-request.md).
Ручная приёмка объединяет функциональность Iteration 2 и интерфейс Iteration 2.5.
Финальный commit Iteration 2.5 не создаётся.

## Граница и checkpoint

Завершённая Iteration 2 сохранена по явному разрешению пользователя в checkpoint
`[историческая ссылка опущена]` (`checkpoint: complete iteration 2 before visual polish`).
До checkpoint сверены состояние Git, отчёт Iteration 2 и последний лог 577 PASS:
изменений application code после этого прогона не было. Checkpoint не означает ручную приёмку.
Текущий HEAD остаётся на этом checkpoint; изменения Iteration 2.5 не закоммичены.

**NO NEW MIGRATION.** Domain, application, infrastructure, composition, dependency pins
и production schema не изменены. Сохраняется `0007_work_programs`; исторические
0001–0007 не редактировались. Формулы прогресса, история Attempt, результаты задач
и навыков, даты, транзакции и доступ к файлам используют существующие контракты.
Remote, Phase 7, AI/OCR, sync/server/live integrations не начаты.

## Visual direction и tokens

Linear Academic с умеренными Fluent-приёмами: спокойная оболочка, лёгкие границы,
ясная типографика и один приглушённый синий акцент. Отдельные семантические цвета
сопровождают текст/символ результата, поэтому цвет не является единственным признаком.
Нет внешних шрифтов, icon fonts, bitmap icons или новых зависимостей.
Оригинальные линейные иконки рисует Qt; disabled-состояние берёт цвет палитры.

| Token | Light | Dark |
|---|---|---|
| Фон приложения | `#f7f8fa` | `#1b1d23` |
| Sidebar | `#eef0f4` | `#202229` |
| Основная поверхность | `#ffffff` | `#242730` |
| Вторичная поверхность | `#f3f4f7` | `#2b2e38` |
| Основной текст | `#252935` | `#edf0f7` |
| Вторичный текст | `#646b7c` | `#a8afbf` |
| Граница | `#dce0e8` | `#3c414e` |
| Hover / selection | `#e8ebf1` / `#e8edfb` | `#333846` / `#353f5e` |
| Акцент | `#5268b5` | `#7f94df` |
| Успех / предупреждение / ошибка | `#2f7963` / `#986c21` / `#b04d53` | `#82c4ab` / `#d6b36f` / `#ea9399` |

Logical pixels: spacing **4/8/12/20/32**, control radius **5**, surface radius **8**.
Segoe UI: page **26**, section **17**, body/table **13**, caption **11**; metric **28**.
Палитры заданы явно; Dark не строится инверсией строк Light QSS.
Focus, hover, pressed, selected, disabled, read-only и primary action имеют общие стили.
QPalette покрывает native controls, QSS — поверхности, menus/popups/tooltips/tabs/scrollbars.
Сохранённые charts, calendars, icons и Home tiles обновляются при переключении темы.

## Оболочка и плотность

Sidebar шириной 180 logical px: Главная, Работа, Дисциплины, Библиотека, Добавить;
Настройки внизу. Иконки и активный пункт сохраняют один визуальный язык.
Учебный период находится в верхнем правом углу; Back и breadcrumb показывают
дисциплину, период, группу и текущий объект. Существующий navigation stack сохранён.

Home / Discipline / WorkProgram используют свободное пространство и смысловые секции.
Журнал сохраняет плотность: строки 34 px, компактные групповые заголовки, frozen ФИО,
горизонтальная прокрутка и исходная модель выбора. Hover и текущая строка помогают
связать ФИО с фактическими ячейками; прямоугольная сетка ослаблена.
Длинные формы и детали прокручиваются; редкие поля раскрываются по запросу.
Бизнес-значения скрытых полей и существующие Save/Cancel callbacks сохранены.

## Что изменилось на экранах

| Экран | Результат |
|---|---|
| Home | Три крупные кликабельные карточки, краткий контекст продолжения работы, компактный список групп, понятный empty state. |
| Discipline | Обзор предмета с секциями программ, материалов и знаний; быстрые переходы и счётчик программ. |
| WorkProgram | Summary и визуальная последовательность модулей с неделями; выбор модуля открывает существующую строку плана; PDF сохраняется. |
| Journal | Спокойные band headers, единая высота, ослабленная сетка, frozen ФИО и подсветка строки, семантические статусы. |
| Student × Work / Attempts | Сначала студент, работа, итог и новая попытка; затем история. Выбранная попытка, комментарий, файлы и результаты сгруппированы. Нижняя область прокручивается. |
| Homework content | Темы/навыки показаны тегами; части работы раскрываются; пустая таблица частей заменена объяснением; общие файлы остаются доступны. |
| RK checking | Видимые студент/работа/задача, текст условия, результат задачи и отдельные результаты навыков; баллы и максимум в «Дополнительно». |
| Analytics | Крупные factual metrics, единые chart backgrounds/axes, один акцент radial chart и ограниченная палитра line/series. Evidence и формулы сохранены. |
| Forms | Общий heading, логичные интервалы, primary Save, перенос длинных labels. Редкие поля периода/группы/работы/материала раскрываются. |
| Calendar | Понедельник первым, короткие дни, без номера недели/сетки, отдельный outline сегодняшнего дня, контрастные arrows, native month/year и keyboard. |
| Tags / pickers | Выбранные темы/навыки видны компактными тегами с удалением через существующий selection state; empty taxonomy объяснён. |
| Library | Банк задач стал списком title + tags с сохранёнными selection/filter/Enter. Редкие фильтры свёрнуты; текст материала сначала доступен для чтения. |
| Knowledge Base | Список слева, выбранная запись с вопросом/ответом/ссылками/числом источников справа; пустое состояние без лишнего modal. |

Исправлено реальное наложение панели результатов частей на заголовок Homework history:
не включённый в tabs дочерний widget теперь явно скрывается при отсутствии частей.
Это проверяется отдельным geometry/visibility regression. Список файлов в контексте
одной попытки не повторяет колонки даты/работы/попытки; metadata и действия сохранены.

## Изменённые UI-файлы

Все пути относительно `src/studium/presentation/desktop/`:

- Новые: `design.py`, `icons.py`, `visuals.py`, `calendar.py`, `chart_style.py`.
- Изменены: `theme.py`, `components.py`, `navigation.py`, `main_window.py`,
  `pages.py`, `programs.py`, `dialogs.py`, `files.py`, `learning.py`, `library.py`,
  `journal.py`, `widgets.py`, `analytics.py`, `charts.py`, `progress_charts.py`,
  `workflow_widgets.py`.

Packaging: `Studium.spec` использует неизменённые Python implementations locked
SQLAlchemy вместо optional Cython binaries (ADR-043); `.venv` и dependency pins прежние.
Новые QA: `tests/integration/test_visual_desktop.py`,
`scripts/preview_iteration2_5.py`, `scripts/smoke_iteration2_5_packaged.py` / `.ps1`.
Документация: README, AGENTS, roadmap/todo/done, ui-navigation, ADR-042/043 и этот отчёт.

## Проверки и screenshots

Финальный regression обычной `.venv`: **585 PASS / 333.84s**. Дополнительный полный
regression на SQLAlchemy Python backend, используемом в bundle: **585 PASS / 345.67s**.
Ruff format/check **PASS**, pip check **PASS**, `git diff --check` PASS.
Проверены 8 новых UI regressions: контраст обеих тем,
прозрачность icons, keyboard Home, сохранение advanced form values, отсутствие
перекрытия history/files и скрытие пустых results, Calendar keyboard/theme/arrow contrast,
выбор существующего модуля.

Source Qt captures: **33 PNG на DPR 1.0 + 6 на 1.25 + 6 на 1.5 = 45 PNG** в
`docs/screenshots/iteration2_5/dpi-100`, `dpi-125`, `dpi-150`.
Это Windows Qt platform с фактически проверенным DPR, а не ресайз одного bitmap.
Есть Light/Dark, Home, Discipline, Program/Modules, Journal/collapse, Homework,
RK, Library/materials, Knowledge, charts, Calendar, PDF, Attempts/files/results,
узкое и максимизированное окно. Resize проверяет реальные **960×620 / 1240×780**;
maximized capture — **2880×1779 logical px** на текущем экране при DPR 1.0.
`qa.json` каждого DPI сохраняет inventory PNG и геометрию последнего targeted capture;
`captured_this_run` отличает обновлённые кадры от полного inventory.
Сводный machine report содержит все 45 source PNG,
их physical dimensions, проверенный Windows DPR и геометрию крупных QA-прогонов.

Упаковка: `Studium.spec` сохраняет locked SQLAlchemy 2.1.1, staging копирует только
официальные `.py` без изменения кода; optional Cython binaries исключены. В начале
packaged QA frozen native `_processors_cy` блокировал import, включая `--help`.
Проверены совпадение pyd SHA256 и успешный source import; смена порядка Qt/SQLAlchemy
не помогла. Python implementation успешно выполняет production `--help` (exit 0).
Причина native блокировки не установлена; выбран явный packaging workaround ADR-043.
Попытка несanitized diagnostic build отдельно подтянула несовместимую ICU DLL из
PATH Codex; production build использует очищенный PATH и эту DLL не содержит.

**Production onedir и actual exe smoke завершены:**

| Проверка | Результат |
|---|---|
| Fresh / populated v6 upgrade / workflow / reopen | **PASS**, все **exit 0** |
| Populated Iteration 2 v7 | Все прежние rows и schema objects **не изменены** |
| SQLite | **77 user tables**, `integrity_check=ok`, FK violations **0** |
| GUI | Home, Discipline/Program/Modules, Journal, новая Homework Attempt, RK task/Skill, negative validation, charts, Library, PDF/image и native multi-file picker **PASS** |
| Theme / Calendar | Реальный Combo popup, Dark surface pixel assertion, Light restore; Calendar popup/grid/keyboard и отмена формы **PASS** |
| После reopen | Homework latest ACCEPTED, task CORRECT / Skill INCORRECT, прежняя history и новые attachments **PASS** |

Packaged machine report.
Добавлены **24 native PNG** в `screenshots/iteration2_5/packaged`: вместе с source
**69 PNG**, меньше 100. Итоговые native Light/Dark/Calendar/PDF/RK кадры осмотрены.
QA адаптирован к новым CheckBox roles checkable buttons и вложенным Calendar Table
providers; старые End/Home не переключали Combo, поэтому заменены настоящим popup
выбором и проверкой поверхности. Ошибки ранних QA selectors не объявлялись PASS.

Команды финального QA:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
# Повторный полный pytest с PYTHONPATH официального pure-SQLAlchemy staging: 585 PASS.
.\.venv\Scripts\python.exe -m ruff format --check .
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m pip check
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/build_windows.ps1
.\.venv\Scripts\python.exe scripts/smoke_iteration2_5_packaged.py
# preview_iteration2_5.py: Windows platform, --scale 1 / 1.25 / 1.5.
```

Оба полных pytest включают прежние performance guards: bank1000/generation30,
Journal30×17+6/progress и analytics30×20/1800 Attempts/600 ItemResults. Они PASS.

## Финальное состояние Git

**24 modified tracked paths + 12 untracked entries**, staged изменений нет.
Untracked screenshots directory содержит 69 PNG и QA JSON, а не один файл.
Из UI изменены 16 файлов и добавлены 5; полный список выше. Также изменён
`Studium.spec` для ADR-043. Финальный commit 2.5 **не создан**.
Diff domain/application/infrastructure/composition/dependency pins пустой;
новых миграций нет, 0001–0007 и исходные DOCX/assets сохранены.

## Remaining visual limitations и legacy widgets

- Modules, program works, taxonomy, часть Library и левый список Knowledge остаются
  стандартными Qt tables с общими стилями. Не каждый CRUD экран заменён индивидуальными cards.
- Основной текст материалов — read-only plain text с явным переходом в редактирование;
  Markdown/rich text renderer не добавлялся. Condition и originals не преобразуются.
- При узком окне длинные tabs используют стандартные стрелки Qt, таблицы — горизонтальную
  прокрутку. Раскрытые files/results могут требовать прокрутки нижней области history.
- Native Windows titlebar сохраняет оформление/accent ОС; цвет заголовка не задаётся
  общей QSS-палитрой приложения. Проверить на личных Windows appearance settings.
- Knowledge показывает ссылки и counts источников выбранной записи, без нового N+1 списка
  source previews. Существующий draft/source workflow сохранён.
- Radial chart сохраняет исходную числовую привязку секторов к ФИО и tooltip;
  без постоянных длинных ФИО вокруг круга. Прогнозы/рейтинги не добавлены.
- Native Explorer → exe OLE drag/drop остаётся шагом ручной приёмки. Установленный
  computer-use helper дважды не инициализировал trusted Node; CUA native surfaces отключены.
  Qt local-URL drop tests и native file picker — отдельные проверки.
- В Iteration 2 были ранние automation heap crashes `ntdll / 0xc0000374`; их причина
  не установлена. Повторный корректный smoke не доказывает устранение всех вариантов
  keyboard/assistive automation. Проверить РК вручную с обычным keyboard/mouse.
- Пользовательские данные не использовались. Автоматические проверки не являются
  преподавательской приёмкой функциональности или дизайна.

## Совместная ручная приёмка Iteration 2 + 2.5

- [ ] Home → Работа → группа → Журнал: контекст, Back, выбор студента, frozen ФИО,
  hover/focus, стрелки/Enter, поиск, прокрутка, свёрнутые модули.
- [ ] Discipline → WorkProgram → Modules: overview, неделя/числитель/знаменатель,
  выбор модуля, редактирование, PDF и сохранение выбора после Back.
- [ ] Homework → Attempts: статус, новая сдача/переделка, история прежних попыток,
  файлы, изображения/PDF, длинный комментарий и узкое окно.
- [ ] Control Work → tasks → skills: отдельно результат задачи и каждого навыка,
  пустой результат даёт понятную ошибку; новые факты сохраняются после reopen.
- [ ] Analytics → radial → line: выбранные module/as-of scope, подписи/tooltip,
  факт/деноминатор, будущие недели, Light/Dark, отсутствие визуального шума.
- [ ] Library: поиск/редкие filters, выбранный материал, текст/ответ, теги,
  редактирование и multi-file picker. Knowledge: вопрос/ответ/links/draft/sources.
- [ ] Light/Dark: переключение на открытых pages/dialogs/charts, dropdowns, menus,
  tooltip, focus, disabled/validation, выбранные tags и сохранение темы после reopen.
- [ ] Calendar: месяц/год, arrows, клик/Enter, PageUp/PageDown, ограничения дат,
  сегодняшняя/выбранная дата и обе темы на используемом Windows DPI.
- [ ] Explorer → exe: перетащить синтетические PNG/PDF, проверить drop feedback,
  импорт/preview/reopen. Повторить в узком окне и для нескольких файлов.
- [ ] Reopen packaged exe: сохранённый период/тема/факты/files, старые v7 данные,
  отсутствие новой migration. Копировать весь `dist/Studium`, включая `_internal`.
- [ ] После совместной приёмки отдельно разрешить финальный commit. До этого commit запрещён.
