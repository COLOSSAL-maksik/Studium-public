"""Versioned annual content and exact arithmetic independent of Qt/SQL."""

from collections import defaultdict
from copy import deepcopy
from dataclasses import dataclass
from decimal import Decimal
from uuid import uuid4

from studium.domain.entities import StudiumEntity
from studium.domain.enums import AssessmentType
from studium.domain.qa import check_cents, direction_identity
from studium.domain.value_objects import EntityId

LESSON_KINDS = {"LECTURE": "Лекции", "SEMINAR": "Семинары", "LAB": "Лабораторные"}
LOAD_KINDS = LESSON_KINDS | {
    "SELF_STUDY": "Самостоятельная работа",
    "CONSULTATION": "Консультации",
    "CONTROL": "Контроль / аттестация",
    "OTHER": "Прочее",
}
OUTCOME_KINDS = {"KNOWLEDGE": "Знания", "ABILITY": "Умения", "COMPETENCE": "Компетенции"}
WORK_KINDS = {v.value for v in AssessmentType}


def key() -> str:
    return str(uuid4())


def hours(value: str) -> Decimal:
    """Academic hours: exact hundredths, no floats, exponent or rounding."""
    import re

    if not isinstance(value, str) or not re.fullmatch(r"\d{1,8}(?:[.,]\d{1,2})?", value):
        raise ValueError("Часы: неотрицательное число, до двух знаков после запятой")
    return Decimal(value.replace(",", "."))


def new_annual(title="") -> dict:
    return {
        "schema_version": 1,
        "passport": {
            "title": title,
            "label": "",
            "academic_year": "",
            "notes": "",
            "academic_hour_minutes": 45,
            "directions": [],
        },
        "semesters": [
            {"key": key(), "number": n, "title": f"Семестр {n}", "weeks": 17, "modules": []}
            for n in (1, 2)
        ],
        "outcomes": [],
        "prerequisites": [],
        "loads": [],
        "norms": [],
        "budgets": [],
        "scoring": "POINTS",
        "not_applicable": [],
    }


@dataclass(frozen=True, kw_only=True)
class ProgramDraft(StudiumEntity):
    course_program_id: EntityId
    content_json: str
    base_version_id: EntityId | None = None


@dataclass(frozen=True, kw_only=True)
class ProgramImport(StudiumEntity):
    program_version_id: EntityId
    origin: str
    content_hash: str


@dataclass(frozen=True, kw_only=True)
class PlanLesson(StudiumEntity):
    semester_plan_id: EntityId
    plan_module_id: EntityId
    program_version_id: EntityId
    source_key: str
    baseline_json: str
    current_json: str
    lesson_id: EntityId | None = None


@dataclass(frozen=True)
class Volume:
    semester_key: str | None
    kind: str
    count: int
    hours: Decimal
    normative: Decimal | None

    @property
    def difference(self):
        return None if self.normative is None else self.hours - self.normative


@dataclass(frozen=True)
class ScoreTotal:
    semester_key: str
    module_key: str
    category: str
    allocated: int
    budget: int | None
    maximum: int


def volume(annual: dict) -> tuple[Volume, ...]:
    totals, counts = defaultdict(Decimal), defaultdict(int)
    for semester in annual["semesters"]:
        for module in semester["modules"]:
            for lesson in module["lessons"]:
                slot = semester["key"], lesson["kind"]
                counts[slot] += 1
                totals[slot] += hours(lesson.get("hours", "0") or "0")
    for load in annual["loads"]:
        totals[load["semester_key"], load["kind"]] += hours(load["hours"])
    norms = {(n["semester_key"], n["kind"]): hours(n["hours"]) for n in annual["norms"]}
    rows = [
        Volume(
            s["key"],
            kind,
            counts[s["key"], kind],
            totals[s["key"], kind],
            norms.get((s["key"], kind)),
        )
        for s in annual["semesters"]
        for kind in LOAD_KINDS
    ]
    for kind in LOAD_KINDS:
        parts = [r for r in rows if r.kind == kind]
        rows.append(
            Volume(
                None,
                kind,
                sum(r.count for r in parts),
                sum((r.hours for r in parts), Decimal()),
                sum((r.normative for r in parts), Decimal())
                if parts and all(r.normative is not None for r in parts)
                else None,
            )
        )
    return tuple(rows)


@dataclass(frozen=True)
class ModuleVolume:
    semester_key: str
    module_key: str
    kind: str
    count: int
    hours: Decimal


