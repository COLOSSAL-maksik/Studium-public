from alembic import context

from studium.infrastructure.database.models import Base


def run_migrations() -> None:
    connection = context.config.attributes.get("connection")
    if connection is None or context.is_offline_mode():
        raise RuntimeError("Use upgrade_database(engine) with the Studium connection policy")
    context.configure(connection=connection, target_metadata=Base.metadata, render_as_batch=True)
    with context.begin_transaction():
        context.run_migrations()


run_migrations()
