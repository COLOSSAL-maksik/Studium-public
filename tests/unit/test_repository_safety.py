"""Disposable repos for mutations; the project's history is only read, never rewritten."""

import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
from sqlalchemy import text
from sqlalchemy.exc import OperationalError

from studium.application.errors import ApplicationError
from studium.composition import create_runtime
from studium.infrastructure.database.session import create_database_engine
from studium.infrastructure.file_storage import LocalFileStorage
from studium.infrastructure.user_data import AppPaths, data_directory
from tests import conftest

PROJECT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location(
    "repository_safety", PROJECT / "scripts/check_repository_safety.py"
)
safety = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = safety
spec.loader.exec_module(safety)

DEV_NAME = "Maksim"
DEV_EMAIL = "maksim" + "@" + "local.dev"
DEV_TRAILER = f"Co-authored-by: {DEV_NAME} <{DEV_EMAIL}>"
GITHUB_NAME = "COLOSSAL-maksik"
GITHUB_EMAIL = "328697613+" + GITHUB_NAME + "@" + "users.noreply.github.com"
GITHUB_TRAILER = f"Co-authored-by: {GITHUB_NAME} <{GITHUB_EMAIL}>"


def identity_document(name=DEV_NAME, email=DEV_EMAIL):
    return {"version": 1, "identities": [{"name": name, "email": email}]}


def approved_identity_policy():
    return {"approved_git_identities": safety.parse_identity_policy(identity_document())}


def multi_identity_document():
    return {
        "version": 1,
        "identities": [
            {"name": DEV_NAME, "email": DEV_EMAIL},
            {"name": GITHUB_NAME, "email": GITHUB_EMAIL},
        ],
    }


def write_identity_policy(root, document=None):
    path = root / safety.IDENTITY_POLICY
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(document or identity_document(), indent=2) + "\n", encoding="utf8")


@pytest.fixture
def git_repo(tmp_path):
    root = tmp_path / "repo"
    root.mkdir()
    safety.git(root, "init", "-q")
    safety.git(root, "config", "user.name", "Synthetic Author")
    safety.git(root, "config", "user.email", "author@example.test")
    return root


@pytest.mark.parametrize(
    "name",
    [
        "data/roster.csv",
        "files/id.txt",
        "runtime/one.json",
        "nested/.env",
        "x.sqlite-wal",
        "x.db-shm",
        "x.sqlite3-journal",
        "student-backup.zip",
        "config.local.json",
        "private.pem",
        "note.log",
        "crash.dmp",
    ],
)
def test_forbidden_staged_artifacts_are_rejected(git_repo, name):
    path = git_repo / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("synthetic", encoding="utf8")
    safety.git(git_repo, "add", name)
    findings, stats = safety.scan_tree(git_repo, staged=True)
    assert findings and stats["files_checked"] == 1


def test_staged_scan_uses_index_even_if_working_copy_was_sanitized(git_repo):
    token = "ghp_" + "A" * 36
    (git_repo / "settings.txt").write_text(token, encoding="utf8")
    safety.git(git_repo, "add", "settings.txt")
    (git_repo / "settings.txt").write_text("safe", encoding="utf8")
    findings, _ = safety.scan_tree(git_repo, staged=True)
    assert any(f.rule == "github-token" for f in findings)
    assert token not in json.dumps([vars(f) for f in findings])


def test_secret_and_sqlite_magic_are_detected_under_innocent_filenames():
    findings = safety.check_content("notes.txt", b"SQLite format 3\0synthetic", {})
    assert any(f.rule == "sqlite-content" for f in findings)
    for value in [
        "sk-" + "a" * 40,
        "-----BEGIN " + "PRIVATE KEY-----",
        'password="' + "randomvalue12345" + '"',
    ]:
        assert safety.scan_text("source.py", value)
    assert not safety.scan_text(".env.example", 'API_KEY="placeholder"\n')
    assert safety.scan_text(".env.example", "ACCESS_TOKEN=" + "arbitrary-secret-value")