def module_volume(annual: dict) -> tuple[ModuleVolume, ...]:
    rows = []
    for semester in annual["semesters"]:
        for module in semester["modules"]:
            for kind in LOAD_KINDS:
                lessons = [lesson for lesson in module["lessons"] if lesson["kind"] == kind]
                amount = sum((hours(lesson.get("hours") or "0") for lesson in lessons), Decimal())
                amount += sum(
                    (
                        hours(load["hours"])
                        for load in annual["loads"]
                        if load.get("module_key") == module["key"] and load["kind"] == kind
                    ),
                    Decimal(),
                )
                rows.append(
                    ModuleVolume(semester["key"], module["key"], kind, len(lessons), amount)
                )
    return tuple(rows)


def score_totals(annual: dict) -> tuple[ScoreTotal, ...]:
    budgets = {(b["module_key"], b["category"]): b["max_cents"] for b in annual["budgets"]}
    rows = []
    for s in annual["semesters"]:
        for m in s["modules"]:
            categories = {w["category"] for w in m["works"]} | {
                c for mid, c in budgets if mid == m["key"] and c != "*"
            }
            module_max = 0
            for c in sorted(categories):
                allocated = sum(w.get("max_cents") or 0 for w in m["works"] if w["category"] == c)
                budget = budgets.get((m["key"], c))
                maximum = budget if budget is not None else allocated
                rows.append(ScoreTotal(s["key"], m["key"], c, allocated, budget, maximum))
                module_max += maximum
            budget = budgets.get((m["key"], "*"))
            rows.append(
                ScoreTotal(
                    s["key"],
                    m["key"],
                    "*",
                    module_max,
                    budget,
                    budget if budget is not None else module_max,
                )
            )
    return tuple(rows)


