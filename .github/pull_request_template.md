## Изменение и причина

Опишите trigger, итоговое поведение и scope. Без private данных или task metadata.

## Проверки

Укажите exact head, safety/quality, relevant pytest/Ruff/package и NOT RUN.
Native Windows/manual acceptance учитывайте отдельно. Required CI checks
приоритетны; второй reviewer согласуется владельцем отдельно.

## Данные и риски

Меняются ли schema/resources/installer? Как сохраняются данные и выполняется rollback?
Используйте только synthetic fixtures. Не прикладывайте production logs/storage.
