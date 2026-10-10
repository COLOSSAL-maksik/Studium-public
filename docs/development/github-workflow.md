# Разработка Studium

Локальный исходный bootstrap не создаёт remote и не запускает Actions.
Публичный repository: COLOSSAL-maksik/Studium-public, ветка main.
Первый push проверенного source bundle выполняет владелец; перед ним Actions
отключаются. После первого push настроить main: PR required, force-push и
deletion запрещены. Required checks закрепить после успешных запусков,
отдельно разрешённых владельцем; отсутствующие checks не требовать.
После подключения независимого repo: task branch → PR → safety/quality checks
→ review → отдельно разрешённый merge. Force push и deletion main запрещены.
Второй reviewer/CODEOWNERS обсуждаются отдельно; single-owner проект не должен
зависеть от отсутствующего reviewer. Branch protection настраивается позднее.

Проверки: stdlib safety checker worktree/staged/history/identity, Ruff,
раздельные fast/full pytest и Windows-sensitive/installer contracts.
scripts/ci_plan.py рассматривает неизвестные code/config paths консервативно;
docs-only routing не выключает safety. Unknown tests discovery сохраняется.
Workflows здесь — source configs, не доказательство GitHub CI PASS.

Каждая задача имеет свой scope и branch. Проверять actual heads, не затирать
чужие изменения. Bender implementation и инфраструктура изменяются только
Jules в отдельном repo; переход текущих задач требует отдельного учёта работы.
Runtime/student data, secrets, private inventories и logs не передаются агентам.
