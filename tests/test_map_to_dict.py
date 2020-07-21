from dataclasses import dataclass
from typing import List
from unittest import TestCase

from panamap import Mapper


@dataclass
class Nested:
    value: str


@dataclass
class A:
    nested: Nested
    list_of_nested: List[Nested]


class TestMapToDict(TestCase):
    def test_map_from_dict(self):
        mapper = Mapper()
        mapper.mapping(A, dict) \
            .map_matching() \
            .register()
        mapper.mapping(Nested, dict) \
            .map_matching() \
            .register()

        a = mapper.map(
            {
                'nested': {
                    'value': "abc",
                },
                'list_of_nested': [
                    {
                        'value': "def",
                    },
                    {
                        'value': "xyz",
                    }
                ]
            },
            A,
        )

        self.assertEqual(a.__class__, A)
        self.assertEqual(a.nested.__class__, Nested)
        self.assertEqual(a.nested.value, "abc")
        self.assertEqual(len(a.list_of_nested), 2)
        self.assertEqual(a.list_of_nested[0].__class__, Nested)
        self.assertEqual(a.list_of_nested[0].value, "def")
        self.assertEqual(a.list_of_nested[1].value, "xyz")
