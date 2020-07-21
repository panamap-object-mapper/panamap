from typing import Type, Any, TypeVar, Callable, Generic, List, Optional, Dict, Iterable, Set, Union, Tuple
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from inspect import signature

from typing_inspect import get_origin, get_args


class MappingException(Exception):
    pass


@dataclass
class FieldMappingExceptionInfo:
    a: Type[Any]
    b: Type[Any]
    a_fields_chain: List[str] = field(default_factory=list)
    b_fields_chain: List[str] = field(default_factory=list)

    def has_fields_chain(self):
        return 0 < len(self.a_fields_chain) or 0 < len(self.b_fields_chain)


class DuplicateMappingException(MappingException):
    def __init__(self, left: Type, right: Type):
        super(DuplicateMappingException, self).__init__(
            f"Mapping from '{left.__name__}' to '{right.__name__}' already defined."
        )


class MissingMappingException(MappingException):
    def __init__(self, left: Type, right: Type):
        super(MissingMappingException, self).__init__(
            f"Mapping from '{left.__name__}' to '{right.__name__}' is not defined."
        )


class ImproperlyConfiguredException(MappingException):
    def __init__(self, left: Type, right: Type, error: str):
        super(ImproperlyConfiguredException, self).__init__(
            f"Mapping from '{left.__name__}' to '{right.__name__}' is improperly configured: {error}"
        )


class UnsupportedFieldException(MappingException):
    def __init__(self, t: Type, field_name: str):
        super(UnsupportedFieldException, self).__init__(f"Unsupported field '{field_name}' for type '{t,__name__}'")


class FieldMappingException(MappingException):
    def __init__(self, error: str, exc_info: Optional[FieldMappingExceptionInfo] = None):
        if exc_info is None:
            message = error
        elif exc_info.has_fields_chain():
            message = (
                f"Cannot map field '{'.'.join(exc_info.a_fields_chain)}' of type '{exc_info.a.__name__}' to "
                f"field '{'.'.join(exc_info.b_fields_chain)}' of type '{exc_info.b.__name__}': {error}"
            )
        else:
            message = f"Cannot map type '{exc_info.a}' to type '{exc_info.b}': {error}"
        super(MappingException, self).__init__(message)


T = TypeVar("T")
F = TypeVar("F")


@dataclass
class FieldDescriptor(Generic[T, F]):
    name: str
    type: Type[F]
    getter: Callable[[T], F]
    setter: Optional[Callable[[T, F], None]]
    is_constructor_arg: bool


T1 = TypeVar("T1")
T2 = TypeVar("T2")
F1 = TypeVar("F1")
F2 = TypeVar("F2")


@dataclass
class FieldMapRule(Generic[T1, F1, T2, F2]):
    from_field: FieldDescriptor[T1, F1]
    to_field: FieldDescriptor[T2, F2]
    converter: Optional[Callable[[F1], F2]]
    check_types: bool


