# Roadmap Studium

Существующее приложение: локальные учебные факты, persistence, file storage,
ручные Q&A, factual analytics, workspace workflows, backup/recovery и отчёты.
Сохраняются migrations/resources/Windows distribution contracts.

Текущий scope — независимый source repo и чистая история. Далее: устранить
зависимость historical tests от Git объектов, проверить Windows acceptance,
license/material права, отдельно подключить remote и required CI.

Bender — отдельная разработка Jules. Independent bootstrap предшествует
integration; будущий локальный JSON-RPC 2.0 stdio API/client принимается отдельно.
API/solvers/GUI не являются условием source migration. Cloud/server/sync/mobile/
AI и новые integrations требуют отдельного задания, без назначенной даты.
