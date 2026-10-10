# Phase 6.5 — итоговый UX и Windows build review

> Документ относится к Studium как независимому локальному приложению.
> Bender — отдельный проект; будущая интеграция использует локальный JSON-RPC
> 2.0 over stdio. Прямые импорты Bender, API/client, облачный сервер и новые
> возможности этим переносом не реализованы. Описания прежних фаз сохраняют
> технические требования; их проверки и acceptance не подтверждены этим текстом.

**3 октября 2026.** Реализация готова к пользовательской приёмке. HEAD остаётся `[историческая ссылка опущена]` (Phase 6); final Phase 6.5 commit не создавался. Phase 7 не начата, remote отсутствует. Domain и database schema сохранены: latest `0005_analytics_foundation`, 31 user tables, migration 0006 нет. Исходные документы/схемы и исторические миграции не изменены.

## Навигация и основные изменения

- **Обзор / Группы / Вопросы**, нижняя кнопка **Настройки**. Пустая база начинает с периода → дисциплины → группы.
- **Группа: Журнал / Студенты / Работы / Занятия / Аналитика**. Один header группы/дисциплины/периода. Выбранный контекст сохраняется между разделами в сессии.
- **Карточка: Обзор / Работы / Прогресс / Файлы / Вопросы**. Крупный details dialog, характеристика, existing work/attendance/questions summary и последние фактические события.
- Журнал открывается первым. ФИО закреплено, колонку можно расширять; статус различается символом/подписью/tooltip и цветовым accent. Enter/double-click → compact quick Attempt; история — через меню ячейки. Новая запись сохраняет прежние Attempts.
- Студенты: одна кнопка добавления с меню новый/существующий, поиск; context menu открыть/изменить/завершить/архивировать с подтверждением.
- Занятия показывают темы и attendance counts; выбранные Ctrl/Shift строки сохраняются одним atomic batch с прежними комментариями и revision conflict rollback.
- Общий QuestionCase открывается из глобального списка, Student и Assessment. Waiting заметен спокойным amber accent и текстом.
- Файлы сохраняют прежний FileAsset pipeline/context/integrity. Lists/thumbnail/hash/decode и Message attachments читаются в фоне; загрузка карточки lazy, stale results игнорируются.
- Компактные group/student indicators и отдельные evidence counts используют Phase 6 DTO/формулы. Новых рейтингов, mastery, прогнозов нет.
- QSS, размеры controls, spacing и plain-text hints централизованы. Стандартные PySide6 widgets и Qt shortcuts; стороннего UI framework нет.

Клавиатура: стрелки — выбор; Enter — открыть/quick Attempt, Save в quick form; Esc — cancel/close; Ctrl+F — поиск активного раздела; Tab/Shift+Tab — поля; Ctrl/Shift — attendance selection. Подробности — [карта экранов](ui-navigation.md).

## Presentation/application структура

```text
src/studium/presentation/desktop/
  main_window.py      sidebar / onboarding / active period
  pages.py            group workspace / journal / students / assessments
  dialogs.py          existing forms / Student details / history
  theme.py            NEW: common QSS / dimensions / screen sizing
  widgets.py          NEW: Qt table Enter / frozen column / scoped Ctrl+F
  quick_attempt.py    NEW: compact form over existing Attempt validation
  background.py       NEW: QRunnable / queued delivery / owner lifetime
  learning.py         lessons / selected attendance batch
  communication.py    shared QuestionCase / search / waiting / attachments
  files.py            lazy file lists / preview / worker guards
  analytics.py        existing metrics / compact highlights / evidence
  components.py, models.py, messages.py
```

Существующие файлы сохранены, разделение ограничено четырьмя общими компонентами. Application добавляет `record_attempt`, `ActivityEntry`, `lesson_list`, `mark_attendance_many` и bulk reads для attendance/case context filters. UI не получает ORM Session/models. Analytics formula modules, domain и persistence schema не изменены. См. ADR-033/034 и [архитектуру](architecture.md).

## Частый сценарий A: количество действий

