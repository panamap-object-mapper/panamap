from typing import Type, Any, TypeVar, Callable, Generic, List, Optional, Dict, Iterable, Set, Union, Tuple
from abc import ABC, abstractmethod
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


class ImproperlyConfiguredException(MappingException):
    def __init__(self, l: Type, r: Type, error: str):
        super(ImproperlyConfiguredException, self).__init__(f"Mapping from '{l}' to '{r}' is improperly configured: {error}")


class FieldMappingException(MappingException):
    def __init__(self, l: Type, r: Type, l_field: str, r_field: str, error: str):
        super(MappingException, self).__init__(f"Cannot map field '{l_field}' of type '{l}' to field '{r_field} of type '{r}': '{error}'")


L = TypeVar('L')
R = TypeVar('R')


@dataclass
class FieldMapRule(Generic[L, R]):
    from_field: str
    from_field_getter: Callable[[L], Any]
    to_field: str
    to_field_is_constructor_arg: bool
    to_field_setter: Optional[Callable[[R, Any], None]]

    from_field_type: Optional[Type[Any]] = None
    to_field_type: Optional[Type[Any]] = None
    converter: Optional[Callable[[Any], Any]] = None


class MappingDescriptor(ABC, Generic[T]):
    def __init__(self, t: Type[T]):
        self.type = t

    @classmethod
    @abstractmethod
    def supports_type(cls, t: Type[Any]) -> bool:
        pass

    @abstractmethod
    def get_getter(self, field_name: str) -> Callable[[T], Any]:
        """
        Return setter for field name
        """
        pass

    @abstractmethod
    def get_setter(self, field_name: str) -> Callable[[Dict, Any], None]:
        """
        Return getter for filed name
        """
        pass

    @abstractmethod
    def get_constructor_args(self) -> Set[str]:
        """
        Return constructor args
        """
        pass

    def is_constructor_arg(self, field_name: str) -> bool:
        """
        Checks if filed_name is constructor arg
        """
        return field_name in self.get_constructor_args()

    @abstractmethod
    def get_required_constructor_args(self) -> Set[str]:
        """
        Return required constructor args
        """
        pass

    @abstractmethod
    def get_declared_fields(self) -> Set[str]:
        """
        Return set of declared fields. Note that if filed is not declared it still can be supported.
        Used in map_matching.
        """
        pass

    @abstractmethod
    def is_field_supported(self, field_name: str) -> bool:
        """
        Checks if field can be set
        """
        pass

    @abstractmethod
    def get_preferred_field_type(self, field_name: str) -> Type[Any]:
        """
        Returns filed type if available else Any
        """
        pass

    @abstractmethod
    def is_container_type(self) -> bool:
        """
        Marks container types designed to store arbitrary fields
        """
        pass

    @staticmethod
    def uncase(field_name: str) -> str:
        return field_name.replace('_', '').lower()

    @staticmethod
    def to_uncase_dict(fields: Iterable[str]) -> Dict[str, str]:
        return {MappingDescriptor.uncase(field): field for field in fields}


class CommonTypeMappingDescriptor(MappingDescriptor):
    def __init__(self, t: Type[T]):
        super(CommonTypeMappingDescriptor, self).__init__(t)
        self.constructor_parameters = signature(t.__init__).parameters
        self.uncased_dict = self.to_uncase_dict(self.constructor_parameters.keys())

    @classmethod
    def supports_type(cls, t: Type[Any]) -> bool:
        return True

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

    def get_field_type(self, field_name: str) -> Type[Any]:
        param = self.constructor_parameters.get(field_name)
        if param is not None:
            return param.annotation
        else:
            return None

    def get_preferred_field_type(self, field_name: str) -> Type[Any]:
        param = self.constructor_parameters.get(field_name)
        if param is not None:
            return param.annotation
        else:
            return Any

    def get_constructor_args(self) -> Set[str]:
        return set(self.constructor_parameters.keys()).difference({'self'})

    def get_required_constructor_args(self) -> Set[str]:
        return {name for name, props in self.constructor_parameters.items() if props.default == props.empty}.difference({'self'})

    def get_declared_fields(self) -> Set[str]:
        return self.get_constructor_args()

    def is_field_supported(self, field_name: str) -> bool:
        return True

    def is_container_type(self) -> bool:
        return False


