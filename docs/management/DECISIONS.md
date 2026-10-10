# Действующие решения Studium

## QA-A — согласованные продуктовые решения 2026-10-11

[ADR-049](../decisions.md#adr-049--qa-a-product-contracts) и
[контракты/migration mapping](QA_A_CONTRACTS.md), база actual main
`b620ef3635c2965ad3630bae15d00d1b7bd9a82d`:

- B1: одна программа целого курса, immutable назначенная версия, отдельный
  календарь offering и explicit ordinal→period; no automatic copy/merge/switch.
- B2: deadline ДЗ/РК за модулем и после семестра разрешён с warning/confirmation;
  модули внутри семестра; preview/cancel no writes, confirmed package atomic.
- B3: date-only учебный день, explicit plan offset, Москва +03 default; exact
  priority/timestamps сохраняются, actual issuance отдельно, legacy ambiguous.
- B4: новый score/min/max integer default; сохраняемый bool toggle fractional
  2 digits/OFF. No hidden rounding, old fractions видны, история не меняется.
  Min — минимальный начисляемый балл, inclusive; отсутствие/revision не 0.
- B5: проверка на saved submission, immutable Review; no new Attempt/no при
  проверке/перепроверке. Legacy evidence не достраивается по Grade/соседству.
- B6: exact selected rule/snapshot в Review, old/new выбор для pre-change submission,
  current для новых сдач; старый result/min/max неизменен.

Технические предложения Content/Version/Plan, ReviewGrade, int64 cents/range и
compatibility resolver **PROPOSED до review**. Implementation/manual acceptance
не выполнены, application/migration/Windows/manual tests NOT RUN. Product agreement
не утверждает 10-PR plan и не закрывает 30 исходных замечаний. B7–B9 остаются QA-B/C;
общие остатки OPEN-002/009/011 сохраняются. Ниже прежние решения и их история.

Последующее уточнение review 2026-10-11 после HEAD
`3649afaee48be28d27f81ac41aff86087d594636`: [индивидуальный долг B2](QA_A_CONTRACTS.md#b2-student-debt)
сохраняется в T2 на исходной работе T1; только ACCEPTED всех обязательных работ
закрывает модуль студента, calendar группы прежний. Связь 011/029, полный UI QA-B.
QA-A-REV-01/02 уточняют запрет новой SCORED из REVISION_REQUIRED и допустимость
unchanged rule bounds snapshot при OFF; детали — contracts/ADR-049. Legacy fold/
REAL не меняются; mandatory binding/closure/archive policy требуют review.

## QA — принятые границы 2026-10-10

- [30 требований](QA_REGISTER.md) сохраняют ID/приоритеты и порядок QA-A/B/C/D.
  [Аудит](QA_AUDIT.md) завершён по коду; implementation и manual acceptance открыты.
- ST-QA-030: min — минимальный начисляемый балл, не порог зачёта. При 18–30
  numeric score только в этом диапазоне; pending/revision — без начисления,
  отсутствие оценки не равно 0. История и exact decimals обязательны.
- Новые изменения должны сохранять immutable Attempt/Grade/Attendance/FileAsset,
  UUID/UTC/revisions, transaction/file boundaries и historical v1–v9.
  Proposed content/semester/scoring/review schema пока не принята и не реализована;
  зависимые контракты B1–B9 перечислены в аудите. Min не переоткрывается.
- Разбиение QA-A на [10 последовательных PR](QA_AUDIT.md#qa-a-pr-plan) —
  предлагаемый план, ещё требующий утверждения владельца, а не принятое решение.
  Реализация ожидает утверждения плана и отдельного задания;
  порядок QA-A → QA-B → QA-C → QA-D сохраняется.
  QA-B/C/D и Bender этим аудитом не начинаются.
- Базовые публичные checks подтверждены чтением; первоначальный documentation audit
  Actions не запускал. Manual Windows/reporting/backup/installer не закрываются.
- [ADR-048](../decisions.md#adr-048--qa-register-и-семантика-min) дополняет
  исторические Grade/Program ADR; принятие min не переписывает существующий код.

Уточнение review 2026-10-10: ST-QA-019/020 совместно дорабатываются и принимаются;
это отделено от обязательных предварительных зависимостей и не задаёт цикл.
Первоначальный аудит не запускал Actions; для текущего документационного review
разрешены обычные автоматические required checks, без workflow_dispatch/full_windows.

## Сохранённые архитектурные и публикационные решения

- Windows-first local/offline PySide6; SQLAlchemy/Alembic/SQLite persistence.
- Domain/application contracts не получают ORM/UI/transport dependency.
- UUID/UTC, immutable факты попыток/сообщений, revision и additive migrations.
- Managed immutable file originals вне Git; derived analytics не меняют факты.
- Отдельные Studium и Bender repo с новыми независимыми histories.
- Первый Bender transport JSON-RPC 2.0 over stdio; HTTP допускается позднее.
- Jules пишет Bender implementation/tests/packaging/CI/API; Codex Studium/client.
- Repo migration до API/solvers/GUI; integration отдельным последующим этапом.
- Required safety/quality приоритетны; обязательный второй reviewer отдельно.
- Публичный source repository COLOSSAL-maksik/Studium-public, ветка main.
- All rights reserved, без открытой лицензии; third-party licenses сохраняются.
- Владелец подтвердил право публичного размещения всех 310 текущих материалов,
  созданных для проекта с помощью ChatGPT без сторонних изображений/дизайнов.
- Migration assertions используют frozen SHA-256 raw bytes без старой Git history.

Технические product ADR/OPEN — в [docs/decisions](../decisions.md).
Windows/manual acceptance и unfinished integration work не закрываются
этими решениями. Source-specific operational records в public docs не включаются.
