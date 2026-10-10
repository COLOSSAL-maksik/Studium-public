# Iteration 3 — Acceptance fixes + UX consolidation

> Документ относится к Studium как независимому локальному приложению.
> Bender — отдельный проект; будущая интеграция использует локальный JSON-RPC
> 2.0 over stdio. Прямые импорты Bender, API/client, облачный сервер и новые
> возможности этим переносом не реализованы. Описания прежних фаз сохраняют
> технические требования; их проверки и acceptance не подтверждены этим текстом.

Дата: 4 октября 2026. Источник: [задание](iteration3-request.md).
Linear Academic, top row A [референса](design/studium-ui-reference.png), сохранён.

## Baseline и Git

Проверены status/diff/log, отчёты Iteration 2 / 2.5 / visual match и SHA-256
10 UI sources против сохранённого build proof. Working tree совпадал с
завершённым visual pass; после его 585 PASS application drift не обнаружен.
Без повторного baseline full suite создан прямо разрешённый safety checkpoint
`[историческая ссылка опущена]`, сообщение
`checkpoint: iteration 2.5 visual baseline before iteration 3`.
Current HEAD остаётся тем же. Iteration 3 находится в working tree; final commit
не создан, remote отсутствует. Ручная acceptance отдельно от технического PASS.
Итоговый Git status: **37 modified files + 35 untracked files** (11 untracked
entries в short status, включая каталог screenshots), всего 72 изменённых paths.
Полный список: git-status.txt.

## Изменения

- **Navigation/Home/sidebar:** Back по фактической истории, root переходы через
  sidebar, без Back на Home. Retained Group восстанавливает offering/tab после
  Group → Program → другая Group. Continue/recent объединены: одна заметная
  карточка с неделей/модулем и компактные кликабельные строки без отдельного Open.
  Четыре корня sidebar, один уровень shortcuts и локальное сохранение раскрытия.
  Глобальное Add убрано; period operations в Settings, остальные create в контексте.
- **Library:** семь разделов; Homework условия и HomeworkPack/общий PDF под одной
  вкладкой, файлы переиспользованы. Рубежный контроль содержит готовые TicketSets;
  банк содержит исходные задачи. Семинары/лекции разделены фильтром LessonType.
  Одно primary create, встроенные дополнительные фильтры вместо floating disclosure.
- **Problem Bank:** явный multi-select purpose отдельно от tags. Standalone
  поддержан; family хранит общее условие/classification, варианты — code, параметры,
  ответ/решение/схемы. Child editor не требует копии общего условия. Generation,
  saved sets и student assignment используют существующие алгоритм/снимки; skills
  и shared/variant files наследуются. Устаревший review после изменения family
  отклоняется атомарно. Выданная история после редактирования источника сохраняется.
- **Journal/forms:** ФИО, header и rows одного model/selection синхронизированы,
  overlay выше grouped header, без лишней рамки. Пустая структура Homework/RK
  сохраняется в header/hint без fake work columns. Редкий Group context перенесён
  в «⋯». ContentEditor/важные формы прокручивают body с Save/Cancel снаружи;
  полные названия применены в основных действиях и разделах.

### Аудит «Порядок»

| Форма | Вместо сырого поля |
|---|---|
| Topic / Skill | Append max+1; edit сохраняет прежнее значение; ↑/↓ в каталоге |
| ProgramModule | Новая позиция по start week; edit сохраняет; ↑/↓ в плане |
| ProgramWork | Append max+1; edit сохраняет; ↑/↓ в плане |
| AssessmentItem | Append max+1; edit сохраняет; существующие ↑/↓ |

Реальная перестановка использует транзакцию и revisions; порядок не скрыт
пустым неподтверждённым значением и не требует ввода технического числа.

## Миграция и область изменений

ADR-044 — единственное новое доменное решение. `0008_problem_variants`:
5 additive columns в `problems`, self FK, family index, unique variant code и
triggers; 77 user / 78 total tables. Existing rows/defaults, TicketSets,
assignments и FileAsset не переписываются. 0001–0007 неизменны; dependency и lock
изменений нет. Новых domain entities или параллельной HomeworkPack модели нет.
Изменены 1 domain, 3 application и 12 presentation Python files; 6 infrastructure
files, включая два новых migration files. Application additions обслуживают
purpose/family resolution и существующее presentation ordering/preferences.

## Проверки

Во время batches запускались relevant subsets: навигация/Qt, bank/family,
workflows, populated migration и bank1000 performance. После исправления
сценариев targeted PASS; failures в новых QA обнаруживали также constructor
CheckList и overlay header, исправленные до финального full suite.