class DictMappingDescriptor(MappingDescriptor):
    def __init__(self, d: Type[Dict]):
        super(DictMappingDescriptor, self).__init__(d)

    @classmethod
    def supports_type(cls, t: Type[Any]) -> bool:
        return t is dict

    def get_getter(self, field_name: str) -> Callable[[Dict], Any]:
        def getter(d: Dict):
            return d.get(field_name)

        return getter

    def get_setter(self, field_name: str) -> Callable[[Dict, Any], None]:
        def setter(d: Dict, value: Any):
            d[field_name] = value

        return setter

    def get_constructor_args(self) -> Set[str]:
        return set()

    def get_required_constructor_args(self) -> Set[str]:
        return set()

    def get_declared_fields(self) -> Set[str]:
        return set()

    def is_field_supported(self, field_name: str) -> bool:
        return True

    def get_preferred_field_type(self, field_name: str) -> Type[Any]:
        return Any

    def is_container_type(self) -> bool:
        return True


class MappingConfigFlow:
    def __init__(self, mapper: 'Mapper', left_descriptor: MappingDescriptor, right_descriptor: MappingDescriptor):
        self.mapper = mapper
        self.left = left_descriptor.type
        self.left_descriptor = left_descriptor
        self.right = right_descriptor.type
        self.right_descriptor = right_descriptor

        self.l_to_r_touched = False
        self.l_to_r_map_list: List[FieldMapRule] = []

        self.r_to_l_touched = False
        self.r_to_l_map_list: List[FieldMapRule] = []

    def l_to_r(self, l_field_name: str, r_field_name: str, converter: Callable[[Any], Any] = None) -> 'MappingConfigFlow':
        left_getter = self.left_descriptor.get_getter(l_field_name)
        left_field_type = self.left_descriptor.get_preferred_field_type(l_field_name)

        right_setter = self.right_descriptor.get_setter(r_field_name)
        right_field_type = self.right_descriptor.get_preferred_field_type(r_field_name)

        if self.right_descriptor.is_constructor_arg(r_field_name):
            self.l_to_r_map_list.append(FieldMapRule(l_field_name, left_getter, r_field_name, True, None, converter=converter,
                                                     from_field_type=left_field_type, to_field_type=right_field_type))
        else:
            self.l_to_r_map_list.append(FieldMapRule(l_field_name, left_getter, r_field_name, False, right_setter, converter=converter,
                                                     from_field_type=left_field_type, to_field_type=right_field_type))
        self.l_to_r_touched = True
        return self

    def r_to_l(self, l_field_name: str, r_field_name: str, converter: Callable[[Any], Any] = None) -> 'MappingConfigFlow':
        lset = self.left_descriptor.get_setter(l_field_name)
        ltype = self.left_descriptor.get_preferred_field_type(l_field_name)

        rget = self.right_descriptor.get_getter(r_field_name)
        rtype = self.right_descriptor.get_preferred_field_type(r_field_name)

        if self.left_descriptor.is_constructor_arg(l_field_name):
            self.r_to_l_map_list.append(FieldMapRule(r_field_name, rget, l_field_name, True, None, converter=converter,
                                                     from_field_type=rtype, to_field_type=ltype))
        else:
            self.r_to_l_map_list.append(FieldMapRule(r_field_name, rget, l_field_name, False, lset, converter=converter,
                                                     from_field_type=rtype, to_field_type=ltype))
        self.r_to_l_touched = True
        return self

    def bidirectional(self, l_field_name: str, r_field_name: str) -> 'MappingConfigFlow':
        self.l_to_r(l_field_name, r_field_name)
        self.r_to_l(l_field_name, r_field_name)
        return self

    def l_to_r_empty(self):
        if self.l_to_r_touched:
            raise ImproperlyConfiguredException(self.left, self.right, 'empty mapping after another configuration')
        self.l_to_r_touched = True
        return self

    def r_to_l_empty(self):
        if self.r_to_l_touched:
            raise ImproperlyConfiguredException(self.left, self.right, 'empty mapping after another configuration')
        self.r_to_l_touched = True
        return self

    def bidirectional_empty(self):
        self.r_to_l_empty()
        self.l_to_r_empty()
        return self

    def map_matching(self, ignore_case: bool = False) -> 'MappingConfigFlow':
        if self.left_descriptor.is_container_type() and self.right_descriptor.is_container_type():
            raise ImproperlyConfiguredException(self.left, self.right, 'map matching for two container types doesn\'t make sense')
        if ignore_case and (self.left_descriptor.is_container_type() or self.right_descriptor.is_container_type()):
            raise ImproperlyConfiguredException(self.left, self.right, 'map matching for container types with ignored case does not supported yet')

        if ignore_case:
            l_fields = MappingDescriptor.to_uncase_dict(self.left_descriptor.get_declared_fields())
            r_fields = MappingDescriptor.to_uncase_dict(self.right_descriptor.get_declared_fields())
        else:
            l_fields = {f: f for f in self.left_descriptor.get_declared_fields()}
            r_fields = {f: f for f in self.right_descriptor.get_declared_fields()}

        if self.left_descriptor.is_container_type():
            common_fields = set(r_fields.keys())
            l_fields = r_fields
        elif self.right_descriptor.is_container_type():
            common_fields = set(l_fields.keys())
            r_fields = l_fields
        else:
            common_fields = set(l_fields.keys()).intersection(r_fields.keys())
        for field in common_fields:
            lf_name = l_fields[field]
            rf_name = r_fields[field]
            self.bidirectional(lf_name, rf_name)
        return self

    def register(self) -> None:
        if self.l_to_r_touched:
            self.mapper._add_map_rules(self.left, self.right, self.l_to_r_map_list)
        if self.r_to_l_touched:
            self.mapper._add_map_rules(self.right, self.left, self.r_to_l_map_list)


