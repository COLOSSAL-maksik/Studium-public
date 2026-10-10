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
- Публичный source repository COLOSSAL-maksik/Studium-public, ветка main.
- All rights reserved, без открытой лицензии; third-party licenses сохраняются.
- Владелец подтвердил право публичного размещения всех 310 текущих материалов,
  созданных для проекта с помощью ChatGPT без сторонних изображений/дизайнов.
- Migration assertions используют frozen SHA-256 raw bytes без старой Git history.

Технические product ADR/OPEN — в [docs/decisions](../decisions.md).
Windows/manual acceptance и unfinished integration work не закрываются
этими решениями. Source-specific operational records в public docs не включаются.
