from unittest import TestCase

from panamap import Mapper, MissingMappingException


class TestMapEmptyClasses(TestCase):
    def test_map_empty_class_l_to_r(self):
        class A:
            pass

        class B:
            pass

        l_to_r_mapper = Mapper()
        l_to_r_mapper.mapping(A, B) \
            .l_to_r_empty() \
            .register()

        b = l_to_r_mapper.map(A(), B)

        self.assertEqual(b.__class__, B)

    def test_map_empty_class_r_to_l(self):
        class A:
            pass

        class B:
            pass

        r_to_l_mapper = Mapper()
        r_to_l_mapper.mapping(A, B) \
            .r_to_l_empty() \
            .register()

        a = r_to_l_mapper.map(B(), A)

        self.assertEqual(a.__class__, A)

    def test_map_empty_class_bidirectional(self):
        class A:
            pass

        class B:
            pass

        bi_d_mapper = Mapper()
        bi_d_mapper.mapping(A, B) \
            .bidirectional_empty() \
            .register()

        b = bi_d_mapper.map(A(), B)

        self.assertEqual(b.__class__, B)

        a = bi_d_mapper.map(B(), A)

        self.assertEqual(a.__class__, A)

    def test_raise_exception_when_reverse_map_is_not_set(self):
        class A:
            pass

        class B:
            pass

        mapper = Mapper()
        mapper.mapping(A, B) \
            .l_to_r_empty() \
            .register()

        with self.assertRaises(MissingMappingException):
            mapper.map(B(), A)
