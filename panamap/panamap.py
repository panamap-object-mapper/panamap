from typing import Type, Any, TypeVar, Callable, Generic, List, Optional, Dict
from dataclasses import dataclass


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


class CommonTypeDescriptor(Generic[T]):
    def get_getter(self, field_name: str) -> Callable[[T], Any]:
        def getter(obj: T):
            if hasattr(obj, field_name):
                return getattr(obj, field_name)

        return getter

    def get_setter(self, field_name: str) -> Callable[[T, Any], None]:
        def setter(obj, value):
            setattr(obj, field_name, value)

        return setter



class MappingConfigFlow:
    def __init__(self, mapper: 'Mapper', left: Type, right: Type):
        self.mapper = mapper
        self.left = left
        self.left_descr = CommonTypeDescriptor()
        self.right = right
        self.right_descr = CommonTypeDescriptor()

        self.l_to_r_map_list: List[FieldMapRule] = []

    def l_to_r(self, l_field_name: str, r_field_name: str) -> 'MappingConfigFlow':

        lget = self.left_descr.get_getter(l_field_name)
        rset = self.right_descr.get_setter(r_field_name)
        self.l_to_r_map_list.append(FieldMapRule(l_field_name, lget, r_field_name, True, None))

        return self

    def r_to_l(self, l_field_name: str, r_field_name: str) -> 'MappingConfigFlow':
        return self

    def bidirectional(self, l_field_name: str, r_field_name: str) -> 'MappingConfigFlow':
        return self

    def map_matching(self) -> 'MappingConfigFlow':
        return self

    def register(self) -> None:
        self.mapper._add_map_rules(self.left, self.right, self.l_to_r_map_list)


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
        for rule in self.map_rules[a][b]:
            if rule.r_field_is_constructor_arg:
                constructor_args[rule.r_field_name] = rule.l_field_getter(a_obj)

        b_obj = b(**constructor_args)

        return b_obj

