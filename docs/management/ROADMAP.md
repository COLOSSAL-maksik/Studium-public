# Этапы Studium

## QA-A — актуальное дополнение 2026-10-11

[Контракты/migration mapping](QA_A_CONTRACTS.md) документируют согласованные
B1–B6 на actual main `b620ef3635c2965ad3630bae15d00d1b7bd9a82d`:
content freeze/ordinal→period, confirmed deadlines вне module/semester,
typed date-only/exact, integer default + fractional toggle 2 digits/OFF,
submission/review/Grade и выбранные rules. Technical proposals ещё требуют review.

Документационный scope PR-01 подготовлен; implementation не начат. План из 10 PR
не утверждён. Предлагаемый следующий небольшой PR-02 — directions foundation
и schema/backup compatibility с сохранением raw legacy text, без большой формы;
prerequisites/tests/exit указаны в контрактном документе. PR-09 должен включить
точное storage/range/validation и ReviewGrade/rule/evidence основу, PR-10 — UI
сохраняемого fractional toggle, unsaved validation и историческое отображение.
B7–B9 и полный review queue остаются своим следующим этапам.

Порядок QA-A → QA-B → QA-C → QA-D, ID/приоритеты и отдельная приёмка/merge
каждого этапа сохранены. Product agreement не означает implementation/manual PASS;
application/migration/Windows/manual tests NOT RUN. История roadmap ниже сохранена.

Дополнение review 2026-10-11 после исходного HEAD PR #2:
[B2](QA_A_CONTRACTS.md#b2-student-debt) фиксирует required-work/individual closure
границу и долг прошлого семестра, не растягивая calendar группы. Полный доступ
и регистрация/сводка/queue в active T2 относятся к QA-B (027/029/017);
ended-enrollment/explicit archive policy требует technical review. Score PR-09/10
учитывают QA-A-REV-01/02 из contracts; никакого нового implementation PR сейчас.

## QA — актуальное дополнение 2026-10-10

Архитектурный аудит 30 ST-QA завершён; требования и технические evidence —
[QA_REGISTER](QA_REGISTER.md) и [QA_AUDIT](QA_AUDIT.md).
Порядок этапов QA-A → QA-B → QA-C → QA-D сохраняется. Внутреннее разбиение QA-A
на 10 PR — предлагаемый план, ещё требующий утверждения владельца.
Ниже предлагается последовательность работ после утверждения плана
и отдельно назначенной реализации:

1. QA-A (002/003/006/010/011/013/030): контракты → направления → содержание/версии
   → отдельный календарь группы → формы/display names → План семестра
   → история переносов → фактическая выдача → exact баллы → UI/приёмка.
   [Предлагаемые 10 небольших последовательных PR](QA_AUDIT.md#qa-a-pr-plan),
   разбиение ещё не утверждено владельцем.
2. QA-B (008/009/012/015/017/027/028/029): типы работ, отдельные lesson/work cells,
   регистрация сдач, review/returned files, FIFO и factual summary.
3. QA-C (014/021/022/023): workflow вариантов внутри работы, единый pending
   attachment picker, structured answers и точное дерево выбора тем.
4. QA-D (001/004/005/007/016/018/019/020/024/025/026): interaction, общие styles,
   layout и native Windows Light/Dark/DPI visual acceptance.

Переход после review/приёмки предыдущего этапа и отдельного merge пользователем.
Preview/cancel нужен уже в QA-B; поздняя унификация 021 не откладывает его.
Этот аудит не начинает QA-A. Native reporting/backup/installer acceptance и
будущая интеграция остаются самостоятельными задачами; Bender вне QA scope.
Public main и существующие базовые checks подтверждены в PROJECT_STATUS;
исторический план подключения ниже сохранён.

Уточнение review 2026-10-10: сценарии ST-QA-019/020 совместно дорабатываются
и принимаются в QA-D, без взаимной обязательной предварительной зависимости.

## История этапов — подготовка самостоятельного репозитория

1. Локальное приложение и независимая чистая source history сохранены.
2. Frozen migration fixtures, package/regression и privacy приняты локально.
   Native Windows/manual acceptance выполняется отдельно; NOT RUN учитывается.
3. Владелец выбрал COLOSSAL-maksik/Studium-public, All rights reserved и подтвердил
   права на все 310 материалов. Локальный bundle готовится для публикации владельцем.
4. После подключения GitHub: защита main и отдельно разрешённые Actions.
   Required CI закрепляется после первых успешных actual checks.
5. После миграции: Jules Bender stdio API, Codex Studium client; contract tests.

Bender independent packaging/tests/CI делает Jules после GitHub access.
API/solvers/GUI не блокируют source split. Старые active задачи не retarget
до сохранения residual work; source snapshots и rollback остаются private.