class MappingDescriptor(ABC, Generic[T]):
    def __init__(self, t: Type[T]):
        self.type = t

    @classmethod
    @abstractmethod
    def supports_type(cls, t: Type[Any]) -> bool:
        pass

    def get_field_descriptor(self, field_name: str) -> Optional[FieldDescriptor[T, F]]:
        if self.is_field_supported(field_name):
            return FieldDescriptor(
                name=field_name,
                type=self.get_preferred_field_type(field_name),
                getter=self.get_getter(field_name),
                setter=self.get_setter(field_name),
                is_constructor_arg=self.is_constructor_arg(field_name),
            )
        else:
            return None

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
        return field_name.replace("_", "").lower()

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
            return set(self.uncased_dict.keys()).difference({"self"})
        else:
            return set(self.constructor_parameters.keys()).difference({"self"})

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
            return Any

    def get_preferred_field_type(self, field_name: str) -> Type[Any]:
        param = self.constructor_parameters.get(field_name)
        if param is not None:
            return param.annotation
        else:
            return Any

    def get_constructor_args(self) -> Set[str]:
        return set(self.constructor_parameters.keys()).difference({"self"})

    def get_required_constructor_args(self) -> Set[str]:
        return {name for name, props in self.constructor_parameters.items() if props.default == props.empty}.difference(
            {"self"}
        )

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
    def __init__(self, mapper: "Mapper", left_descriptor: MappingDescriptor, right_descriptor: MappingDescriptor):
        self.mapper = mapper
        self.left = left_descriptor.type
        self.left_descriptor = left_descriptor
        self.right = right_descriptor.type
        self.right_descriptor = right_descriptor

        self.l_to_r_touched = False
        self.l_to_r_map_list: List[FieldMapRule] = []

        self.r_to_l_touched = False
        self.r_to_l_map_list: List[FieldMapRule] = []

    def l_to_r(
        self, left_field_name: str, right_field_name: str, converter: Callable[[Any], Any] = None, check_types=True
    ) -> "MappingConfigFlow":
        left_field = self.left_descriptor.get_field_descriptor(left_field_name)
        if left_field is None:
            raise UnsupportedFieldException(self.left_descriptor.type, left_field_name)

        right_field = self.right_descriptor.get_field_descriptor(right_field_name)
        if right_field is None:
            raise UnsupportedFieldException(self.right_descriptor.type, right_field_name)

        self.l_to_r_map_list.append(
            FieldMapRule(from_field=left_field, to_field=right_field, converter=converter, check_types=check_types)
        )
        self.l_to_r_touched = True
        return self

    def r_to_l(
        self, left_field_name: str, right_field_name: str, converter: Callable[[Any], Any] = None, check_types=True
    ) -> "MappingConfigFlow":
        left_field = self.left_descriptor.get_field_descriptor(left_field_name)
        if left_field is None:
            raise UnsupportedFieldException(self.left_descriptor.type, left_field_name)

        right_field = self.right_descriptor.get_field_descriptor(right_field_name)
        if right_field is None:
            raise UnsupportedFieldException(self.right_descriptor.type, right_field_name)

        self.r_to_l_map_list.append(
            FieldMapRule(from_field=right_field, to_field=left_field, converter=converter, check_types=check_types)
        )
        self.r_to_l_touched = True
        return self

    def bidirectional(self, l_field_name: str, r_field_name: str, check_types=True) -> "MappingConfigFlow":
        self.l_to_r(l_field_name, r_field_name, check_types=check_types)
        self.r_to_l(l_field_name, r_field_name, check_types=check_types)
        return self

    def l_to_r_empty(self):
        if self.l_to_r_touched:
            raise ImproperlyConfiguredException(self.left, self.right, "empty mapping after another configuration")
        self.l_to_r_touched = True
        return self

    def r_to_l_empty(self):
        if self.r_to_l_touched:
            raise ImproperlyConfiguredException(self.left, self.right, "empty mapping after another configuration")
        self.r_to_l_touched = True
        return self

    def bidirectional_empty(self):
        self.r_to_l_empty()
        self.l_to_r_empty()
        return self

    def map_matching(self, ignore_case: bool = False, check_types=True) -> "MappingConfigFlow":
        if self.left_descriptor.is_container_type() and self.right_descriptor.is_container_type():
            raise ImproperlyConfiguredException(
                self.left, self.right, "map matching for two container types doesn't make sense"
            )
        if ignore_case and (self.left_descriptor.is_container_type() or self.right_descriptor.is_container_type()):
            raise ImproperlyConfiguredException(
                self.left, self.right, "map matching for container types with ignored case does not supported yet"
            )

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
        for f in common_fields:
            lf_name = l_fields[f]
            rf_name = r_fields[f]
            self.bidirectional(lf_name, rf_name, check_types=check_types)
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
        (str, bytes): lambda s: s.encode("utf-8"),
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

    def map(self, a_obj: Any, b: Type[T], exc_info: Optional[FieldMappingExceptionInfo] = None) -> T:
        a = a_obj.__class__
        if exc_info is None:
            exc_info = FieldMappingExceptionInfo(a, b)

        if a == b or b is Any:
            return a_obj
        elif self._has_mapping(a, b):
            return self._map_with_map_rules(a_obj, b, exc_info)
        elif self._is_iterable_mapping_possible(a, b):
            return self._map_iterables(a_obj, b, exc_info)
        elif self._has_primitive_mapping(a, b):
            return self._map_primitives(a_obj, b, exc_info)
        else:
            raise MissingMappingException(a, b)

    def _has_mapping(self, a: Type[Any], b: Type[Any]) -> bool:
        return a in self.map_rules and b in self.map_rules[a]

    def _map_with_map_rules(self, a_obj: Any, b: Type[Any], exc_info: FieldMappingExceptionInfo):
        a = a_obj.__class__

        constructor_args = {}
        fields = []

        for rule in self.map_rules[a][b]:
            fields_exc_info = FieldMappingExceptionInfo(
                rule.from_field.type,
                rule.to_field.type,
                exc_info.a_fields_chain + [rule.from_field.name],
                exc_info.b_fields_chain + [rule.to_field.name],
            )
            if rule.converter is not None:
                try:
                    value = rule.converter(rule.from_field.getter(a_obj))
                except Exception as e:
                    raise FieldMappingException("Error on value conversion", fields_exc_info) from e
            else:
                value = self.map(rule.from_field.getter(a_obj), rule.to_field.type, fields_exc_info)

            if rule.to_field.is_constructor_arg:
                constructor_args[rule.to_field.name] = value
            else:
                fields.append((rule.to_field.setter, value))

        b_obj = b(**constructor_args)
        for op in fields:
            setter, value = op
            setter(b_obj, value)

        return b_obj

    def _has_primitive_mapping(self, a: Type[Any], b: Type[Any]) -> bool:
        return (a, b) in self.PRIMITIVE_CONVERTERS

    def _map_primitives(self, a_obj: Any, b: Type[Any], exc_info: FieldMappingExceptionInfo):
        a = a_obj.__class__
        primitive_converter = self.PRIMITIVE_CONVERTERS[(a, b)]
        try:
            return primitive_converter(a_obj)
        except Exception as e:
            raise FieldMappingException("Exception on mapping primitive values", exc_info) from e

    def _is_iterable_mapping_possible(self, a: Type[Any], b: Type[Any]) -> bool:
        return self._is_iterable(a) and self._is_iterable(b)

    def _map_iterables(self, a_obj: Any, b: Type[Any], exc_info: FieldMappingExceptionInfo):
        args = get_args(b)
        if len(args) == 0:
            # Iterable without type
            to_type = get_origin(b)

            try:
                return to_type(*a_obj)
            except Exception as e:
                raise FieldMappingException("Error on mapping iterable", exc_info) from e

        elif len(args) == 1:
            # Iterable with type
            to_type = get_origin(b)
            to_type_item = args[0]

            mapped_list = []
            for index, item in enumerate(a_obj):
                try:
                    mapped_list.append(self.map(item, to_type_item))
                except Exception as e:
                    raise FieldMappingException(f"Error on mapping iterable at index {index}", exc_info) from e
            return to_type(mapped_list)

        else:
            # Tuple
            to_type = get_origin(b)

            mapped_list = []
            for index, item in enumerate(a_obj):
                to_type_item = args[index]

                try:
                    mapped_list.append(self.map(item, to_type_item))
                except Exception as e:
                    raise FieldMappingException(f"Error on mapping iterable at index {index}", exc_info) from e

            return to_type(mapped_list)

    @staticmethod
    def _is_iterable(t: Type[Any]):
        origin = get_origin(t)
        return origin in [list, set, tuple] or t in [list, set, tuple]
