from unittest import TestCase

from panamap import Mapper


class TestMapper(TestCase):
    def test_map_primitive_class(self):
        class A:
            def __init__(self, value):
                self.value = value

        class B:
            def __init__(self, value):
                self.value = value

        mapper = Mapper()
        mapper.mapping(A, B) \
            .l_to_r("value", "value") \
            .register()

        b = mapper.map(A(123), B)

        self.assertEqual(b.__class__, B)
        self.assertEqual(b.value, 123)
