import pkg_resources
from panamap.panamap import (  # noqa: F401
    Mapper,
    MappingException,
    MissingMappingException,
    ImproperlyConfiguredException,
    MappingDescriptor,
    UnsupportedFieldException,
)

__version__ = pkg_resources.resource_string(__name__, "panamap.version").decode("utf-8").strip()
