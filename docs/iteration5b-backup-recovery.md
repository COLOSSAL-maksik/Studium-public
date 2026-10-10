# Iteration 5B — Backup, Verification & Recovery

> Документ относится к Studium как независимому локальному приложению.
> Bender — отдельный проект; будущая интеграция использует локальный JSON-RPC
> 2.0 over stdio. Прямые импорты Bender, API/client, облачный сервер и новые
> возможности этим переносом не реализованы. Описания прежних фаз сохраняют
> технические требования; их проверки и acceptance не подтверждены этим текстом.

**Статус интеграции, проверка 2026-10-10:**
 влит в `main`
(`[историческая ссылка опущена]`). Следующий абзац описывает исходный этап открытого PR;
контракт и датированные проверки сохранены, ручная acceptance открыта.
Актуальные проверки и задачи — в [management](management/README.md).

Ветка `agent/codex/iteration5b-backup-recovery` начинается от merged Iteration 5A,
без merge. `src/bender/**`, `tests/bender/**`, `docs/bender/**` не затронуты.
Нет новых migrations, dependencies, серверов, telemetry или сетевых операций
в приложении. Разработка и проверки используют только synthetic records.

## Операции и архитектура

`application/backup.py`: frozen BackupEntry, BackupPreview, StorageHealth,
BackupPort, BackupService и cooperative BackupControl (threading.Event).
Application не импортирует SQLite, ZIP, ORM или Qt; domain не изменён.
Composition подключает BackupService к StudiumService через optional port.
Работники используют пути AppPaths и собственные краткоживущие SQLite connections;
они не получают живой connection/Session или QtFileOpener Runtime.

`infrastructure/backup.py`, `backup_paths.py`: SQLite Online Backup API,
потоковый ZIP, ограниченный manifest, verification, staging и publication.
`LocalFileStorage.backup_guard` переиспользует existing `.imports/lock` через
read-only handle; не создаёт и не изменяет active import journal.
Существующий import pipeline и recovery Runtime сохранены.

`presentation/desktop/backup.py`: компактные действия в существующих Настройках,
scroll при 960×620, Light/Dark, ошибки и результаты обычными plain-text labels.
IO выполняется existing BackgroundCall/QThreadPool, результаты и progress
доставляются queued Qt signals в GUI thread. Progress throttled, отмена
проверяется между chunks, SQLite pages и внутри SQLite progress_handler.
Закрытие окна запрашивает отмену; bootstrap уже ждёт workers перед Runtime.close.

## ZIP v1

Формат `studium-local-backup`, integer version `1`. Entries:

- `manifest.json`;
- `studium.sqlite`: самостоятельный SQLite snapshot без sidecars;
- точные existing `files/<prefix>/<UUID>.<extension>` из **всех** FileAsset rows,
  включая soft-deleted assets, detached links и shared Message/Attempt assets.

Manifest: format/version, Studium version, Alembic schema revision,
schema SHA-256, creation UTC, database_size, files с path/size/SHA-256.
Нет ФИО, групп, notes, original_filename, исходных source paths или file contents.
SHA-256 каждой data entry находится в manifest. Сам manifest не содержит
собственный self-hash; ZIP CRC проверяется при чтении. Preview добавляет hash
всего архива для повторной проверки перед restore.

Backup пишет ZIP_STORED (без сжатия), с ZIP64 для streaming large entries.
Verifier также принимает bounded DEFLATE и ZIP64 central directory.
Bytes идут chunks по 1 МиБ; архив и файлы целиком в память не загружаются.
Manifest и central-directory metadata имеют отдельные жёсткие ограничения.
Preferences/theme/sidebar/table widths не являются учебными фактами и не входят
в пакет; Runtime создаст их при дальнейшей работе. Cache, thumbnails, logs,
temp, `.imports`, backups/exports и SQLite sidecars исключены.

## Консистентность и атомарность

Backup удерживает existing межпроцессную file lock до публикации: import не
может вклиниться между file publication и DB commit. Любая journal entry кроме
lock означает pending import: операция отказывает, не выполняет recovery и
не удаляет originals. Startup Runtime остаётся единственным владельцем recovery.

Отдельный read-only SQLite connection начинает read transaction и закрепляет
WAL view, затем Online Backup API переносит snapshot. Учебные commits после
начала снимка могут продолжаться; backup содержит именно закреплённые факты.
FileAsset immutable bytes дают стабильный набор файлов для этого snapshot.
Все ключи, UUID/prefix, размеры и SHA-256 сверяются со snapshot metadata.
Изменение размера/hash/inode/mtime/ctime при чтении, после packaging или при
итоговом проходе отменяет публикацию. Источник не checkpoint/vacuum/migrate.

