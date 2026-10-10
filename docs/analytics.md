# Аналитика Phase 6: контракт фактов и расчётов

> Документ относится к Studium как независимому локальному приложению.
> Bender — отдельный проект; будущая интеграция использует локальный JSON-RPC
> 2.0 over stdio. Прямые импорты Bender, API/client, облачный сервер и новые
> возможности этим переносом не реализованы. Описания прежних фаз сохраняют
> технические требования; их проверки и acceptance не подтверждены этим текстом.

## Phase 6.6 — недели и типы занятий

Legacy exact-date formulas ниже сохраняются. ADR-037: due_at имеет приоритет
над planned_due_week. Без exact deadline первое содержательное предъявление
до конца due week вовремя; позже поздно; без предъявления overdue со следующей
недели. Calendar weeks — семь дней от starts_on в сохранённом offset периода.
planned_issue_week дополнительно исключает будущие плановые работы.

Прежняя комбинированная AttendanceSummary сохраняется. WorkflowAnalytics
содержит два summaries SEMINAR/LECTURE и WeekFacts: все Attempts, первые
сдачи distinct Work, ACCEPTED Attempts и Assessment с due week. ACCEPTED
Attempts — события, а не текущие зачтённые работы. QtCharts — дополнение к
числам/N/A, без ratings/mastery/выводов. UNKNOWN/EXCUSED/unmarked не становятся
нулём процента. Один дополнительный bulk SELECT AcademicTerm сохраняет
отсутствие Students×Assessments N+1. Charts читаются при открытии вкладки.


Основание: отдельное задание Phase 6 от 2 октября 2026, ТЗ §§4.6/6.3/13, ADR-030–ADR-032. Этот документ определяет локальную аналитику без AI, прогнозов, рейтинга и модели освоения. Точные результаты проверок находятся в [done.md](done.md).

## Факты, показатели и интерпретации

**Факты:** Assessment/AssessmentItem и явные Topic/Skill links, Attempt/Grade, AttemptItemResult, Lesson/LessonTopic/Attendance, QuestionCase/Message/context, сроки и исходные даты. Они сохраняют UUID и историю. AttemptItemResult относится к конкретной Attempt; новая переделка имеет собственные результаты частей.

**Показатели:** число и доля выполненных работ, сдача с первого раза, число попыток, своевременность, нормированный балл, посещаемость, число вопросов и время ответа. Application вычисляет их при чтении. Таблиц с completion_rate, attendance_rate, progress_percentage или mastery нет; cache не требуется.

**Педагогические интерпретации:** «плохо знает», «сильная сторона», «риск неусвоения», «провалит экзамен», общий «уровень знаний» не выводятся. Вопрос — факт активности и контекста; посещение — факт присутствия. Ни один из них не превращается в отрицательный балл либо доказательство владения навыком.

## Результаты частей

AttemptItemResult: EntityMetadata (UUID, created_at/updated_at UTC, revision, deleted_at), attempt_id, assessment_item_id, nullable outcome/score/max_score/teacher_comment. ItemOutcome: CORRECT («Верно»), PARTIAL («Частично»), INCORRECT («Неверно»), NOT_EVALUATED («Не оценивалось»).

Допускаются outcome only, score only, outcome + score. Ни outcome, ни score — ошибка; один комментарий/максимум не является результатом. Maximum может сохранять контекст категориального результата и без score. Score finite >= 0, maximum finite > 0, score <= maximum при наличии обоих. Score без maximum сохраняется как факт, но не участвует в нормированном среднем. NOT_EVALUATED — явный исходный факт отсутствия оценки, без автоматического нулевого score.

Item принадлежит той же Assessment, что Attempt → StudentWork. Одна активная запись на пару Attempt/Item. Фактические поля immutable. Явное архивирование ошибочной записи сохраняет tombstone; после него разрешён новый UUID для корректного результата. Историю архивированных результатов можно прочитать отдельно. Новая учебная переделка всегда создаёт новую Attempt.

## Основные формулы

Групповой/Assessment cohort — уникальные активные Student с неархивированным Enrollment, чей интервал `[enrolled_at, ended_at)` содержит cutoff. Работы — неархивированные Assessment данного offering с issued_at <= cutoff; открытие StudentWork не считается началом. Прямой Student summary сохраняет показатели бывшего участника, но не назначает работы студенту вне offering или до первого известного enrolled_at. Переписка без membership всё равно остаётся отдельным фактом. Это текущий состав и область матрицы, без выдуманного исторического журнала индивидуальных назначений.