def test_source_directories_and_placeholder_config_are_allowed():
    for path in [
        "src/studium/infrastructure/database/session.py",
        "tests/fixtures/example.txt",
        "Studium.spec",
        ".env.example",
    ]:
        assert safety.forbidden_path(path) is None
    assert not safety.check_content(".env.example", b"OPENAI_API_KEY=\n", {})
    assert not safety.scan_text(".env.example", "OPENAI_API_KEY=\nGEMINI_API_KEY=\n")
    assert not safety.scan_text("example.md", 'API_KEY=\n"unrelated explanatory text"\n')


def test_changed_binary_needs_exact_reviewed_digest():
    blob = b"\x89PNG\0synthetic"
    digest = safety.hashlib.sha256(blob).hexdigest()
    policy = {"artifacts": {"docs/screenshot.png": {"sha256": [digest]}}}
    assert not safety.check_content("docs/screenshot.png", blob, policy)
    assert safety.check_content("docs/screenshot.png", blob + b"changed", policy)


def test_history_checks_deleted_files_and_tree_refs(git_repo):
    (git_repo / "old.sqlite").write_bytes(b"SQLite format 3\0synthetic")
    safety.git(git_repo, "add", ".")
    safety.git(git_repo, "commit", "-qm", "synthetic first")
    safety.git(git_repo, "rm", "old.sqlite")
    safety.git(git_repo, "commit", "-qm", "synthetic second")
    (git_repo / "notes.txt").write_text("sk-" + "b" * 40, encoding="utf8")
    safety.git(git_repo, "add", ".")
    tree = safety.git(git_repo, "write-tree").decode().strip()
    safety.git(git_repo, "update-ref", "refs/synthetic/tree", tree)
    findings, stats = safety.scan_history(git_repo)
    assert stats["commits"] == 2
    assert any(f.path == "old.sqlite" and f.rule == "sqlite-content" for f in findings)
    assert any(f.path == "notes.txt" and f.rule == "api-token" for f in findings)


@pytest.mark.parametrize("trailer", sorted(safety.IDENTITY_TRAILERS))
def test_exact_approved_identity_in_standard_final_trailer(trailer):
    message = f"Subject\n\n{trailer}: {DEV_NAME} <{DEV_EMAIL}>\n"
    assert not safety.scan_commit_message(message, approved_identity_policy())


def test_approved_trailer_allows_syntax_whitespace_and_crlf():
    message = f"Subject\r\n\r\nCO-AUTHORED-BY:  {DEV_NAME} <{DEV_EMAIL}> \t\r\n"
    assert not safety.scan_commit_message(message, approved_identity_policy())


@pytest.mark.parametrize(
    ("name", "email"),
    [
        ("Another Name", DEV_EMAIL),
        ("maksim", DEV_EMAIL),
        (DEV_NAME, "another-person" + "@" + "local.dev"),
        (DEV_NAME, "unknown" + "@" + "company.org"),
        (DEV_NAME, "Maksim" + "@" + "local.dev"),
    ],
)
def test_unapproved_name_or_email_in_trailer_is_reviewed(name, email):
    message = f"Subject\n\nCo-authored-by: {name} <{email}>\n"
    findings = safety.scan_commit_message(message, approved_identity_policy(), "synthetic-oid")
    assert any(f.rule == "email-review" and f.severity == "review" for f in findings)
    assert all(f.object_id == "synthetic-oid" and f.line == 3 for f in findings)


@pytest.mark.parametrize(
    "message",
    [
        f"Contact {DEV_EMAIL}",
        f"Subject\n\n> {DEV_TRAILER}",
        f"Subject\n\nExample: {DEV_TRAILER}",
        f"Subject\n\nContact: {DEV_NAME} <{DEV_EMAIL}>",
        f"Subject\n\n{DEV_TRAILER} extra text",
        f"Subject\n\n{DEV_TRAILER} another-person" + "@" + "local.dev",
    ],
)
def test_approved_email_outside_exact_identity_trailer_is_reviewed(message):
    findings = safety.scan_commit_message(message, approved_identity_policy())
    assert any(f.rule == "email-review" for f in findings)


