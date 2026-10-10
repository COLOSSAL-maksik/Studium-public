"""Conservative CI routing; every unknown or executable path gets full regression."""

import argparse
import os
import subprocess
from pathlib import Path, PurePosixPath


def plan(paths: list[str]) -> dict[str, bool]:
    def documentation(path: str) -> bool:
        p = PurePosixPath(path)
        return path in {"README.md", ".github/pull_request_template.md"} or (
            p.parts[0] == "docs" and p.suffix in {".md", ".rst"}
        )

    significant = [path for path in paths if not documentation(path)]
    # Empty diffs fail closed (e.g. an unusual merge/ref); manual runs bypass routing.
    full = bool(significant) or not paths
    installer = full
    return {"full": full, "installer": installer}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base")
    parser.add_argument("--head", default="HEAD")
    parser.add_argument("--manual", action="store_true")
    args = parser.parse_args()
    if args.manual:
        result = {"full": True, "installer": True}
    else:
        if not args.base:
            parser.error("--base is required for pull requests")
        raw = subprocess.check_output(
            ["git", "diff", "--name-only", "--no-renames", "-z", f"{args.base}...{args.head}"]
        )
        result = plan([p.decode("utf-8") for p in raw.split(b"\0") if p])
    lines = [f"{key}={str(value).lower()}" for key, value in result.items()]
    print("\n".join(lines))
    if output := os.environ.get("GITHUB_OUTPUT"):
        with Path(output).open("a", encoding="utf-8") as stream:
            stream.write("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