class Mapper:
    DEFAULT_DESCRIPTORS: List[Type[MappingDescriptor]] = [
        DictMappingDescriptor,
        CommonTypeMappingDescriptor,
    ]

    PRIMITIVE_CONVERTERS: Dict[Tuple[Type[Any], Type[Any]], Callable[[Any], Any]] = {
        (int, str): str,
        (int, float): float,
        (float, str): str,
        (str, int): int,
        (str, float): float,
        (str, bytes): lambda s: s.encode('utf-8'),
    }

    def __init__(self, custom_descriptors: Optional[List[Type[MappingDescriptor]]] = None):
        self.map_rules: Dict[Type, Dict[Type, List[FieldMapRule]]] = {}
        self.custom_descriptors = custom_descriptors if custom_descriptors else []

    def mapping(self, a: Union[Type, MappingDescriptor], b: Union[Type, MappingDescriptor]) -> MappingConfigFlow:
        if isinstance(a, Type):
            a = self._wrap_type_to_descriptor(a)
        if isinstance(b, Type):
            b = self._wrap_type_to_descriptor(b)
        return MappingConfigFlow(self, a, b)

    def _wrap_type_to_descriptor(self, t: Type[Any]):
        for d in self.custom_descriptors + self.DEFAULT_DESCRIPTORS:
            if d.supports_type(t):
                return d(t)
        else:
            raise Exception(f"Cannot found descriptor for type '{t}'")

    def _add_map_rules(self, a: Type, b: Type, rules: List[FieldMapRule]):
        a_type_mappings = self.map_rules.setdefault(a, {})
        if b in a_type_mappings:
            raise DuplicateMappingException(a, b)

        a_type_mappings[b] = rules

    def map(self, a_obj: Any, b: Type[T]) -> T:
        a = a_obj.__class__
        if not self._has_mapping(a, b):
            raise MissingMappingException(a, b)

        constructor_args = {}
        other_fields_operations = []
        for rule in self.map_rules[a][b]:
            getter = rule.from_field_getter
            setter = rule.to_field_setter
            converter = rule.converter
            from_type = rule.from_field_type
            to_type = rule.to_field_type

            if converter is not None:
                def wrapped_getter(b_obj: Type[T]) -> Any:
                    try:
                        return converter(rule.from_field_getter(b_obj))
                    except Exception as e:
                        raise FieldMappingException(a, b, rule.from_field, rule.to_field, 'exception on value conversion') from e

                getter = wrapped_getter

            elif self._has_mapping(from_type, to_type):
                def wrapped_getter(b_obj: Type[T]) -> Any:
                    try:
                        return self.map(rule.from_field_getter(b_obj), to_type)
                    except Exception as e:
                        raise FieldMappingException(a, b, rule.from_field, rule.to_field, 'exception on mapping nesting class') from e

                getter = wrapped_getter

            elif (from_type, to_type) in self.PRIMITIVE_CONVERTERS:
                def wrapped_getter(b_obj: Type[T]) -> Any:
                    primitive_converter = self.PRIMITIVE_CONVERTERS[(from_type, to_type)]
                    try:
                        return primitive_converter(rule.from_field_getter(b_obj))
                    except Exception as e:
                        raise FieldMappingException(a, b, rule.from_field, rule.to_field, 'exception on mapping primitive values') from e

                getter = wrapped_getter

            if rule.to_field_is_constructor_arg:
                constructor_args[rule.to_field] = getter(a_obj)
            else:
                value = getter(a_obj)
                other_fields_operations.append((setter, value))

        b_obj = b(**constructor_args)
        for op in other_fields_operations:
            setter, value = op
            setter(b_obj, value)

        return b_obj

    def _has_mapping(self, a: Type[Any], b: Type[Any]) -> bool:
        return a in self.map_rules and b in self.map_rules[a]
