from typing import Type, Any, TypeVar, Callable, Generic, List, Optional, Dict, Iterable, Set
from dataclasses import dataclass
from inspect import signature


T = TypeVar('T')


class MappingException(Exception):
    pass


class DuplicateMappingException(MappingException):
    def __init__(self, l: Type, r: Type):
        super(DuplicateMappingException, self).__init__(f"Mapping from '{l}' to '{r}' already defined.")


class MissingMappingException(MappingException):
    def __init__(self, l: Type, r: Type):
        super(MissingMappingException, self).__init__(f"Mapping from '{l}' to '{r}' is not defined.")


class FieldMappingException(MappingException):
    def __init__(self, l: Type, r: Type, l_field: str, r_field: str, error: str):
        super(MappingException, self).__init__(f"Cannot map field '{l_field}' of type '{l}' to field '{r_field} of type '{r}' because of '{error}'")


L = TypeVar('L')
R = TypeVar('R')


@dataclass
class FieldMapRule(Generic[L, R]):
    l_field_name: str
    l_field_getter: Callable[[L], Any]
    r_field_name: str
    r_field_is_constructor_arg: bool
    r_field_setter: Optional[Callable[[R, Any], None]]
    converter: Optional[Callable[[Any], Any]]


def uncase(field_name: str) -> str:
    return field_name.replace('_', '').lower()


def to_uncase_dict(fields: Iterable[str]) -> Dict[str, str]:
    return {uncase(field): field for field in fields}


class CommonTypeDescriptor(Generic[T]):
    def __init__(self, t: Type[T]):
        self.constructor_parameters = signature(t.__init__).parameters
        self.uncased_dict = to_uncase_dict(self.constructor_parameters.keys())

    def get_field_names(self, ignore_case: bool) -> Set[str]:
        if ignore_case:
            return set(self.uncased_dict.keys()).difference({'self'})
        else:
            return set(self.constructor_parameters.keys()).difference({'self'})

    def get_canonical_field_name(self, field_name: str):
        if field_name in self.constructor_parameters:
            return field_name
        else:
            return self.uncased_dict.get(field_name)

    def get_getter(self, field_name: str) -> Callable[[T], Any]:
        def getter(obj: T):
            if hasattr(obj, field_name):
                return getattr(obj, field_name)

        return getter

    def get_setter(self, field_name: str) -> Callable[[T, Any], None]:
        def setter(obj, value):
            setattr(obj, field_name, value)

        return setter

    def is_constructor_param(self, field_name) -> bool:
        return field_name in self.constructor_parameters


class MappingConfigFlow:
    def __init__(self, mapper: 'Mapper', left: Type, right: Type):
        self.mapper = mapper
        self.left = left
        self.left_descr = CommonTypeDescriptor(left)
        self.right = right
        self.right_descr = CommonTypeDescriptor(right)

        self.l_to_r_touched = False
        self.l_to_r_map_list: List[FieldMapRule] = []

        self.r_to_l_touched = False
        self.r_to_l_map_list: List[FieldMapRule] = []

    def l_to_r(self, l_field_name: str, r_field_name: str, converter: Callable[[Any], Any] = None) -> 'MappingConfigFlow':
        lget = self.left_descr.get_getter(l_field_name)
        rset = self.right_descr.get_setter(r_field_name)
        if self.right_descr.is_constructor_param(r_field_name):
            self.l_to_r_map_list.append(FieldMapRule(l_field_name, lget, r_field_name, True, None, converter))
        else:
            self.l_to_r_map_list.append(FieldMapRule(l_field_name, lget, r_field_name, False, rset, converter))
        self.l_to_r_touched = True
        return self

    def r_to_l(self, l_field_name: str, r_field_name: str, converter: Callable[[Any], Any] = None) -> 'MappingConfigFlow':
        lset = self.left_descr.get_setter(l_field_name)
        rget = self.right_descr.get_getter(r_field_name)
        if self.left_descr.is_constructor_param(l_field_name):
            self.r_to_l_map_list.append(FieldMapRule(r_field_name, rget, l_field_name, True, None, converter))
        else:
            self.r_to_l_map_list.append(FieldMapRule(r_field_name, rget, l_field_name, False, lset, converter))
        self.r_to_l_touched = True
        return self

    def bidirectional(self, l_field_name: str, r_field_name: str) -> 'MappingConfigFlow':
        self.l_to_r(l_field_name, r_field_name)
        self.r_to_l(l_field_name, r_field_name)
        return self

    def l_to_r_empty(self):
        self.l_to_r_touched = True
        return self

    def r_to_l_empty(self):
        self.r_to_l_touched = True
        return self

    def bidirectional_empty(self):
        self.r_to_l_empty()
        self.l_to_r_empty()
        return self

    def map_matching(self, ignore_case: bool = False) -> 'MappingConfigFlow':
        l_fields = self.left_descr.get_field_names(ignore_case)
        r_fields = self.right_descr.get_field_names(ignore_case)
        common_fields = l_fields.intersection(r_fields)
        for field in common_fields:
            lf_name = self.left_descr.get_canonical_field_name(field)
            if lf_name is None:
                raise Exception(f"Not found canonical name for uncased '{field}' for class {self.left}")
            rf_name = self.right_descr.get_canonical_field_name(field)
            if rf_name is None:
                raise Exception(f"Not found canonical name for uncased '{field}' for class {self.right}")

            self.bidirectional(lf_name, rf_name)
        return self

    def register(self) -> None:
        if self.l_to_r_touched:
            self.mapper._add_map_rules(self.left, self.right, self.l_to_r_map_list)
        if self.r_to_l_touched:
            self.mapper._add_map_rules(self.right, self.left, self.r_to_l_map_list)


class Mapper:
    def __init__(self):
        self.map_rules: Dict[Type, Dict[Type, List[FieldMapRule]]] = {}

    def mapping(self, a: Type, b: Type) -> MappingConfigFlow:
        return MappingConfigFlow(self, a, b)

    def _add_map_rules(self, a: Type, b: Type, rules: List[FieldMapRule]):
        a_type_mappings = self.map_rules.setdefault(a, {})
        if b in a_type_mappings:
            raise DuplicateMappingException(a, b)

        a_type_mappings[b] = rules

    def map(self, a_obj: Any, b: Type[T]) -> T:
        a = a_obj.__class__
        if a not in self.map_rules or b not in self.map_rules[a]:
            raise MissingMappingException(a, b)

        constructor_args = {}
        other_fields_operations = []
        for rule in self.map_rules[a][b]:
            getter = rule.l_field_getter
            setter = rule.r_field_setter
            converter = rule.converter

            if converter is not None:
                def wrapped_getter(b_obj: Type[T]) -> Any:
                    try:
                        return converter(rule.l_field_getter(b_obj))
                    except Exception as e:
                        raise FieldMappingException(a, b, rule.l_field_name, rule.r_field_name, 'exception on value conversion') from e

                getter = wrapped_getter

            if rule.r_field_is_constructor_arg:
                constructor_args[rule.r_field_name] = getter(a_obj)
            else:
                other_fields_operations.append(lambda l, r: setter(r, getter(l)))

        b_obj = b(**constructor_args)
        for op in other_fields_operations:
            op(a_obj, b_obj)

        return b_obj