ZIP пишется exclusive temporary file **рядом с назначением**. После ZIP close,
flush/fsync, полной независимой verification и повторной сверки originals
`os.replace` публикует его атомарно. При ошибке временный ZIP и scratch удаляются,
предыдущий выбранный backup остаётся. Before/after tests сравнивают все source
bytes/permissions (включая journal, SQLite/WAL/SHM), records/revisions и schema.
Назначение повторно проверяется перед публикацией; concurrent replacement
выбранного файла/каталога отвергается.

## Verification и защита

Проверка автономна и всегда использует scratch вне production/Git. До ZipFile
ограничены размер файла, EOCD/ZIP64, central-directory bytes и фактическое число
central records (поддельному EOCD count не доверяем). Далее проверяются:

- ZIP CRC/структура, обязательные manifest/SQLite, exact expected entries;
- duplicate JSON keys, повторяющиеся entries и case-insensitive aliases;
- portable FileAsset grammar: нет traversal, absolute/drive/UNC/backslash,
  Windows devices/ADS, dot segments, directory entries или NUL aliases;
- Unix symlink/special type, DOS directory/reparse attributes, encryption;
- declared/actual sizes, SHA-256 и bounded decompression ratio;
- текущая Studium version и `0009_daily_workflow`; другие версии fail closed;
- SQLite `integrity_check`, `foreign_key_check`, exact schema fingerprint;
- все FileAsset metadata и наличие ровно соответствующих immutable bytes;
- повторные hashes уже материализованных файлов и неизменность input archive.

Эталонный schema fingerprint получается из **синтетической** fresh БД,
построенной existing Alembic migrations в scratch и cached в процессе. Это
отвергает архив, который заявляет current revision, но меняет tables/triggers.
Metadata schema ограничены 4096 objects/4 МиБ SQL; query_only/trusted_schema OFF,
SQL statement size ограничен 4 МиБ, attached DB запрещены.

Лимиты v1: 100000 ZIP entries (включая manifest/DB), 64 ГиБ total unpacked,
4 ГиБ snapshot, 1 ГиБ/FileAsset (existing file policy), 16 МиБ manifest,
32 МиБ central directory, ratio до 200:1, 60 секунд на snapshot.
Проверяется свободное место; реальные ENOSPC/permission failures также
обрабатываются. Превышение — явная ошибка, без partial publication.

SHA-256 не аутентифицирует автора: злоумышленник может изготовить полностью
самосогласованный пакет с вымышленными фактами. ZIP конфиденциален и не
зашифрован; требуется доверенный источник и безопасное локальное хранение.
Parents назначения должны находиться под контролем пользователя. Проверки
ссылок/identity не являются sandbox против процесса, который одновременно
враждебно переименовывает ancestors. Native Windows locking/ACL требуют приёмки.

## Модель restore

Restore не закрывает/переключает active Runtime. Выбирается **новый пустой root**
вне current/default production roots и Git, без symlinks/junctions. Непустой
root отвергается; overwrite mechanism отсутствует. Сначала archive полностью
проверяется в scratch, затем повторно читается в sibling staging с повторными
checksums/SQLite/FK/schema/metadata checks. Изменение ZIP после preview отказывает.
Перед публикацией managed bytes становятся read-only. Manifest не переносится
в рабочую структуру. Published root содержит SQLite и `files/` и открывается
existing `create_runtime(override=...)`; миграция archive не выполняется.

Для Windows выбранный existing empty directory удаляется **только rmdir**
непосредственно перед rename staging; при rename failure пустой directory
восстанавливается. Current/default roots и их ancestors никогда не выбираются
назначением. Cleanup удаляет только созданные unique scratch/staging paths,
включая Windows read-only files. После ошибки нет частично опубликованной
рабочей структуры. Отмена действует до короткого финального rename/replace;
после публикации результат завершён и не откатывается.

Повторная verification намеренно требует дополнительных IO и места:
verification scratch должен вместить всё содержимое; restore также требует
места в выбранном filesystem для staging. Проверка не обещает crash/power-loss
rollback, directory durability или cleanup после kill процесса/сбоя питания.
Автоматический switch текущего root, rollback активной базы, encryption,
cloud delivery, архивная ротация и orphan cleanup остаются вне этапа.

## Диагностика и проверки

StorageHealth показывает root, schema, logical snapshot size (включая WAL facts),
count/size всех FileAsset, SQLite/schema/FK integrity, missing/damaged counts
и disk free space либо «Не определяется». Никаких ФИО/file contents в DTO/UI/logs.
Диагностика не изменяет факты, не чистит архивы и не удаляет orphan files.

Synthetic regression suites: `tests/integration/test_backup_recovery.py`,
`tests/integration/test_backup_desktop.py`; existing files/desktop regressions
также запускаются. Покрыты roundtrip всех raw rows/schema/revisions, shared и
archived assets, WAL concurrent commit, malformed/hash/schema/FK spoofing,
missing/damaged/changing originals, pending/busy import, hostile ZIP paths/types,
duplicate/casefold/JSON aliases, ZIP64/forged central count/limits/bombs,
ENOSPC/permissions/publication failure, post-extraction damage, cancellation,
cleanup, source preservation, cancel dialogs, disabled invalid preview,
worker/GUI affinity, close cancellation и 960×620 Light/Dark длинные строки.