| Проверка | Результат |
|---|---|
| Полный `.venv/Scripts/python -m pytest -q` | **605 PASS / 636.99s**, необходимый повтор после persistence fix |
| `.venv/Scripts/python -m ruff format --check .` | PASS, 196 files |
| `.venv/Scripts/python -m ruff check .` | PASS |
| `.venv/Scripts/python -m pip check` | PASS |
| Native source DPI 100/125/150% | PASS: по 38 geometry checks, обе темы |
| Размеры 960×620 / 1240×780 / maximized | Save доступен; body scroll; frozen rows/header совпадают |
| Fresh / empty v7 / populated v7 / double reopen | Targeted PASS; прежние rows/objects/bytes сохранены |
| Fresh PyInstaller onedir | PASS; exe **9 936 246 bytes**, `dist/Studium` **138 248 981 bytes** |
| Actual exe fresh / populated v7 upgrade / workflow / reopen | **PASS**, все четыре exit 0; DB rows/objects, files, TicketSets/assignments, integrity/FK |
| Current code внутри fresh exe | **22/22 source/SQL совпадают**, `build-proof.json` |

Первый full run: 604 PASS и один metadata comparison failure / 600.60s.
Устранены несогласованное имя family index, лишний metadata CHECK и inline FK
declaration; SQLite NO ACTION защищает parent без CASCADE и согласуется с
metadata/PRAGMA. Конкретный failing test + family/migration: **8 PASS / 3.92s**,
включая raw DB запрет удаления family с вариантами. После persistence fix
выполнен необходимый повтор полного suite: **605 PASS**; предыдущий run не назван PASS.

Fractional DPI округляет native client size до ±1 logical pixel; QA допускает
это округление и проверяет реальные bounds Save и viewport. Никакие app data
пользователя не использованы: синтетические временные roots, включая v7 copy.
Автоматическая проверка разрешений один раз остановилась из-за лимита usage;
после указания пользователя тот же запрос успешно выполнен, обхода не было.

нужна вся папка `dist/Studium`. Используется прежний SQLAlchemy Python backend
по ADR-043, версия/pins/system Python не менялись. Native UIA проверила Home/Back,
sidebar expansion/shortcuts, Journal horizontal scroll, семь Library разделов,
Homework packs, family с тремя схемами, saved RK, New Material/advanced scroll и
доступный Save, Light/Dark и actual restored Dark. После reopen проверены все
прежние synthetic facts и immutable file bytes. Qt UIA не экспортирует frozen
view/scrollbar отдельно: horizontal scroll проверен смещением main grid cells;
точное совпадение overlay/header/rows — native Qt geometry на трёх DPI и PNG.
Диагностический source UIA run хранится отдельно от actual packaged proof.
В build log остались штатные optional hidden-import warnings tzdata/pysqlite2/
MySQLdb; native smoke PASS.

## Acceptance set

`docs/screenshots/iteration3`: **16 PNG**, без редактирования снимков.
Home; Work/Library expanded; Journal start/scrolled; Homework; bank; family;
saved controls; seminars; lectures; New Material normal/advanced; dark journal;
dark bank; narrow journal. `geometry-100/125/150.json` содержат машинные проверки.
`packaged-qa.json`, `build-proof.json`, `source-proof.json` и `git-status.txt`
содержат результаты actual exe, code/SQL comparison и окончательную область diff.
QA-family содержит три варианта с разными синтетическими схемами; реальные
схемы/материалы пользователь вводит самостоятельно.

## Ограничения и deferred

- TicketSet остаётся scoped на CourseOffering; создание набора требует выбора
  группы. Новый глобальный шаблон комплекта не вводился.
- Purpose старых задач пустой: смысл исторических tags автоматически не угадывается.
- Алгоритм генератора сохранён: специальное правило «не больше одного варианта
  одного family в одном билете» не добавлено; это отдельное будущее требование.
- Небольшое окно показывает длинные tabs через штатные Qt overflow arrows и
  прямые sidebar shortcuts. Полные длинные ФИО можно прочитать через tooltip/card.
- Reopen сохраняет theme, recent context и sidebar expansion; route history
  текущего процесса не записывается в БД.
- Native QA дополняет тесты; субъективная visual/keyboard acceptance, Explorer
  OLE drag/drop и workflow с реальными преподавательскими материалами — вручную.
- AI/OCR/cloud/server/sync/mobile/student portal/email/Telegram/mastery/ranking/
  predictions/новый export/backup/semester cloning не начаты. Phase 7 deferred.

## Ручная приёмка

- [ ] Home: нет Back; одно Continue/recent; карточка/строки открывают Journal;
      Back возвращает Home, Work→Group→Back возвращает список.
- [ ] Sidebar: четыре корня, один уровень, recent groups/discipline и семь
      Library shortcuts; expanded state после reopen.
- [ ] Group: overflow вместо Context; frozen ФИО при горизонтальной и вертикальной
      прокрутке; modules/collapse и пустые Homework/RK headers в Light/Dark.
- [ ] Library: все семь разделов, Homework packs/PDF без дубликатов, один Create;
      отдельные raw bank и готовые controls; filters/search/purposes.
- [ ] Family: shared condition, 2–3 разных схемы, параметры/ответы; generate→review
      →save→open→assign; прежние выданные snapshots и files остаются прежними.
- [ ] Forms: 960×620, 1240×780, maximized, DPI 125/150%; «Дополнительно» и scroll;
      Save/Cancel, keyboard focus, internal ordering/↑↓.
- [ ] Reopen: theme/context/expansion и данные ожидаемы; реальные материалы и
      Explorer→exe drag/drop. После acceptance — отдельное разрешение на commit.
