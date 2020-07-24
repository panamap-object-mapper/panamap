from dataclasses import dataclass
from typing import List
from unittest import TestCase

from panamap import Mapper, ImproperlyConfiguredException


@dataclass
class Simple:
    value: str


@dataclass
class Nested:
    value: str


@dataclass
class A:
    nested: Nested
    list_of_nested: List[Nested]


@dataclass
class SimpleWithDefaultValue:
    value: str = "Default value"


class TestMapToDict(TestCase):
    def test_raise_exception_on_mapping_dict_to_dict(self):
        mapper = Mapper()
        with self.assertRaises(ImproperlyConfiguredException):
            mapper.mapping(dict, dict).map_matching().register()

    def test_simple_map_to_dict(self):
        mapper = Mapper()
        mapper.mapping(Simple, dict).map_matching().register()

        s = mapper.map({"value": "abc"}, Simple)

        self.assertEqual(s.__class__, Simple)
        self.assertEqual(s.value, "abc")

        d = mapper.map(Simple("def"), dict)

        self.assertEqual(d, {"value": "def"})

    def test_map_from_dict(self):
        mapper = Mapper()
        mapper.mapping(A, dict).map_matching().register()
        mapper.mapping(Nested, dict).map_matching().register()

        a = mapper.map({"nested": {"value": "abc",}, "list_of_nested": [{"value": "def",}, {"value": "xyz",}]}, A,)

        self.assertEqual(a.__class__, A)
        self.assertEqual(a.nested.__class__, Nested)
        self.assertEqual(a.nested.value, "abc")
        self.assertEqual(len(a.list_of_nested), 2)
        self.assertEqual(a.list_of_nested[0].__class__, Nested)
        self.assertEqual(a.list_of_nested[0].value, "def")
        self.assertEqual(a.list_of_nested[1].value, "xyz")

    def test_map_missing_value_to_default(self):
        mapper = Mapper()
        mapper.mapping(SimpleWithDefaultValue, dict).map_matching().register()

        a = mapper.map({}, SimpleWithDefaultValue)
        self.assertEqual(a.value, "Default value")
