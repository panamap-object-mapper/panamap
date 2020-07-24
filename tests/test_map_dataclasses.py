from dataclasses import dataclass
from typing import Optional
from unittest import TestCase

from panamap import Mapper, MissingMappingException


@dataclass
class A:
    a_value: str
    common_value: int


@dataclass
class B:
    b_value: str
    common_value: int


@dataclass
class NestedA:
    value: int


@dataclass
class OuterA:
    nested: NestedA


@dataclass
class NestedB:
    value: int


@dataclass
class OuterB:
    nested: NestedB


@dataclass
class StringCarrier:
    value: str


@dataclass
class OptionalStringCarrier:
    value: Optional[str]


@dataclass
class ForwardRefCarrier:
    value: "ForwardReferenced"


@dataclass
class ForwardReferenced:
    value: str


class TestMapDataclasses(TestCase):
    def test_map_matching_dataclasses(self):
        mapper = Mapper()
        mapper.mapping(A, B).bidirectional("a_value", "b_value").map_matching().register()

        b = mapper.map(A("123", 456), B)

        self.assertEqual(b.__class__, B)
        self.assertEqual(b.b_value, "123")
        self.assertEqual(b.common_value, 456)

        a = mapper.map(B("xyz", 789), A)

        self.assertEqual(a.__class__, A)
        self.assertEqual(a.a_value, "xyz")
        self.assertEqual(a.common_value, 789)

    def test_map_nested_dataclasses(self):
        mapper = Mapper()
        mapper.mapping(OuterA, OuterB).map_matching().register()
        mapper.mapping(NestedA, NestedB).map_matching().register()

        b = mapper.map(OuterA(NestedA(123)), OuterB)

        self.assertEqual(b.__class__, OuterB)
        self.assertEqual(b.nested.__class__, NestedB)
        self.assertEqual(b.nested.value, 123)

    def test_map_optional_value(self):
        mapper = Mapper()
        mapper.mapping(StringCarrier, OptionalStringCarrier).map_matching().register()

        b = mapper.map(StringCarrier("123"), OptionalStringCarrier)

        self.assertEqual(b.value, "123")

        a = mapper.map(OptionalStringCarrier("456"), StringCarrier)

        self.assertEqual(a.value, "456")

        with self.assertRaises(MissingMappingException):
            mapper.map(OptionalStringCarrier(None), StringCarrier)

    def test_forward_ref_resolving(self):
        mapper = Mapper()
        mapper.mapping(ForwardRefCarrier, dict).map_matching().register()
        mapper.mapping(ForwardReferenced, dict).map_matching().register()

        a = mapper.map({"value": {"value": "abc"}}, ForwardRefCarrier)

        self.assertEqual(a.__class__, ForwardRefCarrier)
        self.assertEqual(a.value.__class__, ForwardReferenced)
        self.assertEqual(a.value.value, "abc")