| Показатель | Правило |
|---|---|
| assessments_total | Число работ в выбранной области |
| assessments_started | Работа имеет хотя бы одну активную Attempt, кроме COMMENT_ONLY |
| assessments_completed / passed_count | StudentWorkProgress.status == ACCEPTED, текущая исходная domain projection |
| completion_rate | completed / total; total=0 → None |
| attempts_total | Все активные Attempt, включая COMMENT_ONLY и REJECTED |
| average_attempts_per_started_work | Число всех активных Attempt только начатых работ / started; started=0 → None |
| first_pass_count | Первая содержательная Attempt по attempt_no имеет ACCEPTED |
| first_pass_rate | first_pass_count / started; открытая первая сдача остаётся в denominator |
| on_time_count / late_count | Первое по occurred_at содержательное предъявление <= / > текущего due_at |
| overdue_count | Нет содержательного предъявления и due_at < cutoff |
| on_time_rate | on_time_count / (on_time_count + late_count); нет наблюдаемых сдач со сроком → None |
| normalized score | final_score / max_score той Attempt, которая дала текущий score; оба известны, snapshot maximum положителен |
| average normalized score | Среднее доступных normalized score, по одному на StudentWork; без scored works → None |
| attendance_rate | (PRESENT + LATE) / (PRESENT + LATE + ABSENT); пустой denominator → None |
| open_questions | Неархивированные QuestionCase без closed_at |
| questions_waiting_for_teacher | Existing derived state WAITING |

Содержательные Attempt: PRESENTED, NEEDS_REVISION, ACCEPTED, SCORED, REJECTED. REJECTED остаётся нейтральным для domain status/score, но записанный отказ не должен исчезать из первой сдачи и давать ложное «с первого раза». COMMENT_ONLY не создаёт предъявление. Attempts_total не изменяет прежний StudentWorkProgress.attempt_count.

Group aggregates используют pooled counts: sum first_pass / sum started, sum attempts начатых работ / sum started, sum timely / sum submitted with deadline. Average completion — среднее доступных student completion_rate; distribution показывает число студентов с X выполненными работами. Порядка «лучше/хуже» нет. Attendance складывается по известным фактам, не усредняется как ненаблюдаемый ноль.

Assessment analytics: assigned_students — размер cohort; started/not_started — наличие предъявления; passed — ACCEPTED; revision_required — REVISION_REQUIRED; in_progress — остальные начатые. Mean/median normalized score используют по одному текущему score на work, не все повторные попытки. Items показывают собственные result counts/outcomes/scores.

Attendance lessons_total — число записанных занятий в области; present/absent/late/excused/unknown — отдельные исходные статусы. Отсутствующие отметки показаны как unmarked. EXCUSED не считается отсутствием, UNKNOWN и unmarked не входят в denominator; данные не доказывают, что каждый текущий участник должен был присутствовать во все прошлые дни (OPEN-009).

## Исторический смысл содержания

После **любой** первой Attempt, включая COMMENT_ONLY и позднее архивированную Attempt, действует semantic lock. Он защищает содержание работы, состав Items, их maxima и явные Assessment/Item Topic/Skill links. Также защищена связанная семантика Topic/Skill и родительских тем: переименование, перемещение в иерархии и архивирование не должны переклассифицировать старые evidence.

Прежние migration snapshots v1–v4 сохраняются. Additive v5 устанавливает lock на существующие работы с историей по их **текущему** содержанию. Содержание на момент старого Attempt до установки v5 нельзя восстановить, если оно уже менялось в Phase 3–5: прошлых редакций нет. Это ограничение зарегистрировано явно; v5 защищает последующие изменения.

Изменение срока/даты выдачи остаётся явным редактированием расписания. Показатели своевременности используют текущий срок, поэтому перенос срока может пересчитать их; audit переноса не заявляется. Архивирование самой работы скрывает её из текущего среза, сохраняя Attempt/Items/results. Полная versioning/audit subsystem относится к отдельному заданию.

## Сроки и календарные даты

Assessment.due_at и Attempt.occurred_at — точные UtcInstant. Для сдачи используется первое содержательное предъявление; служебный COMMENT_ONLY не создаёт своевременную сдачу. Первое предъявление <= due_at — вовремя, > due_at — поздно. Если предъявления нет и due_at < as_of — просрочено, не сдано. На самом due_at срок ещё не прошёл.

Без due_at своевременность «Не применимо». Future deadline без предъявления пока не входит в долю своевременных сдач. Своевременность измеряет **первую сдачу**, а не время окончательного зачёта; поздняя переделка не меняет факт первоначальной своевременной сдачи.

