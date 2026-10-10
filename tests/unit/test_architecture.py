import ast
from pathlib import Path


def test_dependency_direction():
    root = Path(__file__).resolve().parents[2] / "src/studium"
    forbidden = {
        "domain": {
            "PySide6",
            "sqlalchemy",
            "alembic",
            "fastapi",
            "sqlite3",
            "pydantic",
            "studium.infrastructure",
            "studium.presentation",
        },
        "application": {
            "PySide6",
            "sqlalchemy",
            "alembic",
            "sqlite3",
            "studium.infrastructure",
            "studium.presentation",
        },
        "presentation": {"sqlalchemy", "alembic", "sqlite3", "studium.infrastructure.database"},
    }
    for layer, imports in forbidden.items():
        for source in (root / layer).rglob("*.py"):
            for node in ast.walk(ast.parse(source.read_text(encoding="utf-8"))):
                names = (
                    [alias.name for alias in node.names]
                    if isinstance(node, ast.Import)
                    else [node.module or ""]
                    if isinstance(node, ast.ImportFrom)
                    else []
                )
                assert not any(
                    name == blocked or name.startswith(blocked + ".")
                    for name in names
                    for blocked in imports
                ), source
