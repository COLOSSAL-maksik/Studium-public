# Состояние Studium

## Дополнение ST-PR3-002 — frozen taxonomy

На базе `67986fd` archive Topic/Skill, используемых сохранённой версией/назначением,
отклоняется с concrete dependency list. Новая v12 добавляет только два archive
guards; 22 v1–v11 payloads, прежние facts/UUID и SQL guards сохраняются.
27 новых synthetic regressions, итоговый targeted пакет **165 PASS**. Required CI
нового HEAD фиксируется в PR; manual всех 30 — PENDING. [Отчёт](PR3_REVIEW_FIXES.md).
Ниже сохранены предыдущие implementation/verification результаты.

## Исправления review PR #3

Все четыре замечания исправлены в существующей ветке и PR #3 с сохранением
пакета всех 30: late first submission при ended participation; frozen V1
problem/family/attachments; explicit preview/CAS переназначения с прежними
bindings; полная сводка ДЗ/РК/посещаемости и переходы. Additive v11,
v1–v10 payloads неизменны. [Отчёт](PR3_REVIEW_FIXES.md), [ADR-051](../decisions.md#adr-051).
Целевые DB/GUI: 38 PASS; полный local regression: 1113 PASS / 3 ожидаемых
Windows-only SKIP. Wheel/source/resources/fresh/reopen/GUI: PASS. Проверки
v1–v10, Ruff, pip и safety: PASS. Новое exact-HEAD CI evidence — в итоговом PR.
Manual всех 30 — PENDING, промежуточная приёмка не требуется. История ниже
сохраняется; старые результаты не объявляются проверкой нового HEAD.

## Единый implementation-пакет — решение 2026-10-10

Владелец расширил задачу до всех ST-QA-001–ST-QA-030 в одной ветке
`agent/codex/qa-a-contracts` и одном итоговом implementation PR. База реализации:
`d23eee39fcb0f3bd463c2868459fa48d0778925a`; документационная база PR #2 сохранена.
QA-A → QA-B → QA-C → QA-D — внутренний порядок зависимостей после необходимых
автоматических проверок. Промежуточные ручные приёмки и merge между этапами
отменены этим решением; общий manual acceptance остаётся PENDING после пакета.
Прежний план десяти QA-A PR и directions-only scope — исторические предложения.

B7–B9 впервые заданы этим пакетным решением: SLA 7 календарных дней от received_at
в explicit offset, near-due последние 24 часа, overdue строго после deadline;
«выполнено» — подтверждённая содержательная сдача, «зачтено» — explicit ACCEPTED,
cancelled исключается из active denominator; шаблоны structured answers копируются
в immutable task/variant snapshots, teacher-only данные не публикуются студенту.
Норматив и near-due настраиваются. Ранее не подтверждённое согласование не выдумывается.

Текущие implementation/evidence и manual pending ведутся в
[QA_ALL_30_IMPLEMENTATION](QA_ALL_30_IMPLEMENTATION.md). Матрицы и записи ниже
сохраняют исторический baseline; они не являются статусом нового пакета.


## Актуальное дополнение — 2026-10-11

Actual main перед работой: `b620ef3635c2965ad3630bae15d00d1b7bd9a82d`.
Отдельно подготовлены [QA-A contracts/migration mapping](QA_A_CONTRACTS.md) и
[ADR-049](../decisions.md#adr-049--qa-a-product-contracts). B1–B6 согласованы
продуктово; B4 — integer default + сохраняемый fractional toggle 2 digits/OFF,
B2 разрешает подтверждённый deadline после семестра, но не module за семестром.
Technical schema/storage/Grade proposals ожидают review. Разбиение на 10 PR
не утверждено; ближайший предложенный implementation — directions foundation
PR-02 с backup support и preservation tests, после отдельного задания.

Все 30 ID/приоритеты и QA-A → QA-B → QA-C → QA-D сохранены. Исходные статусы
2/22/6 — прежняя статическая оценка, не исправленные замечания. Код приложения,
миграции, dependencies, CI и installer не изменены; implementation/manual acceptance
не выполнены. Application/migration/Windows/manual tests NOT RUN. Документационные
локальные проверки и ordinary required quality/safety **итогового HEAD** публикуются
в PR/отчёте, отдельно от предыдущих CI результатов ниже. Merge не выполнен.

Последующее documentation review 2026-10-11 на базе HEAD
`3649afaee48be28d27f81ac41aff86087d594636`: [B2](QA_A_CONTRACTS.md#b2-student-debt)
добавляет индивидуальный долг T1 при active T2 и закрытие по ACCEPTED всех
обязательных работ. Исправлены QA-A-REV-01/02 (Review transitions и unchanged
rule bounds snapshot при OFF). Mandatory/closure модель и запись при ended
membership/explicit archive не реализованы; полный UI долгов — QA-B. Это новое
уточнение после первоначальных contracts, не ранее выполненная функция.

## Актуальное дополнение — 2026-10-10

База архитектурного аудита: public `main`,
`ef5414faa594eba0f339d4208d605c92e98de903`. Проверено по исходникам:
30/30 ST-QA; 2 реализованы, 22 частично, 6 отсутствуют. Это статусы реализации,
не закрытие ручной приёмки. [Матрица и evidence](QA_AUDIT.md),
[реестр](QA_REGISTER.md), [предлагаемые 10 PR QA-A](QA_AUDIT.md#qa-a-pr-plan).
Разбиение QA-A на 10 PR ещё требует утверждения владельца и не утверждено;
порядок QA-A → QA-B → QA-C → QA-D сохраняется.
Программа связана с периодом; normalized directions, schedule history,
exact min/max, review/return lifecycle требуют расширений. Min уже решён:
минимальный начисляемый балл; отсутствие оценки и доработка без автоматического 0.

Для указанной базы прочитаны существующие публичные результаты
[Quality](https://github.com/COLOSSAL-maksik/Studium-public/actions/runs/38081188251)
и [Repository safety](https://github.com/COLOSSAL-maksik/Studium-public/actions/runs/38081144482)
— success; main защищён с required quality/repository-safety.
Это актуализирует прежнюю запись о локальной подготовке ниже. Результаты базы
не являются evidence исправления ST-QA или native Windows/manual PASS.
В документационном аудите Actions не запускались, pytest/Ruff/package/manual
NOT RUN; приложение, миграции, зависимости, CI и установщик не менялись.
Implementation QA-A ожидает отдельной задачи и решения зависимых контрактов.

Уточнение review 2026-10-10: ST-QA-019/020 дорабатываются и принимаются совместно,
без взаимной обязательной предварительной зависимости. Для документационного PR
разрешены обычные автоматические required checks нового HEAD; их фактические
результаты фиксируются в PR. Ручной workflow_dispatch/full_windows не запускается.

## История состояния — подготовка самостоятельных исходников

Studium — самостоятельное локальное приложение преподавателя с PySide6,
SQLAlchemy/Alembic и SQLite. Source содержит учебные программы, группы/студентов,
работы/попытки/оценки, immutable attachments, Q&A, factual analytics,
отчёты, offline help и ZIP backup/recovery. Миграции v0001–v0009 сохранены.

Независимый package discovery и Studium-only routing подготовлены.
Целевой публичный repository: COLOSSAL-maksik/Studium-public, main.
GitHub repository/push/Actions и Windows release этой локальной подготовкой
не выполняются. Три migration immutability tests используют проверенные frozen
SHA-256 и raw bytes без old Git dependency; 18 migrations сохранены.
Принятый Stage 2: 1043 passed, 3 expected Windows skips, 0 failed/errors;
Ruff и source wheel/sdist/import PASS на Linux. Результат не означает Windows PASS.
Исходный код: All rights reserved, без открытой лицензии; лицензии зависимостей
сохраняются. Владелец подтвердил публикационные права на все 310 материалов.
Windows/manual acceptance остаётся отдельной задачей.
Локальные результаты не заменяют Windows или GitHub PASS.

Bender source отделён; результаты foundation/benchmark разработки не считаются
release/acceptance. Всё Bender code/tests/packaging/CI — Jules; bootstrap после
new repository access. Studium API/client ещё отсутствуют; transport утверждён
как JSON-RPC 2.0 over stdio. Нет обязательного cloud server или общей DB.
