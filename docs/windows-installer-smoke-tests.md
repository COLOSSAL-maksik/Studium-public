# Windows installer smoke tests — synthetic only

> Документ относится к Studium как независимому локальному приложению.
> Bender — отдельный проект; будущая интеграция использует локальный JSON-RPC
> 2.0 over stdio. Прямые импорты Bender, API/client, облачный сервер и новые
> возможности этим переносом не реализованы. Описания прежних фаз сохраняют
> технические требования; их проверки и acceptance не подтверждены этим текстом.

Проводить в disposable Windows x64 VM/отдельной учётной записи без реальных
данных. **Non-admin user** обязателен для ручной проверки обычной установки.
Не использовать рабочий профиль преподавателя. SmartScreen/Defender остаются
включёнными; блокировка означает STOP.

## Автоматический lifecycle

После сборки на Windows, из developer checkout:

```powershell
.\.venv\Scripts\python.exe scripts/smoke_installer_windows.py --installer '.\dist\installers\Studium-Setup-0.1.0.exe' --disposable-account
```

Harness отказывается при существующей HKCU/HKLM регистрации Studium,
использует новые temporary program path и LOCALAPPDATA profiles вне Git.
Developer Python нужен только для synthetic seed и сравнений. Установленный
EXE запускается с PATH только из Windows и без PYTHONPATH/PYTHONHOME.
UIA ограничена PID своего процесса/его onedir child, закрытие штатное.
Registry и Start menu затрагиваются: disposable account обязателен.
Рядом с каждым тестируемым EXE нужен соответствующий `.payload.json` из
сборки: harness сравнивает установленные files/size/hash и отвергает лишние
files, кроме собственных Inno uninstall files и `studium-payload.txt`.
Содержимое ownership списка также должно точно совпасть с payload manifest.

Проверяются fresh AppPaths/Alembic, видимое окно, offline Help/search,
три synthetic students и managed TXT, две загрузки с сохранностью records,
attachments/preferences, repair после удаления **и повреждения** owned DLL,
отказ while-running (без закрытия чужих процессов), uninstall/reinstall и побайтовая
сохранность data root после uninstall. Затем удаляется только собственная
temporary synthetic структура. Silent install не проверяет postinstall UX.

Для **настоящего upgrade** нужен второй, действительно более новый build:

```powershell
.\.venv\Scripts\python.exe scripts/smoke_installer_windows.py --installer 'C:\SyntheticQA\Studium-Setup-0.1.0.exe' --upgrade-installer 'C:\SyntheticQA\Studium-Setup-0.1.1.exe' --disposable-account
```

Без второго installer выполняется same-version repair с двумя реальными fault
cases; отчёт явно указывает
NOT RUN для newer-version upgrade. Версии сравниваются численно, проверяется
metadata установленной программы. Smoke рассчитан на текущую схему;
acceptance будущих migrations требует дополнительных тестов.
Quality job `windows-installer` компилирует настоящий Inno EXE и выполняет
same-version lifecycle на Windows runner. Бинарные артефакты PR CI не публикует.

Отдельная автоматизация собирает два настоящих packaged app/installer builds:

```powershell
.\.venv\Scripts\python.exe scripts/smoke_installer_upgrade_windows.py --disposable-account
```

Нужен свежий `dist/Studium` текущего commit. Тест архивирует только tracked
source во временные каталоги вне Git, повышает app version только в **копии**
и заново запускает PyInstaller. Он не меняет версии source/dependencies в PR.
Оба setup компилируются из shipping `Studium.iss`, app/setup ProductVersion
сверяются с source/registration. Payload добавляет/изменяет/исключает synthetic
unused DLL fixtures и исключает synthetic Help article; hashes EXE/setup
должны различаться. После upgrade состав/size/SHA-256 совпадают с новым manifest,
obsolete files отсутствуют. Downgrade старым EXE должен дать exit 7 и unchanged
program/data/registration. Stable AppId оставляет одну HKCU identity, HKLM пуст.

Lifecycle также проверяет пути с пробелами/кириллицей, start-menu shortcut,
desktop opt-in и удаление обоих, совпадение всего data-root hash с закрытым
EXE, integrity/FK/facts/attachment bytes, reinstall с прежними synthetic данными.
SQL comparisons используют immutable read-only connection только после закрытия
и checkpoint; непустой WAL вызывает отказ, а валидатор не создаёт sidecars.
Полный root snapshot берётся с закрытым EXE до/после repair/upgrade/uninstall.
Running-app refusal отдельно сравнивает program/registry/data прямо вокруг
отклонённой операции, затем после закрытия проверяет facts/attachments/preferences.
Backup API может создать пустые SQLite WAL/SHM: прежние bytes должны совпасть,
другие additions и непустой WAL запрещены; эти sidecars не маскируются в
последующих полных installer snapshots.
Restore сравнивает DB-referenced FileAsset paths/size/SHA-256 и фактические bytes.
`files/.imports/lock` — служебный import journal, он не является вложением и
по существующему контракту не входит в backup. Полные source root snapshots
installer-операций включают и этот файл; backup compatibility не изменяется.
Для recovery сохраняются только audited bytes прежней программы и backup:
matching-version API create/verify/restore в пустой root → прежний packaged
EXE открывает **только восстановленную копию**, active/newer root неизменен.
Source API версия должна совпадать с old installer, иначе recovery явно NOT RUN.
GUI backup/restore и non-admin/default-path/UAC/postinstall acceptance этим
не подтверждаются. Две версии содержат synthetic test files: они удаляются
после теста, не публикуются и не являются beta release artifacts.

