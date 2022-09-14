from .KeyboardClass import Key, get_Key, getKey, unbind_all_hotkeys
from keyboard import *

from ._version import get_versions

__version__ = get_versions()["version"]
del get_versions

from . import _version
__version__ = _version.get_versions()['version']