LocalDate занятия/учебного периода не преобразуется в UTC midnight. Lesson не содержит точного времени; membership на конкретный день и учебный timezone автоматически не угадываются. calendar_days_late utility сравнивает локальные календарные даты только с явно переданным reporting timezone. Постоянный учебный timezone/date-only deadline остаются OPEN-009. Число часов между известными моментами не выдаётся за учебные дни.

## Topic/Skill evidence и отсутствие двойного счёта

Теги всей Assessment и её Items независимы. Результат всей работы не разносится по её частям; item score не наследует теги Assessment или TopicSkill. TopicSkill не является LessonSkill и не доказывает, что навык отрабатывался на занятии.

Отдельно показываются покрывающие Assessment и Items, результаты частей и CORRECT/PARTIAL/INCORRECT, оценённые результаты, средний score/max_score, студенты с evidence, явно связанные QuestionCase и число их уникальных авторов-студентов, Topic Lessons и записанная Attendance. Они не сворачиваются в один процент освоения. questions_by_students_count — число студентов с такими вопросами; student_message_count — число их Student Messages. QuestionAnalyticsSummary отдельно показывает Student/Teacher Messages и responses.

evaluated — score задан либо outcome CORRECT/PARTIAL/INCORRECT. NOT_EVALUATED без score остаётся неоценённым; при явно заданном score оба исходных факта сохраняются, score допускается для numeric metric. Outcome не переводится в долю балла. Average normalized item score — mean доступных result.score/result.max_score; нет подходящих пар → None. Lesson exposure count — distinct явно связанные Lesson; attendance_on_topic_lessons использует известные записи, без догадки о LessonSkill.

Родительская Topic объединяет собственные теги и descendants. Covering counts используют distinct Assessment/AssessmentItem UUID, evidence_count — typed distinct Attempt/AttemptItemResult/QuestionCase/Lesson/Attendance UUID. Один Item с parent и child Topic даёт один результат в родительской агрегации; один вопрос/занятие, связанный с несколькими descendants, также учитывается один раз. Наборы разных видов evidence различаются типом и ID; QuestionCase не размножается на его сообщения в общем evidence_count.

## Вопросы и время ответа

QuestionCase count и Student/Teacher Message counts отдельны. Открытый вопрос — closed_at отсутствует; ожидание преподавателя соответствует существующей CommunicationState projection. Связи Assessment/Topic/Skill считаются по distinct cases, без размножения через many-to-many joins.

Для времени ответа одна последовательность Student Messages до следующего Teacher Message образует один эпизод. Время считается от первого Student Message эпизода до первого последующего Teacher Message. Дополнительные сообщения студента не размножают один ответ. Неотвеченный эпизод не включается в среднее/медиану завершённых ответов. Одинаковый sent_at преподавателя и последнего сообщения студента не доказывает причинный порядок ответа: неоднозначный эпизод учитывается отдельно, без response time. Метрика — время локальной последовательности, без SLA, часов работы преподавателя и оценки качества ответа.

## N/A, динамика и границы чтения

Ratio с пустым denominator и score без достаточных score/max_score возвращают None. UI показывает «Нет данных»; отсутствие срока — «Не применимо». Настоящий score=0 с известным maximum даёт 0%, а не отсутствие данных. EXCUSED, UNKNOWN и отсутствующая Attendance не приравниваются к ABSENT.

as_of/timeline фильтруют известные факты по исходным event timestamps, сохраняют текущие структурные связи и текущее состояние изменяемых записей. Это динамика событий по имеющимся фактам, **не полный audit snapshot того, что было известно в Studium в прошлом**. Backdated capture может уточнить прежнюю точку; archive/correction исключает неверный факт из текущего расчёта.

Frozen typed DTO содержат domain values/обычные числа/tuples, без ORM Session/models; будущий CSV/Excel/PDF экспорт сможет работать с ними. Все queries read-only, не создают StudentWork, Grade, Attendance или результаты. Один query читает согласованный bulk snapshot; число SELECT не растёт как Students × Assessments. Performance проверяется на синтетической группе 30 × 20 с несколькими попытками, 10 занятиями, темами/навыками/вопросами.

В Phase 6 snapshot bulk читает текущие repository tables и фильтрует их в application. Это исключает N+1, но не заменяет будущую проверку памяти/времени на многолетней базе. Кэш и отдельный aggregation framework не добавлены; measured query budget/time опубликованы в done.md.
