"""Regression for CI bypasses and coverage of modules added by concurrent PRs."""

import subprocess
import sys
from pathlib import Path

import pytest

from scripts.ci_plan import plan
from scripts.run_ci_tests import ROOT, select


@pytest.mark.parametrize(
    "paths,full,installer",
    [
        (["README.md", "docs/management/BACKLOG.md"], False, False),
        ([".github/pull_request_template.md"], False, False),
        (["src/studium/domain/entities.py"], True, True),
        (["src/studium/presentation/desktop/help_articles/topics.md"], True, True),
        (["src/unknown/new_module.py"], True, True),
        (["tests/new_kind/test_future.py", "docs/design.md"], True, True),
        (["src/unknown/new_module.py", "requirements-dev.lock"], True, True),
        (["src/unknown/new_module.py", "src/studium/composition.py"], True, True),
        (["pyproject.toml"], True, True),
        ([".github/workflows/quality.yml"], True, True),
        (["scripts/ci_plan.py"], True, True),
        (["docs/security/policy.json"], True, True),
        (["new_unknown_directory/config.yml"], True, True),
        (["src/studium/infrastructure/database/migrations/new.sql"], True, True),
        (["docs/old.md", "src/new.py"], True, True),
        ([], True, True),
    ],
)
def test_routing_never_treats_executable_or_unknown_changes_as_documentation(
    paths, full, installer
):
    assert plan(paths) == {"full": full, "installer": installer}


def test_fast_and_full_cover_every_collected_node_once_including_new_categories():
    items = [
        ("tests/unit/test_domain.py", "domain-case", False),
        ("tests/new_area/unit/test_new.py", "new-unit", False),
        ("tests/new_area/architecture/test_new.py", "new-architecture", False),
        ("tests/future_category/test_new.py", "future-category", False),
        ("tests/new_directory/test_new.py", "unknown-new", False),
        ("tests/integration/test_native.py", "new-native", True),
    ]
    fast = {node for nodes in select(items, "fast").values() for node in nodes}
    full = {node for nodes in select(items, "full").values() for node in nodes}
    assert not fast & full
    assert fast | full == {node for _, node, _ in items}
    assert select(items, "windows") == {"tests/integration/test_native.py": ["new-native"]}


def test_an_unmarked_skip_fails_the_ci_worker(tmp_path):
    source = tmp_path / "test_synthetic_skip.py"
    source.write_text("import pytest\ndef test_hidden():\n    pytest.skip('Synthetic skip')\n")
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts/run_ci_tests.py"), "--worker", str(source)],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert result.returncode == 1, result.stdout + result.stderr
    assert "CI refuses unexpected skips" in result.stdout


def test_rename_from_docs_into_code_is_classified_using_both_paths(tmp_path):
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "old.md").write_text("Synthetic content")
    subprocess.run(["git", "-C", str(tmp_path), "add", "."], check=True)
    subprocess.run(
        [
            "git",
            "-C",
            str(tmp_path),
            "-c",
            "user.name=Synthetic",
            "-c",
            "user.email=synthetic@example.test",
            "commit",
            "-qm",
            "Synthetic baseline",
        ],
        check=True,
    )
    before = subprocess.check_output(
        ["git", "-C", str(tmp_path), "rev-parse", "HEAD"], text=True
    ).strip()
    (tmp_path / "src").mkdir()
    (docs / "old.md").rename(tmp_path / "src/new.py")
    subprocess.run(["git", "-C", str(tmp_path), "add", "."], check=True)
    subprocess.run(
        [
            "git",
            "-C",
            str(tmp_path),
            "-c",
            "user.name=Synthetic",
            "-c",
            "user.email=synthetic@example.test",
            "commit",
            "-qm",
            "Synthetic rename",
        ],
        check=True,
    )
    result = subprocess.run(
        [sys.executable, str(Path(ROOT, "scripts/ci_plan.py")), "--base", before],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=True,
    )
    assert result.stdout.splitlines() == ["full=true", "installer=true"]
