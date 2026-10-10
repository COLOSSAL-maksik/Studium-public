# STRICT VISUAL MATCH PASS — 2026-10-04

> Документ относится к Studium как независимому локальному приложению.
> Bender — отдельный проект; будущая интеграция использует локальный JSON-RPC
> 2.0 over stdio. Прямые импорты Bender, API/client, облачный сервер и новые
> возможности этим переносом не реализованы. Описания прежних фаз сохраняют
> технические требования; их проверки и acceptance не подтверждены этим текстом.

Источник: [задание](visual_match_pass-request.md), [authoritative PNG](design/studium-ui-reference.png). За основу взята строка **A — Linear Academic**: спокойные холодные поверхности, синий выбор/акцент, мягкие границы, карточки с цветными значками. Baseline — завершённая техническая Iteration 2.5. Финальный commit не создавался.

## Результат и граница проверки

**Финальная техническая верификация завершена:** 585 tests PASS, Ruff format/check и pip check PASS, свежий PyInstaller onedir и actual exe smoke PASS. Прежний блокер автоматической проверки разрешений устранён; результаты ниже получены заново для текущего visual match pass. При продолжении новые изменения дизайна не добавлялись: исправлены только два замечания Ruff к импортам и расширен существующий smoke harness. Ручная визуальная приёмка остаётся отдельным шагом, финальный commit не создавался.

## Изменено

- Shell: sidebar **232 px**, page padding **32 px**, одна строка breadcrumb/периода; «Добавить» и «Настройки» внизу, мягкая selected pill с синим левым акцентом.
- Home: три крупных tiles высотой от **196 px**, pastel icon badges, текущие счётчики групп/дисциплин. Продолжение и недавние группы расположены рядом; прежняя модель recent offerings отображается компактным двухстрочным списком.
- Discipline: заголовок/metadata и сетка карточек существующих разделов. WorkProgram: лёгкие строки модулей с левым цветовым акцентом и карточки существующих quick links. Маршруты и данные сохранены.
- Journal: закреплённое ФИО **236 px**, attendance **38 px**, work **66 px**, строки **32 px**, header bands **70 px**. Почти два модуля помещаются при 1240×780. Полные имена доступны в tooltip; planned cells, collapse и фильтры сохраняются.
- Общий язык: heading **28 px**, section **19 px**, body **13 px**, caption **12 px**; surface radius **11 px**, control radius **8 px**, мягкие 1 px borders, выбранные вкладки и календарь/ComboBox используют общую палитру. Dark — несколько серо-синих слоёв, цветные badges и читаемые акценты.

UI delta этого шага (10 файлов): `design.py`, `theme.py`, `icons.py`, `visuals.py`, `navigation.py`, `main_window.py`, `components.py`, `programs.py`, `pages.py`, `journal.py` в `src/studium/presentation/desktop/`. Native smoke проверил footer «Добавить»/«Настройки», текущие Home cards и Discipline/WorkProgram markers. Harness принимает отдельный `--output`; сохранены прежние снимки Iteration 2.5. Исправлен повторный Enter при возвращении в уже открытый журнал: сценарий теперь проверяет наличие вкладки перед открытием группы. Изменения приложения для этого не потребовались.

**NO NEW MIGRATION.** Domain, application, infrastructure, composition, schema, business rules, dependency files и `Studium.spec` этим шагом не изменялись. Сверка с `tmp/visual-match-baseline.json`: **86 защищённых файлов unchanged**, все **18 migration files unchanged**, latest `0007_work_programs`; оба lock-файла совпадают с HEAD. В новой distribution также проверены точные bytes всех 18 migration files. Исходный PNG сохранён. Baseline integrity.

## Проверено

Команда: `.venv/Scripts/python scripts/preview_iteration2_5.py --output docs/screenshots/visual_match_pass --only 01-home,01b-home-dark,02-discipline,03-program,05-journal,13-dark-journal,06-group-radial,15-attempt-dialog,16a-homework-history,14b-light-calendar,14-dark-calendar,18-library,09-homework-structure,11-problem-bank,12-knowledge-bank,19-narrow-journal,21-narrow-history-files`.

- **Exit 0**, Windows Qt platform, DPR **1.0**, временный application data root и только синтетические данные.
- **17 PNG** в [screenshots/visual_match_pass/dpi-100](screenshots/visual_match_pass/dpi-100); сценарный отчёт qa.json.
- Resize assertions: **960×620** и **1240×780** совпали с фактическими размерами; source minimum-size hints не превышали requested geometry.
- Визуально просмотрены Home Light/Dark, Discipline, Journal, WorkProgram, Analytics, Attempts, Calendar, Library и narrow Journal/history. Больше всего приблизились shell/Home и группировка журнала.
- Локальный `ruff format` только 10 изменённых UI-файлов: **4 reformatted, 6 unchanged**. Это форматирование, не полная Ruff-проверка.