def test_squash_commit_approved_identity_mid_and_final():
    message = f"Subject\n\n{DEV_TRAILER}\n\nMore body text\n\n{DEV_TRAILER}\n"
    findings = safety.scan_commit_message(message, approved_identity_policy())
    assert not any(f.rule == "email-review" for f in findings)


def test_approved_trailer_does_not_hide_email_elsewhere_in_message():
    message = f"Subject\n\nContact: {DEV_EMAIL}\n{DEV_TRAILER}\n"
    findings = safety.scan_commit_message(message, approved_identity_policy())
    assert [f.line for f in findings if f.rule == "email-review"] == [3]


@pytest.mark.parametrize("name", ["README.md", "src/example.py", "user-content.txt"])
@pytest.mark.parametrize("staged", [False, True])
@pytest.mark.parametrize("content", [DEV_EMAIL, DEV_TRAILER, GITHUB_EMAIL, GITHUB_TRAILER])
def test_approved_identity_email_in_tracked_files_still_fails(git_repo, name, staged, content):
    write_identity_policy(git_repo, multi_identity_document())
    path = git_repo / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf8")
    safety.git(git_repo, "add", ".")
    findings, _ = safety.scan_tree(git_repo, staged=staged, worktree=not staged)
    assert any(f.path == name and f.rule == "email-review" for f in findings)
    mode = "--staged" if staged else "--worktree"
    assert safety.main(["--root", str(git_repo), mode]) == 1


def test_missing_or_empty_identity_policy_does_not_approve_trailers(git_repo):
    message = f"Subject\n\n{DEV_TRAILER}\n"
    for document in [None, {"version": 1, "identities": []}]:
        if document is not None:
            write_identity_policy(git_repo, document)
        assert safety.scan_commit_message(message, safety.load_policy(git_repo))


def test_identity_policy_is_read_from_index_for_staged_scan(git_repo):
    write_identity_policy(git_repo)
    safety.git(git_repo, "add", ".")
    write_identity_policy(git_repo, {"version": 1, "identities": []})
    assert safety.load_policy(git_repo, staged=True) == approved_identity_policy()
    assert not safety.scan_tree(git_repo, staged=True)[0]
    assert safety.scan_commit_message(f"Subject\n\n{DEV_TRAILER}", safety.load_policy(git_repo))


def test_identity_policy_cannot_follow_symlink_outside_checkout(git_repo):
    target = git_repo.parent / "outside-policy.json"
    target.write_text(json.dumps(identity_document()), encoding="utf8")
    path = git_repo / safety.IDENTITY_POLICY
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        path.symlink_to(target)
    except (NotImplementedError, OSError):
        pytest.skip("Symlinks unavailable on this host")
    with pytest.raises(ValueError, match="Policy must stay inside"):
        safety.load_policy(git_repo)


@pytest.mark.parametrize(
    "document",
    [
        {"version": 2, "identities": []},
        {"version": True, "identities": []},
        {"version": 1, "identities": "local.dev"},
        {**identity_document(), "body": DEV_EMAIL},
        identity_document(email="*" + "@" + "local.dev"),
        identity_document(email="local.dev"),
        identity_document(name=f"Unknown <{DEV_EMAIL}>"),
        identity_document(name=""),
    ],
)
def test_identity_policy_rejects_broad_or_malformed_approvals(git_repo, document):
    write_identity_policy(git_repo, document)
    with pytest.raises(ValueError):
        safety.load_policy(git_repo)
    assert safety.main(["--root", str(git_repo), "--worktree"]) == 2


def test_historical_policy_cannot_approve_itself_against_current_policy():
    document = identity_document(email="another-person" + "@" + "local.dev")
    findings = safety.check_content(
        safety.IDENTITY_POLICY, json.dumps(document).encode(), approved_identity_policy()
    )
    assert any(f.rule == "email-review" for f in findings)
    assert any(f.rule == "unapproved-git-identity-policy" for f in findings)


