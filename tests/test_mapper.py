from unittest import TestCase

from panamap import Mapper, MissingMappingException


class TestMapper(TestCase):
    def test_map_primitive_class_l_to_r(self):
        class A:
            def __init__(self, a_value: int):
                self.a_value = a_value

        class B:
            def __init__(self, b_value: int):
                self.b_value = b_value

        l_to_r_mapper = Mapper()
        l_to_r_mapper.mapping(A, B) \
            .l_to_r("a_value", "b_value") \
            .register()

        b = l_to_r_mapper.map(A(123), B)

        self.assertEqual(b.__class__, B)
        self.assertEqual(b.b_value, 123)

    def test_map_primitive_class_r_to_l(self):
        class A:
            def __init__(self, a_value: int):
                self.a_value = a_value

        class B:
            def __init__(self, b_value: int):
                self.b_value = b_value

        r_to_l_mapper = Mapper()
        r_to_l_mapper.mapping(A, B) \
            .r_to_l("a_value", "b_value") \
            .register()

        a = r_to_l_mapper.map(B(456), A)

        self.assertEqual(a.__class__, A)
        self.assertEqual(a.a_value, 456)

    def test_map_primitive_class_bidirectional(self):
        class A:
            def __init__(self, a_value: int):
                self.a_value = a_value

        class B:
            def __init__(self, b_value: int):
                self.b_value = b_value

        bi_d_mapper = Mapper()
        bi_d_mapper.mapping(A, B) \
            .bidirectional("a_value", "b_value") \
            .register()

        b = bi_d_mapper.map(A(123), B)

        self.assertEqual(b.__class__, B)
        self.assertEqual(b.b_value, 123)

        a = bi_d_mapper.map(B(456), A)

        self.assertEqual(a.__class__, A)
        self.assertEqual(a.a_value, 456)

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

    def test_map_non_constructor_attributes(self):
        class A:
            def __init__(self, a_value: int):
                self.a_value = a_value

        class B:
            def __init__(self, b_value: int):
                self.b_value = b_value

        mapper = Mapper()
        mapper.mapping(A, B) \
            .l_to_r("a_value", "b_value") \
            .l_to_r("additional_value", "additional_value") \
            .register()

        a = A(123)
        a.additional_value = 456
        b = mapper.map(a, B)

        self.assertEqual(b.__class__, B)
        self.assertEqual(b.b_value, 123)
        self.assertEqual(b.additional_value, 456)

    def test_map_with_custom_converter(self):
        class A:
            def __init__(self, a_value: int):
                self.a_value = a_value

        class B:
            def __init__(self, b_value: str):
                self.b_value = b_value

        def converter(i: int) -> str:
            return f"--{i}--"

        l_to_r_mapper = Mapper()
        l_to_r_mapper.mapping(A, B) \
            .l_to_r("a_value", "b_value", converter) \
            .register()

        b = l_to_r_mapper.map(A(123), B)

        self.assertEqual(b.__class__, B)
        self.assertEqual(b.b_value, "--123--")

    def test_map_non_constructor_field_with_custom_converter(self):
        class A:
            pass

        class B:
            def __init__(self, b_value: str):
                self.b_value = b_value

        def converter(i: int) -> str:
            return f"--{i}--"

        l_to_r_mapper = Mapper()
        l_to_r_mapper.mapping(A, B) \
            .l_to_r("a_value", "b_value", converter) \
            .register()

        a = A()
        a.a_value = 123
        b = l_to_r_mapper.map(a, B)

        self.assertEqual(b.__class__, B)
        self.assertEqual(b.b_value, "--123--")

    def test_map_matching(self):
        class A:
            def __init__(self, a_value: int, common_value: str):
                self.a_value = a_value
                self.common_value = common_value

        class B:
            def __init__(self, b_value: int, common_value: str):
                self.b_value = b_value
                self.common_value = common_value

        mapper = Mapper()
        mapper.mapping(A, B) \
            .bidirectional("a_value", "b_value") \
            .map_matching() \
            .register()

        b = mapper.map(A(123, "456"), B)

        self.assertEqual(b.__class__, B)
        self.assertEqual(b.b_value, 123)
        self.assertEqual(b.common_value, "456")

        a = mapper.map(B(789, "xyz"), A)

        self.assertEqual(a.__class__, A)
        self.assertEqual(a.a_value, 789)
        self.assertEqual(a.common_value, "xyz")

    def test_map_matching_ignore_case(self):
        class A:
            def __init__(self, a_value: int, common_value: str):
                self.a_value = a_value
                self.common_value = common_value

        class B:
            def __init__(self, b_value: int, CommonValue: str):
                self.b_value = b_value
                self.CommonValue = CommonValue

        mapper = Mapper()
        mapper.mapping(A, B) \
            .bidirectional("a_value", "b_value") \
            .map_matching(ignore_case=True) \
            .register()

        b = mapper.map(A(123, "456"), B)

        self.assertEqual(b.__class__, B)
        self.assertEqual(b.b_value, 123)
        self.assertEqual(b.CommonValue, "456")

        a = mapper.map(B(789, "xyz"), A)

        self.assertEqual(a.__class__, A)
        self.assertEqual(a.a_value, 789)
        self.assertEqual(a.common_value, "xyz")
