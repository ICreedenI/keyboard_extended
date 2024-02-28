# from .KeyboardClass import Key, get_Key, getKey, unbind_all_hotkeys
from keyboard import *
from .keyboard_extended import KeyboardListener, Key, Binding, bind_hotkey, bind_hotkey_hold, bind_hotkey_multipress, remove_binding, remove_all_bindings

__version__ = "0.2.0"
