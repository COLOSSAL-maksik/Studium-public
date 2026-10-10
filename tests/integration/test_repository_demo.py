"""Fresh generated demo, import/reopen and no production source dependency."""

import importlib.util
from pathlib import Path

import pytest

from studium.composition import create_runtime

spec = importlib.util.spec_from_file_location(
    "demo_generator", Path(__file__).resolve().parents[2] / "scripts/create_demo_data.py"
)
demo = importlib.util.module_from_spec(spec)
spec.loader.exec_module(demo)


def test_demo_is_generated_fresh_synthetic_and_preserved_on_reopen(tmp_path):
    root = tmp_path / "demo"
    assert demo.create_demo(root) == {"students": 3, "group": "DEMO-02", "synthetic": True}
    before = (root / "studium.sqlite").read_bytes()
    with pytest.raises(FileExistsError):
        demo.create_demo(root)
    assert (root / "studium.sqlite").read_bytes() == before
    runtime = create_runtime(root)
    try:
        s = runtime.service
        offering = s.list_offerings()[0].offering
        students = s.list_students_for_offering(offering.id)
        assert [e.student.full_name for e in students] == [f"Студент {i:03d}" for i in range(1, 4)]
        files = list((root / "files").rglob("*.txt"))
        assert len(files) == 1 and files[0].read_bytes().startswith(b"Studium DEMO")
    finally:
        runtime.close()


@pytest.mark.parametrize("child", ["", "nested-demo"])
def test_demo_never_uses_default_production_root(tmp_path, child):
    target = tmp_path / "profile/Studium" / child
    with pytest.raises(ValueError, match="production"):
        demo.create_demo(target)
    assert not target.exists()