## Native security regressions

В том же disposable Windows account без существующей Studium registration:

```powershell
.\.venv\Scripts\python.exe scripts/smoke_installer_security_windows.py --disposable-account
```

При необходимости: `--inno-setup-compiler 'C:\BuildTools\Inno Setup 6\ISCC.exe'`.
Harness компилирует **отдельный** `installer/tests/Synthetic.iss`: другой AppId,
временный встроенный data root, placeholder payload без runnable Studium.
Shipping `Studium.iss` не принимает `SyntheticTestRoot`. Обе конфигурации
используют один `InstallSafety.iss`; тесты запускают настоящие native Inno EXE.
Рабочий `%LOCALAPPDATA%\Studium` не открывается и не заменяется.

Проверки отказа: data root/ancestor/отсутствующий descendant, 8.3 alias
(включая отсутствующий target), junction/symlink в target/ancestor и payload
subdirectory, trailing-dot alias отсутствующего data root. Ожидается именно
Inno exit **7** (`PrepareToInstall`), полный unchanged snapshot synthetic
files/directories/SQLite/attachments/preferences и fixture HKCU registration.
Snapshot не следует по reparse points. Если filesystem не предоставляет 8.3
alias либо link creation недоступно, JSON явно фиксирует **NOT RUN**;
не включать capability и не повышать права ради превращения skip в PASS.

Native upgrade fixture **1.9.0 → 1.10.0** добавляет/изменяет/исключает DLL и Help resource:
после установки новый список/размеры/hashes совпадают, исключённые files
отсутствуют, unknown sentinels в root и retired subdirectory сохранены,
synthetic DB/files/preferences неизменны. Проверяются численный downgrade refusal,
same-version repair после удаления/повреждения DLL,
uninstall и сохранность data/unknown files. Tampered receipt, traversal,
absolute/ambiguous/device paths, duplicate ownership entry и изменённая
прежняя DLL отвергаются без file/registry changes. JSON выводится в CI log;
fixture installers и данные удаляются и никогда не публикуются.

Версии placeholder fixture проверяют механику очистки; отдельный harness выше
проверяет два заново скомпилированных app builds. Real release acceptance,
non-admin interactive UX и PDF/backup/restore остаются отдельными gates.
Pre-inventory installer `[историческая ссылка опущена]` требует штатного uninstall перед новым
форматом (data root сохраняется); ownership не восстанавливается догадками.

## Packaged Qt/Alembic/Help/PDF workflow

После установки выполните existing native UIA harness на установленном EXE:

```powershell
.\.venv\Scripts\python.exe scripts/smoke_iteration4_packaged.py --exe "$env:LOCALAPPDATA\Programs\Studium\Studium.exe" --output '.\tmp\installer-native-resources'
```

Его profiles временные и синтетические; реальные данные не читаются.
Проверяются fresh/v8 migration, Qt UI/charts, native file workflow, managed
image после удаления источника, PDF preview, offline Help и reopen.
`--source` не является packaged acceptance. PDF export, backup/restore
и Explorer drag/drop проверяются отдельно вручную.

## Ручной checklist

В disposable non-admin профиле выполните последовательно. Для каждой строки
запишите PASS/FAIL/NOT RUN. Linux и исторические результаты сюда не переносить.