def validate(annual: dict, *, ready=False) -> tuple[str, ...]:
    """Integrity always raises; completeness is returned for a draft or publication."""
    if (
        not isinstance(annual, dict)
        or type(annual.get("schema_version")) is not int
        or annual["schema_version"] != 1
    ):
        raise ValueError("Неизвестная схема годовой программы")
    missing, ids = [], set()

    def identity(row):
        value = row["key"]
        EntityId(value)
        if value in ids:
            raise ValueError("Повтор идентификатора в структуре")
        ids.add(value)

    def integer(value, lo, hi=104):
        if type(value) is not int or not lo <= value <= hi:
            raise ValueError("Некорректный порядок, номер или границы недель")

    def text(value):
        if not isinstance(value, str):
            raise ValueError("Ожидается текст")
        return value.strip()

    p = annual["passport"]
    if not text(p["title"]):
        missing.append("Паспорт: название программы")
    for name in ("label", "academic_year", "notes"):
        text(p[name])
    integer(p["academic_hour_minutes"], 1, 180)
    codes = set()
    for d in p["directions"]:
        code, normalized = direction_identity(d["code"])
        if code != d["code"] or normalized in codes:
            raise ValueError("Повторяющийся или ненормализованный код направления")
        text(d["name"])
        codes.add(normalized)
    if annual["scoring"] not in {"POINTS", "NONE"}:
        raise ValueError("Выберите использование балльной системы")
    na = set(annual["not_applicable"])
    if na - {"outcomes", "prerequisites", "lessons", "works", "materials"}:
        raise ValueError("Неизвестный раздел «Не предусмотрено»")
    semesters, modules, lesson_ids, work_ids, ordinals = {}, {}, set(), set(), set()
    if not annual["semesters"]:
        missing.append("Годовой план: добавьте семестр")
    for s in annual["semesters"]:
        identity(s)
        integer(s["number"], 1)
        integer(s["weeks"], 1)
        if s["number"] in ordinals:
            raise ValueError("Повтор номера семестра курса")
        ordinals.add(s["number"])
        semesters[s["key"]] = s
        if not text(s["title"]):
            missing.append("Название семестра")
        ordered = sorted(s["modules"], key=lambda m: m["start_week"])
        if any(a["end_week"] >= b["start_week"] for a, b in zip(ordered, ordered[1:])):
            raise ValueError("Модули одного семестра пересекаются")
        for m in s["modules"]:
            identity(m)
            modules[m["key"]] = s["key"]
            integer(m["start_week"], 1, s["weeks"])
            integer(m["end_week"], m["start_week"], s["weeks"])
            if not text(m["title"]):
                missing.append("Название модуля")
            for lesson in m["lessons"]:
                identity(lesson)
                lesson_ids.add(lesson["key"])
                if lesson["kind"] not in LESSON_KINDS:
                    raise ValueError("Неизвестный тип занятия")
                if lesson.get("week") is not None:
                    integer(lesson["week"], m["start_week"], m["end_week"])
                raw_hours = lesson.get("hours", "")
                duration = hours("0" if raw_hours == "" else raw_hours)
                if not text(lesson["title"]) or not lesson["topic_ids"] or duration <= 0:
                    missing.append(
                        f"Занятие {lesson['title'] or 'без названия'}: название, темы и положительные часы"
                    )
                for tid in lesson["topic_ids"]:
                    EntityId(tid)
                if len(set(lesson["topic_ids"])) != len(lesson["topic_ids"]):
                    raise ValueError("Повтор темы занятия")
            for w in m["works"]:
                identity(w)
                work_ids.add(w["key"])
                if w["category"] not in WORK_KINDS:
                    raise ValueError("Неизвестный вид работы")
                if not text(w["title"]):
                    missing.append("Название предусмотренной работы")
                low, high = w.get("min_cents"), w.get("max_cents")
                check_cents(low, optional=True)
                check_cents(high, optional=True)
                if low is not None and high is not None and (low > high or high == 0):
                    raise ValueError("Некорректные балльные границы")
                if annual["scoring"] == "POINTS" and (low is None or high is None):
                    missing.append(f"Балльные границы работы {w['title']}")
                if annual["scoring"] == "NONE" and (low is not None or high is not None):
                    raise ValueError("Удалите балльные границы при отказе от балльной системы")
                if w.get("definition_id"):
                    EntityId(w["definition_id"])
    for name in ("loads", "norms"):
        used = set()
        for row in annual[name]:
            identity(row)
            scope = row.get("module_key")
            if (
                row["semester_key"] not in semesters
                or scope
                and modules.get(scope) != row["semester_key"]
            ):
                raise ValueError("Нагрузка ссылается на отсутствующий семестр/модуль")
            if row["kind"] not in LOAD_KINDS or name == "loads" and row["kind"] in LESSON_KINDS:
                raise ValueError("Часы лекций/семинаров/лабораторных вычисляются только из занятий")
            hours(row["hours"])
            slot = row["semester_key"], row["kind"]
            if name == "norms" and slot in used:
                raise ValueError("Повтор норматива")
            used.add(slot)
    for o in annual["outcomes"]:
        identity(o)
        if o["category"] not in OUTCOME_KINDS:
            raise ValueError("Неизвестная категория результата обучения")
        if not text(o["text"]):
            missing.append("Формулировка результата обучения")
        for field, targets in (("module_keys", modules), ("work_keys", work_ids)):
            if set(o.get(field, [])) - set(targets):
                raise ValueError("Результат ссылается на отсутствующий модуль/работу")
        for field in ("topic_ids", "skill_ids"):
            for value in o.get(field, []):
                EntityId(value)
    for p in annual["prerequisites"]:
        identity(p)
        if not text(p["discipline"]) or not text(p["content"]):
            missing.append("Предварительная подготовка: дисциплина и содержание")
        if p.get("course_id"):
            EntityId(p["course_id"])
    budget_slots = set()
    for b in annual["budgets"]:
        identity(b)
        if b["module_key"] not in modules or b["category"] not in WORK_KINDS | {"*"}:
            raise ValueError("Некорректная ссылка бюджета")
        slot = b["module_key"], b["category"]
        if slot in budget_slots:
            raise ValueError("Повтор бюджета модуля/категории")
        budget_slots.add(slot)
        check_cents(b["max_cents"])
    if annual["scoring"] == "NONE" and annual["budgets"]:
        raise ValueError("Балльная система выключена; удалите бюджеты")
    for row in score_totals(annual):
        if row.budget is not None and row.allocated > row.budget:
            missing.append("Распределение баллов превышает бюджет модуля/категории")
    for field, has_values in (
        ("outcomes", annual["outcomes"]),
        ("prerequisites", annual["prerequisites"]),
        ("lessons", lesson_ids),
        ("works", work_ids),
    ):
        if has_values and field in na:
            raise ValueError("Заполненный раздел нельзя пометить «Не предусмотрено»")
        if not has_values and field not in na:
            missing.append(f"Раздел {field}: заполните или укажите «Не предусмотрено»")
    result = tuple(dict.fromkeys(missing))
    if ready and result:
        raise ValueError("\n".join(result))
    return result


def copy_fragment(fragment: dict) -> dict:
    """Copy a semester/module with new internal identities."""
    remap = {}

    def collect(value):
        if isinstance(value, dict):
            if "key" in value:
                remap[value["key"]] = key()
            for child in value.values():
                collect(child)
        elif isinstance(value, list):
            for child in value:
                collect(child)

    def rewrite(value):
        if isinstance(value, dict):
            return {k: rewrite(v) for k, v in value.items()}
        if isinstance(value, list):
            return [rewrite(v) for v in value]
        return remap.get(value, value) if isinstance(value, str) else value

    collect(fragment)
    return rewrite(deepcopy(fragment))
