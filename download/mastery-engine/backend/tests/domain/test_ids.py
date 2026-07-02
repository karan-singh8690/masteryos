"""Tests for typed identifiers."""

from __future__ import annotations

import pytest
from uuid import uuid4

from app.domain.shared.ids import (
    AttemptId,
    ConceptId,
    MasteryScoreId,
    UserId,
)


class TestTypedIds:
    """Tests for typed ID value objects."""

    def test_generate_creates_unique_ids(self) -> None:
        id1 = UserId.generate()
        id2 = UserId.generate()
        assert id1 != id2

    def test_from_string(self) -> None:
        raw = str(uuid4())
        uid = UserId.from_string(raw)
        assert str(uid.value) == raw

    def test_str_representation(self) -> None:
        uid = UserId.generate()
        assert str(uid) == str(uid.value)

    def test_same_value_same_type_are_equal(self) -> None:
        raw = uuid4()
        id1 = UserId(raw)
        id2 = UserId(raw)
        assert id1 == id2

    def test_different_values_same_type_not_equal(self) -> None:
        assert UserId.generate() != UserId.generate()

    def test_same_value_different_types_not_equal(self) -> None:
        """A UserId and a ConceptId with the same UUID are NOT equal."""
        raw = uuid4()
        uid = UserId(raw)
        cid = ConceptId(raw)
        # They should not be equal despite same UUID value
        # (type safety prevents mixing IDs)
        assert uid != cid  # different dataclass types

    def test_immutability(self) -> None:
        uid = UserId.generate()
        with pytest.raises(AttributeError):
            uid.value = uuid4()  # type: ignore[misc]

    def test_all_id_types_can_be_generated(self) -> None:
        """All ID types have generate() and from_string()."""
        for id_type in [UserId, ConceptId, AttemptId, MasteryScoreId]:
            generated = id_type.generate()
            assert generated is not None
            from_str = id_type.from_string(str(generated.value))
            assert from_str == generated
