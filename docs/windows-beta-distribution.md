# Studium: Windows beta distribution

> Документ относится к Studium как независимому локальному приложению.
> Bender — отдельный проект; будущая интеграция использует локальный JSON-RPC
> 2.0 over stdio. Прямые импорты Bender, API/client, облачный сервер и новые
> возможности этим переносом не реализованы. Описания прежних фаз сохраняют
> технические требования; их проверки и acceptance не подтверждены этим текстом.

Результат — один `Studium-Setup-<version>.exe`. Для установки и работы
тестировщику не нужны Python, Git, Inno Setup или терминал. Сборка:
Windows x64 / Python 3.12 x64; native Windows acceptance обязательна.
ARM64/x64 emulation отдельно не подтверждена.

## Сборка разработчиком

Используйте чистую рабочую копию проверенного commit. Версия должна совпадать
в `pyproject.toml` и `src/studium/__init__.py` (`major.minor.patch`). Для нового
релиза повышайте обе версии; скрипт не изменяет версии автоматически.
Не выдавайте разные builds за одну версию.

Установите Python 3.12 x64 и **Inno Setup 6.3+** из официального источника
[jrsoftware.org](https://jrsoftware.org/isinfo.php). Inno — отдельный Windows
build tool; Python dependencies не изменены. Подготовьте venv:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.lock -r requirements-build.lock
.\.venv\Scripts\python.exe -m pip install --no-deps -e .
```

Из корня checkout сборка запускается одной командой:

```powershell
.\scripts\build_installer_windows.ps1
```

Скрипт вызывает сохранённый `scripts/build_windows.ps1`, проверяет native
ProductVersion EXE, ресурсы и безопасность onedir, делает новую изолированную
копию payload и вызывает ISCC. Для нестандартного расположения компилятора:

```powershell
.\scripts\build_installer_windows.ps1 -InnoSetupCompiler 'C:\BuildTools\Inno Setup 6\ISCC.exe'
```

Для **уже собранного текущего** onedir можно добавить `-SkipAppBuild`.
Старый EXE без version resource либо с другой версией отвергается.
Пропущенная сборка не доказывает соответствие compiled Python текущему
commit; перед передачей используйте полную сборку из чистого checkout.

Результаты в игнорируемом `dist/installers/`:

- `Studium-Setup-<version>.exe` — единственный обязательный файл установки;
- `Studium-Setup-<version>.exe.sha256` — контрольная сумма;
- `Studium-Setup-<version>.payload.json` — список, размеры и SHA-256 файлов
  проверенного payload для локального аудита разработчиком.

Скрипт выводит абсолютный путь EXE и hash. Уникальный `build/installer-<GUID>`
удаляется после успеха или ошибки; onedir, другие сборки и пользовательские
roots не очищаются. Ссылки/junctions в build/output/payload отвергаются.
Перед записью проверяются также output file targets; перед удалением stage
все его entries проверяются без следования по reparse points. Если stage стал
linked, cleanup отказывается и оставляет его для локального review вместо
удаления через перенаправление.
Предыдущий installer остаётся при ошибке компиляции: перед отправкой
убедитесь в успешной текущей сборке. `build/` и `dist/` уже исключены из Git.

## Безопасность пакета

AppPaths хранит SQLite, preferences и FileAsset в `%LOCALAPPDATA%\Studium`,
отдельно от `%LOCALAPPDATA%\Programs\Studium`. Установщик не открывает,
не создаёт и не импортирует пользовательскую БД. Alembic выполняется
существующим приложением при старте; новых migrations здесь нет.
Установка/uninstall работают с перечисленными программными файлами и ярлыками.
Инструкций удаления пользовательского root нет.

Перед записью и регистрацией установка разрешает физические расположения
каталогов через Windows directory handles (`GetFinalPathNameByHandleW`).
Отсутствующий target разрешается от ближайшего существующего предка;
8.3 aliases учитываются. Data root, его предки и потомки запрещены.
Reparse points в program path/предках, используемых payload subdirectories
и file targets останавливают установку. UNC/device paths и неоднозначные
компоненты с завершающей точкой/пробелом также отвергаются. Per-user режим
`lowest` сохранён; elevation ради проверки не требуется.

В program directory устанавливается `studium-payload.txt`: только относительные
program paths и SHA-256, без пользовательских данных. Digest списка сохраняется
в HKCU uninstall registration. Upgrade проверяет digest, syntax/duplicates,
каталоги и hashes прежних файлов **до изменения установки**. Он удаляет только
файлы прежнего списка, отсутствующие в новом payload; recursive cleanup нет.
Посторонние файлы, включая файлы внутри `_internal`, сохраняются. Изменённый
устаревший файл или повреждённый список останавливают upgrade; неизвестные
файлы на путях нового payload также не перезаписываются. Пустые старые
подкаталоги могут остаться. Список/digest служат учёту ownership, а не цифровой
подписи; signing всё ещё не реализован.

Удалённые/повреждённые owned files, входящие в новый payload, восстанавливаются
при repair; для них ownership подтверждается digest прежнего списка.
Отсутствующий, подменённый, malformed manifest или marker не разрешает
угадать файлы для удаления/перезаписи. Downgrade отвергается численно по трём
компонентам версии до file/registry changes; same-version repair допустим.
Работающий mapped `Studium.exe` блокирует установку: приложение нужно закрыть
самостоятельно. Installer не принудительно завершает его процессы.

Сборки до этого формата ownership (включая review HEAD `[историческая ссылка опущена]`) не содержат
доказуемого списка установленных файлов. Обновление поверх них отвергается:
в disposable QA профиле сначала выполнить их штатный uninstall, проверить
сохранность synthetic data, затем поставить новый installer. Это одноразовое
ограничение перехода для предварительных сборок; будущие сборки со списком
обновляются поверх установленной версии. Не удалять data root для перехода.

`check_windows_bundle.py` допускает Windows native libraries, standard library
archive, Qt translations, **точные** migration/help resources и один
vendor TXT (`setuptools/_vendor/jaraco/text/Lorem ipsum.txt`) и фиксированный
набор wheel metadata MarkupSafe, сверенные побайтово с установленными locked
dependencies. SQLite/sidecars, FileAsset directories, backups, exports, logs,
settings, `.env`, отдельные документы/картинки и неизвестные ресурсы
останавливают сборку. Ничего не удаляется молча ради успешного аудита.
Тестовые БД и smoke helpers в payload не входят. ISCC получает точный список
проверенных файлов без wildcard рабочей копии.

Это проверка состава и известных опасных входов, а не антивирус или
универсальный определитель персональных данных внутри DLL, compiled Python
или исходной статьи. Release build требует проверенного source commit
и locked dependencies без реальных материалов. После установки сравните
payload manifest с программными файлами по [checklist](windows-installer-smoke-tests.md).

## Передача небольшой группе

Перед передачей выполните Windows checklist, зафиксируйте commit, версию,
Windows build, результаты и SHA-256. Для upgrade нужен реальный более новый
build, а не переименованный EXE.

Отправьте EXE через согласованную закрытую ссылку или приватное вложение.
Передайте hash по отдельному доверенному каналу и краткие release notes
с изменениями, ограничениями и способом сообщить ошибку. Не отправляйте
checkout, onedir, свой data root, архив БД или настройки. Payload manifest
оставьте в локальном журнале разработчика. Приватность репозитория сохраняется.

## Установка, обновление и удаление

1. Получите EXE, проверьте источник и контрольную сумму. Закройте Studium.
2. Запустите EXE двойным щелчком. По умолчанию выбран русский язык;
   английский доступен дополнительно. Установка для текущего пользователя
   не требует обязательного запуска от администратора.
3. Следуйте мастеру. Default path — `%LOCALAPPDATA%\Programs\Studium`.
   Ярлык создаётся в меню «Пуск»; рабочий стол — необязательная галочка.
4. В конце можно выбрать запуск Studium. Дальше открывайте его через «Пуск».
   Первый запуск создаёт пользовательскую БД в отдельном AppPaths root.

Для обновления закройте приложение, создайте штатный backup через Настройки
и запустите установщик новой версии под **той же Windows-учётной записью**.
Сохраните прежний каталог программы. Постоянный AppId связывает установки;
данные и вложения остаются в прежнем root. Автообновлений нет; downgrade
в beta не поддерживается. Если приложение не удалось закрыть, остановите
установку и сначала завершите работу с ним.

Удаление: Windows «Параметры → Приложения → Установленные приложения → Studium
→ Удалить» (Windows 10: «Приложения и возможности»). Сначала закройте Studium.
Программа и ярлыки удаляются; `%LOCALAPPDATA%\Studium` с БД, originals и
настройками сохраняется. Повторная установка использует сохранённые данные.

Backup/restore сохраняет существующие ограничения: ZIP не зашифрован,
restore создаёт отдельный пустой root и не переключает активную БД.
Текущая реализация требует совпадения версии приложения в backup manifest;
после повышения версии старый архив может быть отклонён. Совместимость
backup между версиями не добавлена установщиком. См.
[backup/recovery](iteration5b-backup-recovery.md).

### Recovery backup предыдущей версии

Verifier сравнивает `app_version` **точно**, даже если schema revision одинакова.
Не редактируйте manifest ZIP ради обхода проверки. Перед upgrade сохраните
штатный проверенный backup, номер версии, hash и доверенный installer этой
совместимой версии. Не рассчитывайте на downgrade текущей установки.

Для recovery используйте отдельную disposable Windows account/VM с совместимой
версией Studium. Активный root новой версии не копируйте туда и не открывайте
старым EXE. Verify старого backup → restore в **новый пустой** root → открыть
только восстановленную копию совместимым приложением → проверить integrity,
facts и attachments. Существующую newer-version БД сохранять отдельно.
Дальнейший переход восстановленной копии на newer версию допускается только
после отдельной проверки поддерживаемого migration/backup workflow.

Native harness проверяет эту границу на synthetic data: archive создаётся
до upgrade совместимым API, после upgrade восстанавливается в пустой root,
его открывают сохранённые audited bytes старого packaged EXE. Исходная
active/newer БД старым EXE не открывается. Это техническая API/packaged проверка;
полная GUI recovery в non-admin VM остаётся пунктом acceptance. Если совместимый
installer/версия отсутствует либо процедура не подтверждена, recovery —
**blocker beta distribution**. Preferences/cache не входят в существующий ZIP;
installer сохраняет preferences активного root, но backup format не расширяет.

## SmartScreen и цифровая подпись

Beta пока **не подписана**. Windows может показывать неизвестного издателя
либо предупреждение SmartScreen о малой репутации. `COLOSSAL-maksik` в
свойствах/списке приложений — метаданные, не криптографическая подпись.

Не отключайте SmartScreen, Defender и другие средства защиты, не добавляйте
исключения и не обходите блокировку. При предупреждении/блокировке остановите
установку и сообщите разработчику версию, hash и безопасный текст сообщения.
Доверенный канал и совпадение hash не отменяют решения защитных средств.

Будущее signing возможно через Inno SignTool и отдельный release pipeline;
AppId сохраняется. Отдельная release-задача должна подписывать application EXE,
setup и uninstaller, включать timestamp и проверку всех подписей, затем считать
SHA-256 окончательного подписанного setup. Подпись не гарантирует немедленного
исчезновения SmartScreen warnings. Ключи/сертификаты здесь не реализованы.

### Build reproducibility

PR workflows используют read-only permissions, SHA-pinned checkout v6.1.0
(Node 24) и `persist-credentials:false`; публикации/signing/deployment нет.
Inno 6.3+ отдельно от Python, фактическая версия видна в compilation log.
Фиксация конкретного Inno release/официального checksum и hash-lock для всех
build wheels оценены как следующий release hardening: они уменьшают drift
runner/tool supply, но не заменяют исправления path/ownership guards.
Сейчас версии Python dependencies сохранены; полные platform-aware
`--require-hashes` locks и загрузка pinned Inno не добавлены без проверенных
Windows wheel/compiler hashes. Для каждой QA сборки записывать фактические
tool versions и окончательный installer hash; `-SkipAppBuild` не доказывает
compiled source provenance.

## SHA-256

Дополнительная проверка файла через PowerShell:

```powershell
Get-FileHash -LiteralPath '.\Studium-Setup-0.1.0.exe' -Algorithm SHA256
```

Сравните все 64 hex-символа с hash разработчика, полученным по доверенному
каналу. Регистр не важен. При расхождении не запускайте файл. SHA-256
подтверждает совпадение bytes, а не подлинность отправителя. Терминал нужен
только для этой дополнительной проверки; приложение работает графически.

## Сообщение об ошибке без персональных данных

Сообщите версию Studium, Windows build/архитектуру, этап ошибки, короткие
шаги на синтетическом примере, ожидаемый и фактический результат. Для проблем
доставки добавьте hash установщика и безопасный текст ошибки.

Не отправляйте SQLite/sidecars, `files/`, backups, exports, preferences,
crash dumps или полный data root. Для screenshot воспроизведите ошибку на
synthetic data, уберите ФИО, работы, переписку, личные окна и account paths.
Installer logs могут содержать username/пути: не пересылайте их целиком;
вручную извлеките и обезличьте нужный фрагмент. Если это невозможно,
достаточно текстового описания.

Cloud/Linux tests не являются Windows acceptance. До заполнения
[checklist](windows-installer-smoke-tests.md), включая real upgrade,
non-admin UX, PDF и backup/restore, beta не считается принятой для распространения.