@pytest.mark.parametrize(
    ("rule", "secret"),
    [
        ("github-token", "ghp_" + "A" * 36),
        ("api-token", "sk-" + "b" * 40),
        ("private-key", "-----BEGIN " + "PRIVATE KEY-----"),
        ("literal-credential", 'password="' + "randomvalue12345" + '"'),
        ("env-credential", "ACCESS_TOKEN=" + "arbitrary-secret-value"),
    ],
)
def test_approved_trailer_preserves_secret_rules(rule, secret):
    message = f"Subject\n\n{secret}\n\n{DEV_TRAILER}\n"
    findings = safety.scan_commit_message(message, approved_identity_policy())
    assert any(f.rule == rule and f.severity == "error" for f in findings)
    assert not any(f.rule == "email-review" for f in findings)
    assert secret not in repr(findings)


def test_secret_rules_still_scan_approved_identity_name_and_policy():
    name = "ghp_" + "C" * 36
    policy = {"approved_git_identities": safety.parse_identity_policy(identity_document(name=name))}
    message = f"Subject\n\nCo-authored-by: {name} <{DEV_EMAIL}>"
    for findings in [
        safety.scan_commit_message(message, policy),
        safety.check_content(
            safety.IDENTITY_POLICY, json.dumps(identity_document(name=name)).encode(), policy
        ),
    ]:
        assert any(f.rule == "github-token" for f in findings)


def test_history_accepts_approved_trailer_and_identity_policy(git_repo):
    write_identity_policy(git_repo)
    safety.git(git_repo, "add", ".")
    safety.git(git_repo, "commit", "-qm", f"Subject\n\n{DEV_TRAILER}")
    assert not safety.scan_history(git_repo)[0]
    assert safety.main(["--root", str(git_repo), "--history"]) == 0


def test_history_accepts_multiple_identities_and_previous_policy(git_repo):
    write_identity_policy(git_repo)
    safety.git(git_repo, "add", ".")
    safety.git(git_repo, "commit", "-qm", f"Subject\n\n{DEV_TRAILER}\n{GITHUB_TRAILER}")
    write_identity_policy(git_repo, multi_identity_document())
    safety.git(git_repo, "add", ".")
    assert not safety.scan_tree(git_repo, staged=True)[0]
    assert not safety.scan_tree(git_repo, worktree=True)[0]
    safety.git(git_repo, "commit", "-qm", f"Subject\n\n{DEV_TRAILER}\n{GITHUB_TRAILER}")
    assert not safety.scan_history(git_repo)[0]
    assert safety.main(["--root", str(git_repo), "--history"]) == 0


@pytest.mark.parametrize(
    ("name", "email"),
    [
        (DEV_NAME, GITHUB_EMAIL),
        (GITHUB_NAME, DEV_EMAIL),
        (GITHUB_NAME.lower(), GITHUB_EMAIL),
        (GITHUB_NAME, GITHUB_EMAIL.lower()),
        (GITHUB_NAME, "another-person" + "@" + "users.noreply.github.com"),
    ],
)
def test_multiple_approved_identities_require_exact_pairs(name, email):
    policy = {"approved_git_identities": safety.parse_identity_policy(multi_identity_document())}
    findings = safety.scan_commit_message(f"Subject\n\nCo-authored-by: {name} <{email}>", policy)
    assert any(f.rule == "email-review" and f.severity == "review" for f in findings)


@pytest.mark.parametrize(
    "email",
    [
        DEV_EMAIL,
        GITHUB_EMAIL,
        "another-person" + "@" + "local.dev",
        "unknown" + "@" + "company.org",
    ],
)
def test_history_still_reviews_deleted_ordinary_email_content(git_repo, email):
    write_identity_policy(git_repo, multi_identity_document())
    (git_repo / "README.md").write_text(email, encoding="utf8")
    safety.git(git_repo, "add", ".")
    safety.git(git_repo, "commit", "-qm", f"Subject\n\n{DEV_TRAILER}")
    safety.git(git_repo, "rm", "README.md")
    safety.git(git_repo, "commit", "-qm", "Remove synthetic content")
    findings, _ = safety.scan_history(git_repo)
    assert any(f.path == "README.md" and f.rule == "email-review" for f in findings)
    assert safety.main(["--root", str(git_repo), "--history"]) == 1


