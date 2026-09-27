from alembic import command
from sqlalchemy import Engine

from tests.conftest import alembic_config


def test_migrations_match_the_models(engine: Engine) -> None:
    """`alembic check` fails if a model changed without a migration."""
    command.check(alembic_config())