Linux Cloud использует `TMPDIR=/dev/shm` и отдельный pytest `--basetemp`, поскольку
служебный `/tmp/.git` среды вызывает штатный repository guard. Guards приложения
не изменены. Git CLI Cloud proxy недоступен; доступ к GitHub выполняется existing
connector, Git objects сверяются по SHA, baseline connectivity проверена.

До Windows исправления Linux/Python 3.13 pytest: **947 passed, 2 skipped / 1003.23s**.
Оба skip — Windows junction contracts (existing files и новый backup).
Targeted recovery/files/desktop: **139 passed, 2 skipped / 81.31s**;
финальные multichunk/archive-mutation/deadline regressions включены в full suite.
Ruff format/check (266 files), pip check, Repository safety worktree/history,
git diff whitespace и scope checks — **PASS**. Новых конфиденциальных/binary
материалов нет. Самые медленные Linux tests относятся к прежним desktop/theme
workflows; CI timeouts и guards сохранены. Статус Repository safety и Windows
Quality на опубликованном HEAD фиксируется в PR; local checks его не заменяют.

### Windows Quality: исправление сравнения timestamps

Первый Windows Quality остановился после 237 PASS: UI backup не опубликовал ZIP.
Безопасная диагностика worker подтвердила `ApplicationError` с кодом
`backup_source_changed` и штатным сообщением UI, без subject data или exception
payloads. CPython Windows `stat(path).st_ctime_ns` содержит creation time, тогда
как `fstat(fd).st_ctime_ns` содержит metadata change time
([CPython issue 157671](https://github.com/python/cpython/issues/157671)).
Сравнение полного tuple из разных APIs ошибочно отклоняло неизменившийся snapshot.

Для path/handle сравнения используются volume/file identity, size, mtime и
одноимённый `st_birthtime_ns`, если доступен. Полный raw `fstat`, включая ctime,
по-прежнему проверяется до/после IO. SHA-256, SQLite integrity/FK, schema checks,
path/link guards и staging/publication модель сохранены; новых dependencies нет.
Регрессии воспроизводят исходный отказ на синтетических stat records, проверяют
реальные path/handle metadata и отказ при изменении ctime во время чтения.
Native Windows test удерживает предыдущий ZIP без FILE_SHARE_DELETE: atomic
publication должна отказать, сохранив ZIP/source и удалив временные артефакты.
Локальный Linux targeted backup/desktop/files после fix: **140 passed, 2 skipped /
90.36s**; отдельно timestamp/sharing-lock regressions: **4 passed, 1 Windows-only
skipped**. Исходная timestamp регрессия сначала подтверждённо падала на прежнем
коде с `backup_source_changed`, затем прошла после исправления.

Quality теперь запускает targeted backup desktop/recovery tests перед полным
pytest. Report regression, полный suite, Repository safety и лимит 90 минут

## Обязательная ручная Windows-проверка

Использовать только synthetic data в новом root вне Git и настоящего профиля:

1. Запустить Python/actual packaged `Studium.exe --data-dir <synthetic-root>`.
   Создать учебный контекст, историю попыток/Grade/Attendance, message attachment,
   несколько больших файлов, detached/archived файл. Проверить Light/Dark 960×620.
2. Через native Save dialog создать ZIP вне root/Git. Отменить каждый native
   dialog, проверить отсутствие изменений. Проверить overwrite выбранного
   предыдущего backup только после подтверждения native Save dialog.
3. Во время копирования переключать тему/навигацию, отменить операцию и закрыть
   окно; приложение должно завершиться после cleanup worker. Проверить отсутствие
   temporary ZIP/staging, сохранность originals и прежнего архива.
4. Во втором synthetic экземпляре начать import; проверить взаимное исключение
   через Windows byte-range lock. Backup при pending import должен отказывать;
   штатный перезапуск должен восстановить import journal.
5. Проверить ZIP отдельно, затем preview/restore в пустую sibling папку.
   Непустой root, active root, Git/worktree, symlink/junction и сетевые paths
   с небезопасными ссылками должны отказывать. Проверить ACL denial/ENOSPC и
   файл назначения, удерживаемый Windows процессом.
6. Закрыть source приложение и запустить packaged exe с `--data-dir` restored
   root. Сравнить историю/revisions, Grade/Attendance, file hashes, работу Help,
   затем открыть source root и подтвердить сохранность исходных фактов.
7. Проверить повреждённый/обрезанный ZIP и несовместимую schema: restore disabled.
   Обязательны actual exe resources Alembic/Help, native dialogs/locks/ACL/junctions;
   Linux/offscreen CI не заменяет эти проверки.