Предположения: журнал уже открыт; выбрать результат требуется; дата по умолчанию подходит; комментарий/Grade не нужны. Double-click считается одним действием, открытие combo и выбор — двумя.

| Путь | Действия | Физические клики |
|---|---:|---:|
| Раньше: ячейка → history → новая попытка → combo → результат → save → закрыть history | 6 | 7 |
| Теперь: ячейка → quick → combo → результат → save | 4 | 5 |
| С исходного Обзора, до сохранения: прежний / новый путь | 9 / 6 | 11 / 8 |

Последний путь включает выбор Групп и double-click группы; прежде также переключалась вкладка матрицы. Удалены действия открытия новой попытки из history и закрытия history; default Journal удаляет переключение вкладки. Это подсчёт последовательности, не измерение пользовательского времени.

## Synthetic scenario и проверки

`scripts/phase65_scenario.py`: 1 term, 1 course, 2 groups × 20 students, для каждого CourseOffering 8 homework + 2 controls, всего 8 lessons, 400 Attempts, 320 ItemResults, 160 attendance facts, 12 cases / 18 messages, PNG attachments у Attempt/Message, Topic/Skill links. Все facts синтетические, application data roots временные. Long-name case включает длинные ФИО, Course и Control title.

| Проверка | Результат |
|---|---|
| Чистый baseline `ruff format/check`, `pytest` | PASS; 455 tests / 83.38 s |
| Финальные `python -m ruff format --check .`, `python -m ruff check .` | PASS; 134 files / All checks passed |
| Финальный `python -m pytest -q` | **475 passed in 88.60 s**, exit 0 |
| Новые component tests | 20; onboarding, workspace, four quick results/number/history/cancel/validation, keyboard/frozen column, card/lazy files, shared assessment questions, archive confirm, attendance batch/conflicts/query count, worker responsiveness/stale guards |
| `python scripts/smoke_desktop.py` | Actual native `python -m studium`, visible Windows window, first migration v5 / 31 tables, FK, exit 0 |
| `smoke_analytics.py`, `smoke_communication.py`, `smoke_files.py` | Native source workflow + reopen PASS; временный LOCALAPPDATA |
| Group open, dataset 2 × 20 | 16 SELECT / 0.041 s native100 |
| Group analytics, same dataset | 22 SELECT / 0.0931 s native100 |
| Прежний analytics performance regression 30 × 20 | 1800 Attempts / 600 ItemResults / 10 Lessons / 30 Cases; 22 SELECT / 0.098 s PASS |
| Git diff/PE/dependencies | diff --check PASS; PE subsystem 2 (GUI); pip check PASS |

Сохранены все прежние 455 проверок; ожидаемые indices обновлены в UI tests/helpers. Production tests включают fresh/reopen и populated migration copies предыдущих версий. Performance measurements — локальные синтетические результаты, без универсального SLA. Analytics synchronous, lazy; существующий показатель около 0.1 s не ухудшен. File IO вынесено из GUI; SELECT count не растёт по каждому Lesson/Student attendance row.

## DPI / resize / visual QA

Native platform **windows**, фактический DPR явно проверен: **1.0 / 1.25 / 1.5**. Каждая конфигурация прошла размеры **960 × 620 / 1240 × 780 / 1600 × 900 logical px**, viewport журнала не менее 704 × 194 logical px. Frozen selection/scroll и long-name case проверены. QSS/fonts/layouts визуально просмотрены; слишком длинный header Assessment имеет tooltip и горизонтальное прокручивание, ФИО расширяется мышью.

