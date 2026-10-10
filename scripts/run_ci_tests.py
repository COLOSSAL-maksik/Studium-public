"""Discover all pytest tests and isolate full regression by module, without xdist."""

import argparse
import contextlib
import io
import os
import subprocess
import sys
import time
from collections import defaultdict
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def is_fast(path: str) -> bool:
    return bool({"unit", "architecture"} & set(Path(path).parts[1:-1]))


class Collection:
    def __init__(self):
        self.items = []
        self.skipped = []

    def pytest_collectreport(self, report):
        if report.skipped:
            self.skipped.append(report.nodeid)

    def pytest_collection_finish(self, session):
        self.items = [
            (
                item.path.relative_to(ROOT).as_posix(),
                item.nodeid,
                bool(item.get_closest_marker("windows")),
            )
            for item in session.items
        ]


class SkipPolicy:
    """A new platform-only test cannot silently disappear from Linux coverage."""

    def __init__(self):
        self.unexpected = []

    @pytest.hookimpl(hookwrapper=True)
    def pytest_runtest_makereport(self, item, call):
        report = (yield).get_result()
        if report.skipped and not (os.name != "nt" and item.get_closest_marker("windows")):
            self.unexpected.append(item.nodeid)

    def pytest_sessionfinish(self, session, exitstatus):
        if self.unexpected:
            print("\nCI refuses unexpected skips: " + ", ".join(self.unexpected))
            session.exitstatus = pytest.ExitCode.TESTS_FAILED


def collect() -> list[tuple[str, str, bool]]:
    collector = Collection()
    captured = io.StringIO()
    with contextlib.redirect_stdout(captured), contextlib.redirect_stderr(captured):
        status = pytest.main(["--collect-only", "-qq", "--strict-markers"], plugins=[collector])
    if status != 0:
        print(captured.getvalue())
        raise SystemExit(status)
    if collector.skipped:
        raise SystemExit("CI refuses collection skips: " + ", ".join(collector.skipped))
    if not collector.items:
        raise SystemExit("No tests collected")
    return collector.items


def select(items: list[tuple[str, str, bool]], phase: str) -> dict[str, list[str]]:
    groups = defaultdict(list)
    for path, nodeid, windows in items:
        if (
            phase == "all"
            or (phase == "fast" and is_fast(path))
            or (phase == "full" and not is_fast(path))
        ):
            groups[path].append(nodeid)
        elif phase == "windows" and windows:
            groups[path].append(nodeid)
    return dict(groups)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--phase", choices=["fast", "full", "all", "windows"], default="all")
    parser.add_argument("--list", action="store_true")
    parser.add_argument("--module-timeout", type=int, default=600)
    parser.add_argument("--worker", nargs="+", help=argparse.SUPPRESS)
    args = parser.parse_args()
    os.chdir(ROOT)
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    if args.worker:
        return int(
            pytest.main(
                [
                    "-q",
                    "-x",
                    "--strict-markers",
                    "--durations=30",
                    "-o",
                    "faulthandler_timeout=60",
                    *args.worker,
                ],
                plugins=[SkipPolicy()],
            )
        )
    groups = select(collect(), args.phase)
    if not groups:
        raise SystemExit(f"No tests selected for {args.phase}")
    print(
        f"{args.phase}: {sum(map(len, groups.values()))} tests in {len(groups)} modules", flush=True
    )
    if args.list:
        for path, nodes in groups.items():
            print(f"{path}: {len(nodes)}")
        return 0
    # Fast unit/architecture tests share one process. Full/Windows modules get a
    # fresh QApplication, thread pool and profile each, with no shared DB template.
    batches = (
        [list(groups)]
        if args.phase == "fast"
        else [nodes if args.phase == "windows" else [path] for path, nodes in groups.items()]
    )
    started = time.monotonic()
    for batch in batches:
        print(f"\nRunning {', '.join(batch)}", flush=True)
        try:
            result = subprocess.run(
                [sys.executable, str(Path(__file__).resolve()), "--worker", *batch],
                timeout=args.module_timeout,
                check=False,
            )
        except subprocess.TimeoutExpired:
            print(
                "Module exceeded timeout; CI fails without skipping remaining coverage", flush=True
            )
            return 1
        if result.returncode:
            return result.returncode
    print(f"{args.phase} completed in {time.monotonic() - started:.2f}s", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
