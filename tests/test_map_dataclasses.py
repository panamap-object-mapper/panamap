from dataclasses import dataclass
from unittest import TestCase

from panamap import Mapper


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


class TestMapDataclasses(TestCase):
    def test_map_matching_dataclasses(self):
        mapper = Mapper()
        mapper.mapping(A, B) \
            .bidirectional("a_value", "b_value") \
            .map_matching() \
            .register()

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
        mapper.mapping(OuterA, OuterB) \
            .map_matching() \
            .register()
        mapper.mapping(NestedA, NestedB) \
            .map_matching() \
            .register()

        b = mapper.map(OuterA(NestedA(123)), OuterB)

        self.assertEqual(b.__class__, OuterB)
        self.assertEqual(b.nested.__class__, NestedB)
        self.assertEqual(b.nested.value, 123)