def test_current_repository_history_passes_with_approved_identity_policy():
    findings, stats = safety.scan_history(PROJECT)
    assert stats["commits"] > 0
    assert not findings


@pytest.mark.parametrize("git_marker_is_file", [False, True])
def test_all_runtime_entry_points_reject_checkout(git_repo, git_marker_is_file):
    if git_marker_is_file:
        root = git_repo.parent / "worktree"
        root.mkdir()
        (root / ".git").write_text("gitdir: synthetic", encoding="utf8")
    else:
        root = git_repo
    target = root / "nested/data"
    for action in [
        lambda: data_directory(target),
        lambda: AppPaths(target),
        lambda: create_runtime(target),
        lambda: LocalFileStorage(target),
        lambda: create_database_engine(target / "hidden.sqlite"),
    ]:
        with pytest.raises(ApplicationError, match="unsafe_data_directory"):
            action()
    assert not target.exists()


def test_normal_suite_default_never_resolves_production(tmp_path):
    paths = AppPaths.resolve()
    assert paths.root == tmp_path / "profile/Studium"
    assert not paths.root.is_relative_to(conftest._production_root)
    for path in [
        paths.database_path,
        paths.files_dir,
        paths.cache_dir,
        paths.logs_dir,
        paths.backups_dir,
        paths.exports_dir,
        paths.temp_dir,
    ]:
        assert path.is_relative_to(paths.root)
    with pytest.raises(RuntimeError, match="production Studium storage"):
        open(conftest._production_root / "must-never-open.txt", "rb")


def test_database_exception_does_not_render_bound_student_text(tmp_path):
    engine = create_database_engine(tmp_path / "synthetic.sqlite")
    try:
        with engine.connect() as connection:
            with pytest.raises(OperationalError) as error:
                connection.execute(
                    text("SELECT :student FROM missing_table"),
                    {"student": "Synthetic private diagnostic marker"},
                )
        assert "Synthetic private diagnostic marker" not in str(error.value)
        assert "missing_table" in str(error.value)
    finally:
        engine.dispose()


def test_env_and_runtime_files_are_ignored_by_real_ignore_rules(git_repo):
    (git_repo / ".gitignore").write_bytes((PROJECT / ".gitignore").read_bytes())
    for name in [
        ".env",
        ".env.secret",
        "a.sqlite",
        "a.sqlite-wal",
        "nested/b.db-shm",
        "files/id.txt",
        "cache/thumb.png",
        "exports/report.csv",
        "crash.dmp",
    ]:
        assert safety.git(git_repo, "check-ignore", name).strip()
    assert (
        subprocess.run(
            ["git", "-C", str(git_repo), "check-ignore", ".env.example"], capture_output=True
        ).returncode
        == 1
    )


def test_actual_precommit_hook_blocks_commit(git_repo):
    safety.git(git_repo, "config", "core.hooksPath", str(PROJECT / ".githooks"))
    (git_repo / "bad.sqlite").write_bytes(b"SQLite format 3\0synthetic")
    # Hook is portable; fixture repo supplies the project checker without source imports.
    (git_repo / "scripts").mkdir()
    (git_repo / "scripts/check_repository_safety.py").write_bytes(
        (PROJECT / "scripts/check_repository_safety.py").read_bytes()
    )
    safety.git(git_repo, "add", ".")
    env = dict(os.environ, PATH=str(Path(sys.executable).parent) + os.pathsep + os.environ["PATH"])
    result = subprocess.run(
        ["git", "-C", str(git_repo), "commit", "-m", "must be blocked"],
        env=env,
        capture_output=True,
    )
    assert result.returncode != 0 and b"sqlite-content" in result.stdout + result.stderr
    assert (
        subprocess.run(
            ["git", "-C", str(git_repo), "rev-parse", "--verify", "HEAD"], capture_output=True
        ).returncode
        != 0
    )