| Проверка | Действие и ожидаемый результат |
|---|---|
| Источник | SHA-256 совпадает с доверенным значением; versions/commits обоих builds известны. |
| Fresh install | Обычный запуск EXE: русский мастер, правильные name/version/publisher, обязательного UAC нет. Default path `%LOCALAPPDATA%\Programs\Studium`. |
| Ярлыки | Без checkbox desktop shortcut отсутствует; Start menu запускает EXE. Повторить с checkbox: desktop shortcut работает. |
| Postinstall | С галочкой запуска открывается Studium без Python/Git; без галочки запуск отсутствует. |
| Default AppPaths | В Настройках root `%LOCALAPPDATA%\Studium`; в program path нет SQLite/preferences/files. Повторить с другим допустимым program path: data root тот же. |
| Alembic | Fresh Home без startup error, схема `0009_daily_workflow`; SQLite создан runtime, его не было в payload. |
| Synthetic DB | Создать `SYNTHETIC 2026`, дисциплину, группу `TEST-01`, `Студент 001–002`, работу и попытку. Только вымышленные данные. |
| Attachments | Создать synthetic PNG/PDF/TXT, импортировать к попытке. Закрыть EXE, удалить только исходные synthetic files вне managed root. Открыть: records/managed bytes доступны. |
| Qt/Help | Русский текст, Light/Dark, icons/charts, native picker работают. Offline статьи открываются; search находит текст. |
| PDF | PDF attachment отображается в preview. Экспортировать synthetic Report в PDF вне program/data roots; открыть PDF, проверить кириллицу/содержание/страницы. |
| Backup | Настройки → создать synthetic ZIP вне active root/Git → дождаться завершения → проверить архив. Нет missing/damaged assets. |
| Restore | Restore preview → новый пустой root вне Git/current root. Активная БД прежняя. Открыть восстановленный root через `--data-dir`: facts/PDF/images совпадают. Непустой target отклоняется. |
| Reopen | Закрыть/открыть дважды: те же facts/files/выбранный период/тема. Зафиксировать counts/hashes перед upgrade. |
| Newer-version upgrade | Закрыть EXE, сохранить backup, поставить реальную следующую версию в прежний program path без uninstall. Version обновилась, в Windows Apps одна запись; facts/files/preferences сохранены. |
| Uninstall | Закрыть EXE, удалить через Windows Apps: программа/Start menu/выбранный desktop shortcut удалены; своих зависших процессов нет. |
| Data after uninstall | Default data root остался; DB/files/preferences hashes совпадают с snapshot после последнего закрытия. Переустановка открывает те же synthetic данные. |
| Privacy payload | До первого запуска exact set/hash установленного payload совпадает с `.payload.json`; дополнительные файлы только Inno uninstall metadata (`unins000.exe/.dat`, при наличии `.msg`) и проверенный `studium-payload.txt`. Нет SQLite/FileAsset/backups/exports/logs/settings/real documents. |

Дополнительная отдельная synthetic DB разработчиком (каталог `data` новый):

```powershell
$qaRoot = Join-Path $env:TEMP ('Studium-Synthetic-' + [guid]::NewGuid().ToString('N'))
.\.venv\Scripts\python.exe scripts/create_demo_data.py --data-dir (Join-Path $qaRoot 'data')
& "$env:LOCALAPPDATA\Programs\Studium\Studium.exe" --data-dir (Join-Path $qaRoot 'data')
```

Existing/production/Git roots отвергаются. Test root не должен находиться
под каталогом с `.git`. После закрытия можно удалить только созданный
`$qaRoot`. Восстановленный root открывается аналогично с `--data-dir`.

Проверка установленного payload по локальному manifest:

```powershell
$manifest = Get-Content -LiteralPath '.\dist\installers\Studium-Setup-0.1.0.payload.json' -Raw | ConvertFrom-Json
$program = Join-Path $env:LOCALAPPDATA 'Programs\Studium'
foreach ($entry in $manifest.files) {
    $actual = (Get-FileHash -LiteralPath (Join-Path $program $entry.path) -Algorithm SHA256).Hash
    if ($actual -ine $entry.sha256) { throw 'Installed payload differs from audited build.' }
}
```

Просмотрите также **весь** список program files: hash сверка сама по себе
не ловит лишние files. Manifest не является криптографической подписью.
Тестовые материалы никогда не включать в installer ради acceptance.

## Запись результата

Запишите versions/commits, installer SHA-256, Windows edition/build/x64,
non-admin статус, дату, команды/exit codes и результаты всех строк.
Не публикуйте raw data, account paths или личные screenshots.

Начальный ручной статус — **NOT RUN** до native выполнения. Windows CI
подтверждает compilation/security/two-version lifecycle только своими logs;
non-admin default path/UAC, wizard language/metadata, interactive shortcuts и
оба postinstall launch variants остаются **NOT RUN**, если клиентской VM нет.
Real release upgrade,
интерактивная установка, PDF/backup/restore требуют заполненного Windows
report перед распространением beta. Linux synthetic audit не является
Windows installer acceptance.

## Зафиксированная автоматическая проверка

2026-10-09, code HEAD `[историческая ссылка опущена]`:

PASS. Inno 6.7.1 / Python 3.12.10, disposable Windows runner, **не non-admin client VM**.
23 security case groups PASS; 8.3/junction/symlink доступны и проверены без skips.
Fresh lifecycle, оба repair faults, running-app refusal, shortcuts,
uninstall/reinstall, matching-version recovery PASS. Genuine packaged upgrade
0.1.0 → 0.1.1 с add/change/remove payload, downgrade refusal и whole closed-data
hashes PASS. Source app/dependency versions не менялись; test binaries удалены.
Это запись конкретного code HEAD; результат Quality и повторного native job
после следующих commits смотрите в PR. Все пункты non-admin/interactive/PDF/
GUI backup checklist требуют отдельной клиентской приёмки и остаются NOT RUN.
