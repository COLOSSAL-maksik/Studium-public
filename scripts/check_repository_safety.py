"""Offline repository gate. Stdlib only; findings never include matched secret values."""

import argparse
import hashlib
import io
import json
import re
import subprocess
import sys
import zipfile
from dataclasses import asdict, dataclass
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]
POLICY = "docs/security/approved-artifacts.json"
IDENTITY_POLICY = "docs/security/approved-git-identities.json"
HISTORY_REVIEW = "docs/security/reviewed-history.json"
# Existing findings are recorded to prevent regressions, not to approve public disclosure.
NOREPLY = re.compile(
    r"(?:[A-Za-z0-9+_.\[\]-]+@(?:users\.)?noreply\.github\.com|noreply@github\.com)", re.ASCII
)
RAW_LOG_NAME = re.compile(
    r"(?:studium_(?:output|test_out|test_output|tests)|"
    r"(?:.*[_-])?(?:pytest|test|tests)[_-](?:out(?:put)?|logs?|results?))\.txt",
    re.IGNORECASE,
)
RAW_LOG_TEXT = re.compile(
    r"(?m)^(?:=+ test session starts =+|Traceback \(most recent call last\):)$"
)
IDENTITY_TRAILERS = {
    "co-authored-by",
    "signed-off-by",
    "acked-by",
    "reviewed-by",
    "tested-by",
    "reported-by",
    "suggested-by",
}
TRAILER = re.compile(r"([A-Za-z][A-Za-z0-9-]*):[ \t]+(.+)")
GIT_IDENTITY = re.compile(r"([^<>\r\n]+) <([^<>\r\n]+)>")
RUNTIME_ROOTS = {
    "data",
    "runtime",
    "storage",
    "files",
    "cache",
    "logs",
    "backups",
    "exports",
    "tmp",
    "temp",
    "local-data",
    "user-data",
    "attachments",
    ".secrets",
    "secrets",
    ".venv",
    "venv",
    "build",
    "dist",
    ".idea",
    ".vscode",
    ".vs",
    ".pytest_cache",
    ".ruff_cache",
    "htmlcov",
}
PRIVATE_SUFFIXES = {
    ".db",
    ".sqlite",
    ".sqlite3",
    ".sqlitedb",
    ".dump",
    ".log",
    ".bak",
    ".dmp",
    ".mdmp",
    ".stackdump",
    ".pem",
    ".key",
    ".p12",
    ".pfx",
    ".jks",
    ".keystore",
    ".local",
    ".tmp",
    ".temp",
    ".pyc",
    ".pyo",
}
REVIEW_SUFFIXES = {
    ".png",
    ".jpg",
    ".jpeg",
    ".webp",
    ".gif",
    ".bmp",
    ".tif",
    ".tiff",
    ".pdf",
    ".doc",
    ".docx",
    ".xlsx",
    ".pptx",
    ".odt",
    ".ods",
    ".odp",
    ".zip",
    ".7z",
    ".tar",
    ".gz",
    ".rar",
    ".bin",
    ".exe",
    ".dll",
}
PLACEHOLDERS = re.compile(
    r"(?i)^(?:|test|dummy|example|placeholder|changeme|replace_me|your[_ -].*|"
    r"\$\{.*\}|<.*>|synthetic.*|not[_ -]a[_ -].*)$"
)
TOKEN_RULES = (
    ("private-key", re.compile(r"-----BEGIN (?:[A-Z]+ )?PRIVATE KEY-----")),
    (
        "github-token",
        re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,})\b"),
    ),
    ("api-token", re.compile(r"\bsk-(?:proj-|ant-)?[A-Za-z0-9_-]{24,}\b")),
    ("google-key", re.compile(r"\bAIza[A-Za-z0-9_-]{35}\b")),
    ("aws-key", re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b")),
    ("slack-token", re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{20,}\b")),
    ("credential-url", re.compile(r"[a-zA-Z][\w+.-]*://[^\s/:]+:[^\s/@]{8,}@")),
    ("bearer-token", re.compile(r"(?i)\bBearer\s+[A-Za-z0-9_.-]{24,}")),
    ("telegram-token", re.compile(r"\b\d{8,12}:[A-Za-z0-9_-]{35}\b")),
    (
        "webhook-secret",
        re.compile(r"https://hooks\.(?:slack\.com/services|discord\.com/api/webhooks)/[^\s\"']+"),
    ),
)
ASSIGNMENT = re.compile(
    r"(?im)[\"']?\b(?:[A-Z0-9_]*(?:api_key|access_token|auth_token|client_secret|"
    r"password|passwd|secret_key))[\"']?[ \t]*[:=][ \t]*[\"']([^\"'\r\n]{8,})[\"']"
)
ENV_ASSIGNMENT = re.compile(
    r"(?im)^[ \t]*(?:export[ \t]+)?[A-Z0-9_]*(?:API_KEY|ACCESS_TOKEN|AUTH_TOKEN|CLIENT_SECRET|"
    r"PASSWORD|PASSWD|SECRET_KEY)[ \t]*=[ \t]*([^\s\"'#]{8,})[ \t]*\r?$"
)
EMAIL = re.compile(r"\b[\w.+-]+@([\w.-]+\.[A-Za-z]{2,})\b")
PHONE = re.compile(r"\+7[ (.-]*\d{3}[ ).-]*\d{3}[ .-]*\d{2}[ .-]*\d{2}\b")
MACHINE_PATH = re.compile(r"(?i)[A-Z]:[\\/]+Users[\\/]+([^\\/\s\"']+)")


@dataclass(frozen=True)
class Finding:
    path: str
    rule: str
    severity: str = "error"
    line: int | None = None
    object_id: str | None = None


def git(root: Path, *args: str) -> bytes:
    result = subprocess.run(["git", "-C", str(root), *args], capture_output=True, check=True)
    return result.stdout


def forbidden_path(path: str) -> str | None:
    p = PurePosixPath(path.replace("\\", "/").lower())
    name = p.name
    if p.is_absolute() or ".." in p.parts:
        return "unsafe-path"
    if p.parts and p.parts[0] in RUNTIME_ROOTS:
        return "runtime-directory"
    if any(part in {".imports", ".local", ".secrets"} for part in p.parts):
        return "private-directory"
    if "__pycache__" in p.parts or name.startswith("~$"):
        return "temporary-artifact"
    if re.search(r"(?:^|/)files/[0-9a-f]{2}/[0-9a-f-]{36}\.", str(p)):
        return "managed-file-storage"
    if name == ".env" or (name.startswith(".env.") and name != ".env.example"):
        return "private-env"
    if name.startswith(("credentials", "service-account", "config.local.")):
        return "local-credentials"
    if RAW_LOG_NAME.fullmatch(name):
        return "raw-test-log"
    if p.suffix in PRIVATE_SUFFIXES or re.search(r"\.(?:db|sqlite3?|sqlitedb)-", name):
        return "private-artifact"
    if any(word in name for word in ("backup", "back-up")) and p.suffix in {
        ".zip",
        ".7z",
        ".tar",
        ".gz",
    }:
        return "backup-archive"
    return None


def scan_text(path: str, value: str, object_id: str | None = None) -> list[Finding]:
    findings = []
    for rule, pattern in TOKEN_RULES:
        for match in pattern.finditer(value):
            findings.append(
                Finding(
                    path, rule, line=value.count("\n", 0, match.start()) + 1, object_id=object_id
                )
            )
    for match in ASSIGNMENT.finditer(value):
        if not PLACEHOLDERS.fullmatch(match[1]) and not match[1].startswith(
            ("os.environ", "environ.")
        ):
            findings.append(
                Finding(
                    path,
                    "literal-credential",
                    line=value.count("\n", 0, match.start()) + 1,
                    object_id=object_id,
                )
            )
    for match in ENV_ASSIGNMENT.finditer(value):
        if not PLACEHOLDERS.fullmatch(match[1]) and not match[1].startswith(
            ("os.", "environ", "$")
        ):
            findings.append(
                Finding(
                    path,
                    "env-credential",
                    line=value.count("\n", 0, match.start()) + 1,
                    object_id=object_id,
                )
            )
    for match in EMAIL.finditer(value):
        if match[1].lower() not in {
            "example.com",
            "example.org",
            "example.net",
            "example.test",
            "localhost.test",
        }:
            findings.append(
                Finding(
                    path,
                    "email-review",
                    "review",
                    value.count("\n", 0, match.start()) + 1,
                    object_id,
                )
            )
    for match in MACHINE_PATH.finditer(value):
        if match[1].lower() not in {"public", "default", "<user>", "test", "example", "synthetic"}:
            findings.append(
                Finding(
                    path,
                    "machine-user-path",
                    "review",
                    value.count("\n", 0, match.start()) + 1,
                    object_id,
                )
            )
    for match in PHONE.finditer(value):
        findings.append(
            Finding(
                path, "phone-review", "review", value.count("\n", 0, match.start()) + 1, object_id
            )
        )
    return findings


def parse_identity_policy(policy: dict) -> frozenset[tuple[str, str]]:
    """Only explicit name/email pairs; malformed or broad approvals fail closed."""
    if (
        not isinstance(policy, dict)
        or set(policy) != {"version", "identities"}
        or type(policy["version"]) is not int
        or policy["version"] != 1
        or not isinstance(policy["identities"], list)
    ):
        raise ValueError("Invalid Git identity policy")
    identities = set()
    for identity in policy["identities"]:
        if not isinstance(identity, dict) or set(identity) != {"name", "email"}:
            raise ValueError("Invalid Git identity entry")
        name, email = identity["name"], identity["email"]
        if (
            not isinstance(name, str)
            or not name
            or name != name.strip()
            or any(c in name for c in "<>\r\n\t")
            or EMAIL.search(name)
            or not isinstance(email, str)
            or not EMAIL.fullmatch(email)
        ):
            raise ValueError("Git identities require exact names and email addresses")
        identities.add((name, email))
    return frozenset(identities)


def scan_commit_message(value: str, policy: dict, object_id: str | None = None) -> list[Finding]:
    """Approve identity emails only in complete, unquoted Git trailers."""
    findings = scan_text("<commit-message>", value, object_id)
    lines = [line.removesuffix("\r") for line in value.split("\n")]
    approved = policy.get("approved_git_identities", frozenset())
    approved_lines = set()
    for number, line in enumerate(lines, 1):
        trailer = TRAILER.fullmatch(line)
        if not trailer:
            continue
        identity = GIT_IDENTITY.fullmatch(trailer[2].rstrip(" \t"))
        if (
            trailer[1].lower() in IDENTITY_TRAILERS
            and identity
            and (identity[1], identity[2]) in approved
        ):
            approved_lines.add(number)
    # Keep every secret/token/path/phone finding from the original, unmodified message.
    return [f for f in findings if f.rule != "email-review" or f.line not in approved_lines]


def read_policy_json(root: Path, path: str, *, staged: bool = False) -> dict | None:
    if staged:
        try:
            content = git(root, "show", f":{path}")
        except subprocess.CalledProcessError:
            return None
    else:
        file = root / path
        if (
            file.is_symlink()
            or file.is_junction()
            or not file.resolve().is_relative_to(root.resolve())
        ):
            raise ValueError("Policy must stay inside the working tree")
        if not file.exists():
            return None
        content = file.read_bytes()
    return json.loads(content)


def load_policy(root: Path, *, staged: bool = False) -> dict:
    policy = read_policy_json(root, POLICY, staged=staged)
    if policy is None:
        policy = {}
    if not isinstance(policy, dict):
        raise ValueError("Invalid artifact policy")
    identity_policy = read_policy_json(root, IDENTITY_POLICY, staged=staged)
    policy["approved_git_identities"] = (
        parse_identity_policy(identity_policy) if identity_policy is not None else frozenset()
    )
    review = read_policy_json(root, HISTORY_REVIEW, staged=staged)
    if review is not None:
        if (
            not isinstance(review, dict)
            or set(review) != {"version", "legacy_contact_metadata", "historical_raw_logs"}
            or type(review["version"]) is not int
            or review["version"] != 1
        ):
            raise ValueError("Invalid historical review")
        for field in ("legacy_contact_metadata", "historical_raw_logs"):
            if not isinstance(review[field], dict):
                raise ValueError("Invalid historical review entries")
            for key, digest in review[field].items():
                if (
                    not isinstance(key, str)
                    or not isinstance(digest, str)
                    or not re.fullmatch(r"[0-9a-f]{64}", digest)
                    or (
                        field == "legacy_contact_metadata"
                        and not re.fullmatch(r"[0-9a-f]{40}", key)
                    )
                    or (field == "historical_raw_logs" and forbidden_path(key) != "raw-test-log")
                ):
                    raise ValueError("Historical review requires exact objects and digests")
        policy.update(review)
    return policy


def scan_identity(name: str, email: str, role: str, policy: dict, oid=None) -> list[Finding]:
    """Inspect metadata without printing names or addresses, including overridden Git env."""
    findings = scan_text(f"<git-{role}-name>", name, oid)
    email_findings = scan_text(f"<git-{role}-email>", email, oid)
    if NOREPLY.fullmatch(email) or (name, email) in policy.get("approved_git_identities", ()):
        email_findings = [f for f in email_findings if f.rule != "email-review"]
    elif not EMAIL.fullmatch(email):
        email_findings.append(Finding(f"<git-{role}-email>", "invalid-git-email", object_id=oid))
    return findings + email_findings


def scan_pending_identity(root: Path, *, staged: bool = False) -> list[Finding]:
    policy = load_policy(root, staged=staged)
    findings = []
    for role in ("author", "committer"):
        value = git(root, "var", f"GIT_{role.upper()}_IDENT").decode("utf8").strip()
        identity = re.fullmatch(r"(.+) <([^<>]+)> \d+ [+-]\d{4}", value)
        if not identity:
            raise ValueError("Cannot parse pending Git identity")
        findings.extend(scan_identity(identity[1], identity[2], role, policy))
    return findings


def check_content(
    path: str, data: bytes, policy: dict, object_id: str | None = None, *, historical=False
) -> list[Finding]:
    findings = []
    rule = forbidden_path(path)
    if (
        rule == "raw-test-log"
        and historical
        and policy.get("historical_raw_logs", {}).get(path) == hashlib.sha256(data).hexdigest()
    ):
        rule = None
    if rule:
        findings.append(Finding(path, rule, object_id=object_id))
    if data.startswith(b"SQLite format 3\0"):
        findings.append(Finding(path, "sqlite-content", object_id=object_id))
    suffix = PurePosixPath(path).suffix.lower()
    binary = b"\0" in data or data.startswith((b"PK\x03\x04", b"%PDF", b"\x89PNG", b"\xff\xd8\xff"))
    if suffix in REVIEW_SUFFIXES or binary:
        digest = hashlib.sha256(data).hexdigest()
        if digest in policy.get("blocked_sha256", {}):
            findings.append(Finding(path, "known-private-image", object_id=object_id))
        accepted = policy.get("artifacts", {}).get(path, {}).get("sha256", [])
        if digest not in accepted:
            findings.append(Finding(path, "unapproved-binary-or-material", object_id=object_id))
    if not binary:
        try:
            value = data.decode("utf-8-sig")
            if (
                suffix == ".txt"
                and RAW_LOG_TEXT.search(value)
                and forbidden_path(path) != "raw-test-log"
            ):
                findings.append(Finding(path, "raw-test-log", object_id=object_id))
            text_findings = scan_text(path, value, object_id)
            if path == IDENTITY_POLICY:
                identities = parse_identity_policy(json.loads(value))
                if identities <= policy.get("approved_git_identities", frozenset()):
                    # This strict-schema policy declares approvals, not ordinary file content.
                    text_findings = [f for f in text_findings if f.rule != "email-review"]
                else:
                    text_findings.append(
                        Finding(
                            path, "unapproved-git-identity-policy", "review", object_id=object_id
                        )
                    )
            findings.extend(text_findings)
        except UnicodeError:
            findings.append(Finding(path, "non-utf8-review", "review", object_id=object_id))
    # Inspect Office/archive XML, relationships and metadata; never execute embedded files.
    if data.startswith(b"PK\x03\x04"):
        try:
            with zipfile.ZipFile(io.BytesIO(data)) as archive:
                members = archive.infolist()
                if sum(m.file_size for m in members) > 32 * 1024 * 1024 or len(members) > 2000:
                    findings.append(Finding(path, "archive-review-limit", object_id=object_id))
                else:
                    for member in members:
                        if member.filename.endswith((".xml", ".rels", ".txt", ".json")):
                            value = archive.read(member).decode("utf8", errors="replace")
                            findings.extend(scan_text(path, value, object_id))
        except (zipfile.BadZipFile, RuntimeError, OSError):
            findings.append(Finding(path, "unreadable-archive", object_id=object_id))
    return findings


def index_entries(root: Path) -> dict[str, tuple[str, str]]:
    entries = {}
    for entry in git(root, "ls-files", "--stage", "-z").split(b"\0"):
        if not entry:
            continue
        info, raw_path = entry.split(b"\t", 1)
        mode, oid, stage = info.decode().split()
        if stage != "0":
            raise ValueError("Unmerged index: resolve conflicts before scanning")
        entries[raw_path.decode("utf8")] = (mode, oid)
    return entries


def scan_tree(
    root: Path, *, staged: bool = False, worktree: bool = False
) -> tuple[list[Finding], dict]:
    policy = load_policy(root, staged=staged)
    entries = index_entries(root)
    if staged:
        changed = set(
            git(root, "diff", "--cached", "--name-only", "--diff-filter=ACMR", "-z")
            .decode()
            .split("\0")
        )
        entries = {p: v for p, v in entries.items() if p in changed}
    elif worktree:
        for path in (
            git(root, "ls-files", "--others", "--exclude-standard", "-z").decode().split("\0")
        ):
            if path:
                entries.setdefault(path, ("100644", ""))
    findings = []
    checked = 0
    for path, (mode, oid) in entries.items():
        if mode not in {"100644", "100755"} or (not staged and (root / path).is_symlink()):
            findings.append(Finding(path, "symlink-or-submodule"))
            continue
        if staged:
            data = git(root, "cat-file", "blob", oid)
        else:
            file = root / path
            if not file.exists():
                continue
            if file.is_junction() or not file.resolve().is_relative_to(root.resolve()):
                findings.append(Finding(path, "outside-working-tree"))
                continue
            data = file.read_bytes()
        findings.extend(check_content(path, data, policy, oid if staged else None))
        checked += 1
    return findings, {
        "mode": "staged" if staged else "worktree" if worktree else "tracked",
        "files_checked": checked,
    }


def history_roots(root: Path) -> list[str]:
    # Codex keeps tree refs as well as ordinary commit refs. Audit both.
    roots = set(git(root, "rev-list", "--all").decode().splitlines())
    for ref in git(root, "for-each-ref", "--format=%(refname)").decode().splitlines():
        result = subprocess.run(
            ["git", "-C", str(root), "rev-parse", f"{ref}^{{tree}}"], capture_output=True
        )
        if result.returncode:
            raise ValueError("Unsupported ref type: manual history review required")
        roots.add(result.stdout.decode().strip())
    return sorted(roots)


def scan_history(root: Path) -> tuple[list[Finding], dict]:
    policy = load_policy(root)
    objects: dict[tuple[str, str], str] = {}
    roots = history_roots(root)
    for revision in roots:
        for entry in git(root, "ls-tree", "-r", "-z", revision).split(b"\0"):
            if not entry:
                continue
            info, raw_path = entry.split(b"\t", 1)
            mode, kind, oid = info.decode().split()
            path = raw_path.decode("utf8")
            objects[(path, oid)] = mode if kind == "blob" else "unsupported"
    findings = []
    blobs = {}
    materials = []
    for (path, oid), mode in sorted(objects.items()):
        if mode not in {"100644", "100755"}:
            findings.append(Finding(path, "historical-symlink-or-submodule", object_id=oid))
            continue
        if oid not in blobs:
            blobs[oid] = git(root, "cat-file", "blob", oid)
        data = blobs[oid]
        findings.extend(check_content(path, data, policy, oid, historical=True))
        if PurePosixPath(path).suffix.lower() in REVIEW_SUFFIXES or b"\0" in data:
            materials.append(
                {
                    "path": path,
                    "object_id": oid,
                    "bytes": len(data),
                    "sha256": hashlib.sha256(data).hexdigest(),
                }
            )
    legacy_contacts = []
    for oid in git(root, "rev-list", "--all").decode().splitlines():
        metadata = git(root, "show", "-s", "--format=%an%x00%ae%x00%cn%x00%ce", oid)
        author, author_email, committer, committer_email = (
            metadata.decode("utf8").rstrip("\n").split("\0")
        )
        identity_findings = scan_identity(author, author_email, "author", policy, oid)
        identity_findings.extend(
            scan_identity(committer, committer_email, "committer", policy, oid)
        )
        if (
            policy.get("legacy_contact_metadata", {}).get(oid)
            == hashlib.sha256(metadata).hexdigest()
        ):
            # Keep token/name/path/phone findings. Only this exact old email finding is recorded.
            if any(f.rule == "email-review" for f in identity_findings):
                legacy_contacts.append(oid)
            identity_findings = [f for f in identity_findings if f.rule != "email-review"]
        findings.extend(identity_findings)
        message = git(root, "show", "-s", "--format=%B", oid).decode("utf8", errors="replace")
        findings.extend(scan_commit_message(message, policy, oid))
    return findings, {
        "mode": "history",
        "commits": len(git(root, "rev-list", "--all").splitlines()),
        "roots": len(roots),
        "path_versions": len(objects),
        "unique_blobs": len(blobs),
        "largest_blob_bytes": max(map(len, blobs.values()), default=0),
        "materials": materials,
        "legacy_contact_commits": legacy_contacts,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--staged", action="store_true", help="Check changed index bytes, not working files"
    )
    mode.add_argument("--history", action="store_true", help="All reachable commits and tree refs")
    mode.add_argument(
        "--worktree", action="store_true", help="Tracked plus unignored untracked files"
    )
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument(
        "--check-identity",
        action="store_true",
        help="Check pending author/committer, including Git environment overrides",
    )
    parser.add_argument("--report", type=Path, help="Write value-redacted JSON evidence locally")
    args = parser.parse_args(argv)
    try:
        root = args.root.resolve()
        findings, stats = (
            scan_history(root)
            if args.history
            else scan_tree(root, staged=args.staged, worktree=args.worktree)
        )
        if args.check_identity:
            findings.extend(scan_pending_identity(root, staged=args.staged))
        errors = [f for f in findings if f.severity == "error"]
        reviews = [f for f in findings if f.severity == "review"]
        report = {
            "scanner": "Studium stdlib fallback v1",
            "stats": stats,
            "errors": len(errors),
            "reviews": len(reviews),
            "findings": [asdict(f) for f in findings],
        }
        if args.report:
            args.report.parent.mkdir(parents=True, exist_ok=True)
            args.report.write_text(
                json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf8"
            )
        for finding in findings:
            print(
                f"{finding.severity}: {finding.path} [{finding.rule}] line={finding.line} object={finding.object_id}"
            )
        print(
            f"{stats['mode']}: {stats.get('files_checked', stats.get('path_versions'))} checked; {len(errors)} errors; {len(reviews)} manual-review signals"
        )
        if stats.get("legacy_contact_commits"):
            print(
                f"Known historical contact metadata: {len(stats['legacy_contact_commits'])} commits; public release still requires an owner decision"
            )
        # Privacy signals need a human decision too; never silently label them PASS.
        return 1 if findings else 0
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        print(f"Repository scan failed ({type(error).__name__}); no PASS", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