@pytest.mark.parametrize(
    "name", ["studium_output.txt", "nested/pytest-output.txt", "test_results.txt"]
)
def test_force_added_raw_logs_fail_even_when_empty(git_repo, name):
    path = git_repo / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("", encoding="utf8")
    safety.git(git_repo, "add", "-f", name)
    assert any(f.rule == "raw-test-log" for f in safety.scan_tree(git_repo, staged=True)[0])


def test_raw_log_history_exception_does_not_allow_reintroduction_or_changed_bytes():
    path = "studium_output.txt"
    data = b"synthetic old test output"
    policy = {"historical_raw_logs": {path: safety.hashlib.sha256(data).hexdigest()}}
    assert not safety.check_content(path, data, policy, historical=True)
    assert safety.check_content(path, data, policy)
    assert safety.check_content(path, data + b"changed", policy, historical=True)
    assert safety.check_content("renamed_test_output.txt", data, policy, historical=True)
    assert not safety.check_content("docs/pytest-summary.txt", b"10 passed", {})
    assert safety.check_content("unusual-name.txt", b"Traceback (most recent call last):\n", {})


def test_pending_identity_checks_environment_overrides_and_redacts_values(git_repo, monkeypatch):
    email = "synthetic-private" + "@" + "mail.invalid"
    monkeypatch.setenv("GIT_AUTHOR_NAME", "Synthetic Author")
    monkeypatch.setenv("GIT_AUTHOR_EMAIL", email)
    findings = safety.scan_pending_identity(git_repo)
    assert any(f.path == "<git-author-email>" and f.rule == "email-review" for f in findings)
    assert email not in json.dumps([vars(f) for f in findings])


@pytest.mark.parametrize(
    "email",
    [
        "123+contributor" + "@" + "users.noreply.github.com",
        "123+agent[bot]" + "@" + "users.noreply.github.com",
        "noreply" + "@" + "github.com",
    ],
)
def test_public_contributors_and_bot_headers_need_no_personal_email_allowlist(email):
    assert not safety.scan_identity("Synthetic Author", email, "author", {})


def test_noreply_metadata_cannot_hide_secrets_or_false_domains():
    email = "123+agent" + "@" + "users.noreply.github.com"
    assert safety.scan_identity("ghp_" + "A" * 36, email, "author", {})
    assert safety.scan_identity("Synthetic", email + ".invalid", "author", {})


def test_historical_metadata_record_never_approves_new_commits(git_repo):
    email = "synthetic-private" + "@" + "mail.invalid"
    safety.git(git_repo, "config", "user.email", email)
    (git_repo / "readme.md").write_text("synthetic", encoding="utf8")
    safety.git(git_repo, "add", ".")
    safety.git(git_repo, "commit", "-qm", "old synthetic commit")
    old = safety.git(git_repo, "rev-parse", "HEAD").decode().strip()
    metadata = safety.git(git_repo, "show", "-s", "--format=%an%x00%ae%x00%cn%x00%ce", old)
    review = {
        "version": 1,
        "legacy_contact_metadata": {old: safety.hashlib.sha256(metadata).hexdigest()},
        "historical_raw_logs": {},
    }
    path = git_repo / safety.HISTORY_REVIEW
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(review), encoding="utf8")
    findings, stats = safety.scan_history(git_repo)
    assert not findings and stats["legacy_contact_commits"] == [old]
    safety.git(git_repo, "commit", "--allow-empty", "-qm", "new synthetic commit")
    new = safety.git(git_repo, "rev-parse", "HEAD").decode().strip()
    findings, _ = safety.scan_history(git_repo)
    assert any(f.rule == "email-review" and f.object_id == new for f in findings)
    review["legacy_contact_metadata"][old] = "0" * 64
    path.write_text(json.dumps(review), encoding="utf8")
    assert any(f.object_id == old for f in safety.scan_history(git_repo)[0])


def test_historical_review_rejects_wildcard_approvals(git_repo):
    path = git_repo / safety.HISTORY_REVIEW
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {"version": 1, "legacy_contact_metadata": {"*": "0" * 64}, "historical_raw_logs": {}}
        ),
        encoding="utf8",
    )
    with pytest.raises(ValueError):
        safety.load_policy(git_repo)
