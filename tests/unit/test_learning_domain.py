from dataclasses import replace

import pytest

from studium.domain.entities import AssessmentItem, Attendance, Skill, Topic
from studium.domain.enums import AttendanceStatus
from studium.domain.value_objects import EntityId
from tests.unit.test_domain import metadata


@pytest.mark.parametrize(
    "kind,fields",
    [
        (Topic, {"course_id": EntityId.generate(), "title": " "}),
        (Skill, {"course_id": EntityId.generate(), "title": " "}),
        (Topic, {"course_id": EntityId.generate(), "title": "Test", "sort_order": -1}),
        (Skill, {"course_id": EntityId.generate(), "title": "Test", "sort_order": 1.5}),
        (AssessmentItem, {"assessment_id": EntityId.generate(), "title": " "}),
        (AssessmentItem, {"assessment_id": EntityId.generate(), "title": "Test", "max_score": 0}),
        (
            AssessmentItem,
            {"assessment_id": EntityId.generate(), "title": "Test", "max_score": float("inf")},
        ),
        (
            Attendance,
            {
                "lesson_id": EntityId.generate(),
                "enrollment_id": EntityId.generate(),
                "status": "invalid",
            },
        ),
    ],
)
def test_invalid_learning_values(kind, fields):
    with pytest.raises(ValueError):
        kind(metadata=metadata(), **fields)


def test_topic_cannot_be_its_own_parent():
    topic = Topic(metadata=metadata(), course_id=EntityId.generate(), title="Test")
    with pytest.raises(ValueError):
        replace(topic, parent_topic_id=topic.id)


def test_unknown_attendance_is_distinct_from_unmarked():
    fact = Attendance(
        metadata=metadata(),
        lesson_id=EntityId.generate(),
        enrollment_id=EntityId.generate(),
        status=AttendanceStatus.UNKNOWN,
    )
    assert fact.status == AttendanceStatus.UNKNOWN
