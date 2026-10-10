# Действующие решения Studium

- Windows-first local/offline PySide6; SQLAlchemy/Alembic/SQLite persistence.
- Domain/application contracts не получают ORM/UI/transport dependency.
- UUID/UTC, immutable факты попыток/сообщений, revision и additive migrations.
- Managed immutable file originals вне Git; derived analytics не меняют факты.
- Отдельные Studium и Bender repo с новыми независимыми histories.
- Первый Bender transport JSON-RPC 2.0 over stdio; HTTP допускается позднее.
- Jules пишет Bender implementation/tests/packaging/CI/API; Codex Studium/client.
- Repo migration до API/solvers/GUI; integration отдельным последующим этапом.
- Required safety/quality приоритетны; обязательный второй reviewer отдельно.

Технические product ADR/OPEN — в [docs/decisions](../decisions.md).
License/remote names, Windows/manual acceptance и unfinished work не закрываются
этими решениями. Source-specific operational records в public docs не включаются.
