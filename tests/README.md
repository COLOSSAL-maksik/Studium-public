# Проверки Studium

Suite содержит unit, database и integration tests Studium. Bender tests и
его root conftest отсутствуют. Existing tests используют synthetic fixtures,
temporary SQLite/file roots и изоляцию LOCALAPPDATA до collection.

```text
python scripts/run_ci_tests.py --phase fast
python scripts/run_ci_tests.py --phase full
python scripts/run_ci_tests.py --phase windows
```

Fast/full partitions вместе покрывают collected tests без пересечений.
Новые категории не теряются: unknown modules входят в full. Windows marked
tests на Linux имеют явный platform skip; другие skips fail CI. Каждый full
module получает отдельный процесс, QApplication и временный профиль.
Выносить bytecode/cache/temp/build outputs за source tree либо отключать caches.

Три historical migration immutability assertions используют frozen fixture
`tests/fixtures/migration_hashes.json`: 10 проверенных SHA-256 сравниваются
с `SHA-256(read_bytes())`, без CRLF/LF или Unicode-нормализации.
Fixtures не генерируются во время тестов. Исходная Git history тестам не нужна;
все 18 migration payloads сохраняются побайтово. Остальные preservation/
backup/recovery сценарии проверяют реальные synthetic databases.
Недоступные проверки не объявлять PASS.
Native Windows installer/manual acceptance выполняются отдельно, не в Linux.