Финальные команды через локальную `.venv/Scripts/python`:

| Проверка | Результат |
|---|---|
| `-m pytest -q` | **585 passed in 350.22s**, exit 0 |
| `-m ruff format --check .` | **188 files already formatted**, exit 0 |
| `-m ruff check .` | **All checks passed**, exit 0 после исправления unused import/import order |
| `-m pip check` | **No broken requirements found**, exit 0 |
| `powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/build_windows.ps1` | PyInstaller **6.22.3**, Python **3.12.10**, `--clean --noconfirm`, onedir **PASS** |
| `scripts/smoke_iteration2_5_packaged.py --output docs/screenshots/visual_match_pass` | **fresh / migration / workflow / reopen — все exit 0** |

Actual exe проверен на временных профилях: Home, Discipline, WorkProgram overview/modules, Journal в обеих темах; footer navigation; переключение Light↔Dark и восстановление сохранённой Dark после закрытия. Дополнительно Calendar, PDF/image, multi-file picker, Homework attempt, RK task/skill validation и charts. Все прежние populated v7 rows/schema objects unchanged; **v7 / 77 user tables + alembic_version**, integrity/FK PASS. Historical v6 → v7 сохраняет прежние данные/файлы. Реальные пользовательские данные не использовались.

**Последний UI подтверждён внутри exe:** code objects всех **10 UI-модулей** из встроенного PYZ совпадают с компиляцией текущих исходников (включая constants и nested code; исключён только filename). Это проверка содержимого новой exe, дополненная native UIA assertions и визуальным просмотром. Build UI proof, checks, packaged QA.

Всего **55 PNG**: **17 source** + **38 actual exe** в [packaged](screenshots/visual_match_pass/packaged). Новые native Home Light/Dark, WorkProgram и dark Journal просмотрены; основные композиции соответствуют source screenshots. PrintWindow captures включают системный Windows titlebar и невидимые resize bounds, которые могут отображаться чёрными полосами по краям PNG.

## Что ещё отличается от PNG

- Это collage трёх концепций и разных экранов: выбран единый язык A, без переключения на тёплый стиль C. Совпадение не пиксельное.
- Home tiles шире, нижние карточки выше; нет персонального имени, фиктивных уведомлений или профиля. Глобальная навигация остаётся на всех экранах.
- Discipline overview показывает существующие разделы карточками; официальный PDF и подробный план остаются в WorkProgram, без переноса данных или новых workflows. Quick links программы частично требуют прокрутки.
- Attendance отображает реальные числовые факты `1/2`, `2/2` и символы; не заменена декоративными кружками. Длинные ФИО/заголовки могут обрезаться, предусмотрены tooltip/scroll. Пропорции при 960 px требуют ручной оценки.
- Analytics сохраняет существующие фактические графики; декоративные KPI/donut/rainbow из референса не добавлены. Library/Knowledge остаются списками/таблицами с общей стилизацией.
- Стандартные Qt controls остаются под QSS: spin/check/radio indicators, tab overflow, table corner; titlebar/native file picker используют Windows chrome. Небольшие формы, включая добавление попытки, пока сохраняют исходную form geometry и заметный вертикальный воздух. Мягкая тень из PNG не воспроизводилась отдельными графическими эффектами.

## Git/build и следующий шаг

HEAD: `[историческая ссылка опущена]` (main); commit/remote не создавались. Рабочее дерево содержит прежние незакоммиченные Iteration 2.5 changes плюс этот delta, документы и screenshots. Итоговый статус: **24 modified tracked / 16 untracked entries**, staging пуст. Полный git status. Build artifacts и временные application roots игнорируются.


`git diff --check` PASS. Следующий отдельный шаг — ручная оценка визуальной близости A, DPI 125/150%, keyboard focus/Enter/Space, footer navigation, frozen names и горизонтального scroll, длинных labels, native calendar/ComboBox popups в обеих темах и Explorer drag/drop. Полного нового DPI screenshot pass не было: текущие source/native снимки на DPR 1.0; прежние Iteration 2.5 DPI результаты не засчитываются новым визуальным размерам. После ручной приёмки требуется отдельное разрешение на final commit.
