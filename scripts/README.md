# Команды Studium

Скрипты относятся к Studium: migrations, synthetic demo/preview, local safety,
CI selection, Windows build/installer и smoke contracts. Перед запуском читать
script и выбирать temporary synthetic root; production данные не открывать.

## Safety и tests

check_repository_safety.py: worktree/staged/history/check-identity, stdlib/offline.
ci_plan.py: unknown/code/config changes требуют full/installer; docs-only
изменения допускают lightweight routing без отключения safety.
run_ci_tests.py: fast/full/all/windows, discovery всех collected modules и
fail-closed skip policy. Full tests изолируются по module/process.

## Windows distribution

build_windows.ps1 создаёт onedir; build_installer_windows.ps1 проверяет payload
и компилирует Inno Setup installer. check_windows_bundle.py проверяет version/
resources/private payload. Native smoke_installer_windows.py,
smoke_installer_security_windows.py, smoke_installer_upgrade_windows.py и
packaged scenarios требуют Windows/disposable synthetic account.
Fixture installers не заменяют acceptance настоящей новой версии.
Локальный Linux packaging test не является Windows bundle PASS.

## Данные и preview

migrate.py требует explicit DB path; production schema Alembic v0001–v0010,
без reset/create_all. create_demo_data.py требует новую synthetic directory.
Preview/scenario/smoke scripts создают данные только в temporary profiles;
новые images требуют metadata/OCR/provenance review и material manifest.
Исторический screenshot sanitizer в самостоятельный repo не переносится.
Открытие default viewers и native UI workflows выполняется только в специально
разрешённой synthetic проверке. Source build outputs/logs не публикуются.