На рабочем мониторе Windows 200%, поэтому `--native-base-scale 2` компенсирует native DPR; settings Windows не менялись. Использованы [Qt test scale controls](https://doc.qt.io/qtforpython-6/overviews/qtdoc-highdpi.html). При случайном DPR 3.0 отдельно обнаружено ограничение доступной высоты Windows; это не выдано за проверку 150%, прогоны повторены с правильным фактическим DPR. Проверка перемещения между разными физическими мониторами и изменение Windows settings при уже открытом приложении не проводились.

Native JSON: 100%, 125%, 150%. Для воспроизведения: `QT_QPA_PLATFORM=windows`, `python scripts/preview_phase65.py --native-base-scale 2 --scale 1.25 --output tmp/phase65-native125` на мониторе 200%; для другого native DPR заменить 2. Offscreen screenshots: `python scripts/preview_phase65.py --output docs/screenshots`.

## Windows bundle и actual exe smoke


Actual packaged process с временным **LOCALAPPDATA вне checkout**, без доступа к production profile:

1. Первый запуск создаёт `Studium/studium.sqlite`, применяет v5, показывает onboarding; FK check пустой.
2. Через GUI exe созданы term/course/group/Student/Assessment. В журнале Enter открывает quick Attempt, сохранён ACCEPTED; history и Student overview показывают одну попытку и зачёт.
3. Через native picker exe импортирован PNG; preview показывает image и Student/Assessment/Attempt/date context. Создан QuestionCase из карточки, сохранён исходный вопрос и ответ преподавателя; Progress и Group analytics открываются.
4. Через GUI создан Lesson, выбран студент и массово сохранён PRESENT attendance.
5. Окончательная пересобранная версия повторно открыла эти facts. PDF импортирован через GUI; QtPDF preview загрузился. Student Files содержит оба вложения, глобальные Questions показывают case и «Ответ дан».
6. Штатное закрытие **exit 0**, repeat reopen/PDF/files/questions проверка PASS. DB facts: 1 term/course/group/student/assessment/work/attempt/lesson/attendance/case, 2 files/attachments, 2 messages. FK check и SHA-256 проверены. В bundle нет пользовательской БД/originals/preferences.

GUI smoke использовал внешнюю Windows UI Automation только для собственных процессов. Test hooks не включены в production exe. Первоначальная ошибка ICU из чужого PATH исправлена очищением build PATH; final exe запускался с PATH Windows/System32, без source Python/Qt paths.

## Screenshots

| Экран | Снимок |
|---|---|
| Первый запуск | [first run](screenshots/phase65-first-run.png) |
| Group / Journal | [journal](screenshots/phase65-journal.png) |
| Students | [students](screenshots/phase65-students.png) |
| Student card | [card](screenshots/phase65-student-card.png) |
| Quick Attempt | [quick](screenshots/phase65-quick-attempt.png) |
| Lesson / attendance | [lesson](screenshots/phase65-lesson.png) |
| Global Questions | [questions](screenshots/phase65-questions.png) |
| Student Questions | [student questions](screenshots/phase65-student-questions.png) |
| Files / Preview | [files](screenshots/phase65-files.png), [preview](screenshots/phase65-file-preview.png) |
| Student Progress | [progress](screenshots/phase65-student-progress.png) |
| Group Analytics | [analytics](screenshots/phase65-group-analytics.png) |
| Long names / horizontal scroll | [long names](screenshots/phase65-long-names.png) |

Все 13 screenshots — синтетические. Исторические snapshots Phase 2–6 сохранены.

## Ручная приёмка и границы

Блокеров реализации нет. Требуется ручная UX-приёмка преподавателем:

- Удобно ли открывать группу сразу в Журнале; достаточно ли сохранения контекста в сессии.
- Подходит ли стартовая ширина ФИО и размеры Assessment колонок для реальных названий.
- Удобны ли четыре quick результата, default дата и раскрытие score/Grade; нужна ли другая исходная focus позиция.
- Подходят ли крупная Student card и расположение последних событий/характеристики.
- Понятны ли selected-row attendance, глобальное архивирование студента и спокойный Waiting accent.
- Проверить на своём мониторе клавиатурный Tab order и читаемость, особенно PDF/long-name cases.

Объективные DPI/component проверки не заменяют эту приёмку. Новые backend/sync/mobile/AI/live adapters/schema/формулы не реализованы. Final commit/stage/push не выполнялись; build/dist/tmp/.venv игнорируются. Изменения только в рабочем дереве, готовы к review.
