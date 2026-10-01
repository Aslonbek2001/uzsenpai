import time

from app.shared.ids import uuid7


def test_uuid7_version_and_variant() -> None:
    value = uuid7()
    assert value.version == 7
    assert value.variant == "specified in RFC 4122"


def test_uuid7_embeds_current_millisecond() -> None:
    before = time.time_ns() // 1_000_000
    value = uuid7()
    after = time.time_ns() // 1_000_000
    assert before <= value.int >> 80 <= after + 1  # +1: the counter may borrow the next millisecond


def test_uuid7_is_monotonic_and_unique() -> None:
    ids = [uuid7() for _ in range(10_000)]
    assert ids == sorted(ids)
    assert len(set(ids)) == len(ids)
