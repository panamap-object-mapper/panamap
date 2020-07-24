# panamap

[![PyPI version](https://badge.fury.io/py/panamap.svg)](https://badge.fury.io/py/panamap)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/panamap)](https://pypi.org/project/panamap/)
[![Build Status](https://travis-ci.com/kirillsulim/panamap.svg?branch=master)](https://travis-ci.com/kirillsulim/panamap)
[![Coveralls github](https://img.shields.io/coveralls/github/kirillsulim/panamap)](https://coveralls.io/github/kirillsulim/panamap)


Panamap is a Python object mapper. It is useful to avoid boilerplate code when copying data between objects with
similar data, for example protobuf generated files and domain models.

## Installation


Use the package manager [pip](https://pip.pypa.io/en/stable/) to install foobar.

```bash
pip install panamap
```

## Usage

### Mapping primitive values

The most simple usage of panamap is to map primitive values:

```python
from panamap import Mapper

mapper = Mapper()
print(mapper.map("123", int) + 1)
# 124
```

### Mapping simple classes

To set up mapping call `mapping` function of mapper object.
Each field pair can be bind with `bidirectional` function or separately with `l_to_r` and `r_to_l` if we only need one
directional mapping or there is custom conversion on mapping.

Here are some examples:

```python
from panamap import Mapper

class A:
    def __init__(self, a_value: int):
        self.a_value = a_value


class B:
    def __init__(self, b_value: int):
        self.b_value = b_value

mapper = Mapper()
mapper.mapping(A, B) \
    .l_to_r("a_value", "b_value") \
    .register()

b = mapper.map(A(123), B)
print(b.b_value)
# 123
# a = mapper.map(B(123), A) will raise MissingMappingException cause we didn't set any r_to_l map rules

bidirectional_mapper = Mapper()
bidirectional_mapper.mapping(A, B) \
    .bidirectional("a_value", "b_value") \
    .register()

b = bidirectional_mapper.map(A(123), B)
print(b.b_value)
# 123
a = bidirectional_mapper.map(B(123), A)
print(a.a_value)
# 123

shifting_mapper = Mapper()
shifting_mapper.mapping(A, B) \
    .l_to_r("a_value", "b_value", lambda a: a + 1) \
    .r_to_l("a_value", "b_value", lambda b: b - 1) \
    .register()

b = shifting_mapper.map(A(123), B)
print(b.b_value)
# 124
a = shifting_mapper.map(B(123), A)
print(a.a_value)
# 122
```

### Mapping empty classes

Sometimes there is need to convert one empty class to another. For such case there is `_empty` versions of map config
functions:

```python
from panamap import Mapper

class A:
    pass

class B:
    pass

mapper = Mapper()
mapper.mapping(A, B) \
    .bidirectional_empty() \
    .register()

b = mapper.map(A(), B)
print(isinstance(b, B))
# True
```

### Mapping nested fields

Panamap supports mapping of nested fields. To perform this mapping for nested fields classes must be set up.

```python
from dataclasses import dataclass
from panamap import Mapper

@dataclass
class NestedA:
    value: str


@dataclass
class A:
    value: NestedA


@dataclass
class NestedB:
    value: str


@dataclass
class B:
    value: NestedB

mapper = Mapper()
mapper.mapping(A, B) \
    .map_matching() \
    .register()
mapper.mapping(NestedA, NestedB) \
    .map_matching() \
    .register()

b = mapper.map(A(NestedA("abc")), B)
print(isinstance(b.value, NestedB))
# True
print(b.value.value)
# abc
```

### Mapping from and to dict

Panamap allow to set up mapping frm and to dict object. Here is an example:

```python
from typing import List
from dataclasses import dataclass
from panamap import Mapper

@dataclass
class Nested:
    value: str


@dataclass
class A:
    nested: Nested
    list_of_nested: List[Nested]

mapper = Mapper()
mapper.mapping(A, dict) \
    .map_matching() \
    .register()
mapper.mapping(Nested, dict) \
    .map_matching() \
    .register()

a = mapper.map({
    "nested": {
        "value": "abc",
    },
    "list_of_nested": [
        {"value": "def",},
        {"value": "xyz",},
    ]},
    A,
)
print(a)
# A(nested=Nested(value='abc'), list_of_nested=[Nested(value='def'), Nested(value='xyz')])
```

### Mapping protobuf generated classes

To map protobuf generated classes use separate module [panamap-proto](https://github.com/kirillsulim/panamap-proto). 

## Contributing

Contributing described in [separate document](docs/contributing.md).
