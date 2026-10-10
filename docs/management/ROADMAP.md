# Этапы Studium

## QA — актуальное дополнение 2026-10-10

Архитектурный аудит 30 ST-QA завершён; требования и технические evidence —
[QA_REGISTER](QA_REGISTER.md) и [QA_AUDIT](QA_AUDIT.md).
Следующая продуктовая последовательность после отдельно назначенной реализации:

1. QA-A (002/003/006/010/011/013/030): контракты → направления → содержание/версии
   → отдельный календарь группы → формы/display names → План семестра
   → история переносов → фактическая выдача → exact баллы → UI/приёмка.
   [Десять небольших последовательных PR](QA_AUDIT.md#qa-a-pr-plan).
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
