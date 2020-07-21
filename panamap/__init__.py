import pkg_resources
from panamap.panamap import Mapper, MappingException, MissingMappingException, ImproperlyConfiguredException

__version__ = pkg_resources.resource_string(__name__, 'panamap.version').decode('utf-8').strip()

