import typing
import uuid
from time import time

from keyboard import *


class KeyboardListener:
    "Start listening to keyboard events. This is necessary to add hotkeys of this package since they rely on a hook to the keyboard."
    def __init__(self, start_listening: bool = True):
        self.hook = None
        if start_listening:
            self.start_keyboard_hook()

    def start_keyboard_hook(self):
        self.hook = hook(self._keyboard_hook)

    def stop_keyboard_hook(self):
        if self.hook:
            self.hook = unhook(self.hook)

    def _keyboard_hook(self, event: KeyboardEvent):
        key: Key = Key.get_key(event.name)
        if not key:
            key = Key._from_event(event)
        else:
            key.update(event)
            key.check_for_callbacks()


class Key:
    keys: dict = {}
    _general_bindings = {}

    def __init__(
        self,
        name,
        scan_code,
        event_type=None,
        modifiers=None,
        _time=0,
        device=None,
        is_keypad=None,
        event: KeyboardEvent = None,
    ) -> None:
        self.name = name
        self.scan_code = scan_code
        self.last_scan_code = scan_code
        self.state = event_type
        self.modifiers = modifiers
        self.last_state_change = _time
        self.last_update = _time
        self.device = device
        self.is_keypad = is_keypad
        self.history = []
        self.history_length = 0
        self.history_length_factor = 10
        "When using multipress binding there must be a history. The length of this is calculated by the highest amound of needed presses for multiplied with this factor. When not using any multipress binding the history length is 0."
        self.bindings: dict[uuid.UUID, Binding] = {}
        "id to binding"
        Key.keys[self.name] = self

    def __str__(self) -> str:
        return f'Key object: name: "{self.name}", state: "{self.state}", scan_code: {self.scan_code}, last_state_change: {self.last_state_change}, last_update: {self.last_update}, len(bindings): {len(self.bindings)}, is_keypad: {self.is_keypad}, device: {self.device}'

    def update(self, event: KeyboardEvent):
        self.device = event.device
        event_scan_code = (
            [
                event.scan_code,
            ]
            if isinstance(event.scan_code, int)
            else list(event.scan_code)
        )
        self_scan_code = (
            [
                self.scan_code,
            ]
            if isinstance(self.scan_code, int)
            else list(self.scan_code)
        )
        self.scan_code = tuple(
            self_scan_code + [x for x in event_scan_code if x not in self_scan_code]
        )
        self.last_scan_code = event.scan_code
        self.is_keypad = event.is_keypad
        self.modifiers = event.modifiers
        self.last_update = event.time
        if event.event_type != self.state:
            self.last_state_change = event.time
            self.state = event.event_type
            self.history.append(
                {
                    "state": self.state,
                    "time": event.time,
                    "last_scan_code": self.last_scan_code,
                }
            )
            while len(self.history) > self.history_length:
                self.history.pop(0)

    def get_amount_of_states_in_time_span(
        self, state, time_span, scan_codes: tuple = None
    ):
        relevant = [x for x in self.history if x["state"] == state]
        if scan_codes:
            relevant = [x for x in relevant if x["last_scan_code"] in scan_codes]
        _time = time()
        in_time_span = [x for x in relevant if x["time"] >= _time - time_span]
        return len(in_time_span)

    def check_for_callbacks(self):
        try:
            for binding in self.bindings.values():
                binding(self)
        except RuntimeError:
            return "self.bindings dictionary keys changed during iteration"

    @classmethod
    def _from_event(cls, event: KeyboardEvent):
        self = cls(
            event.name,
            event.scan_code,
            event.event_type,
            event.modifiers,
            event.time,
            event.device,
            event.is_keypad,
            event,
        )
        self.update(event)
        return self

    @classmethod
    def _from_name(cls, name: str):
        name = name
        scan_code = key_to_scan_codes(name)
        self = cls(
            name,
            scan_code,
        )
        return self

    @staticmethod
    def _keys_from_string(keys: str):
        """Getting a list of keys from the string of keys where they are + seperated"""
        if keys != "+":
            keys = keys.split("+")
        else:
            keys = [
                "+",
            ]
        return keys

    @staticmethod
    def get_key(key: str):
        k = Key.keys.get(key)
        if not k:
            scan_code = key_to_scan_codes(key, False)
            if scan_code:
                if isinstance(scan_code, int):
                    scan_code = [
                        scan_code,
                    ]
                for _key in Key.keys.values():
                    ksc = _key.scan_code if _key.scan_code else []
                    if isinstance(ksc, int):
                        ksc = [
                            ksc,
                        ]
                    if any([s in ksc for s in scan_code]) or any(
                        [s in scan_code for s in ksc]
                    ):
                        return _key
        if not k:
            k = Key._from_name(key)
        return k

    def recalculate_history_length(self):
        binds = [bind for bind in self.bindings.values() if bind.type == "multipress"]
        if len(binds) == 0:
            self.history_length = 0
        else:
            presses = []
            for bind in binds:
                for key_name, multi_dict in bind.keys_to_multipress_times.items():
                    key_scan_codes = key_to_scan_codes(key_name)
                    if isinstance(key_scan_codes, int):
                        key_scan_codes = [key_scan_codes,]
                    if key_name == self.name or any([ksc in self.scan_code for ksc in key_scan_codes]):
                        presses.append(multi_dict["presses"])
            self.history_length = max(presses) * self.history_length_factor


class Binding:
    types = {"normal", "hold", "multipress"}

    def __init__(
        self,
        _id: uuid.UUID,
        callback: typing.Callable,
        _type: str,
        args: typing.Iterable = None,
        keys_to_states: dict[str, str] = {},
        keys_to_hold_times: dict[str, float] = {},
        keys_to_multipress_times: dict[str, dict[str, typing.Any]] = {},
        fire_when_hold: bool = False,
        scan_code: int | tuple = None,
        ignore_keypad: bool = False,
    ) -> None:
        assert (
            _type in Binding.types
        )  # _type must be one of "normal", "hold", "multipress"
        self.id = _id
        self.keys_to_states = keys_to_states
        self.keys_to_hold_times = keys_to_hold_times
        self.keys_to_multipress_times = keys_to_multipress_times
        self.callback = callback
        self.type = _type
        self.args = args
        self.fire_when_hold = fire_when_hold
        self.did_fire = False
        if isinstance(scan_code, int):
            scan_code = (scan_code,)
        self.scan_code = scan_code
        self.ignore_keypad = ignore_keypad
        self.keys = (
            list(keys_to_states.keys())
            + list(keys_to_hold_times.keys())
            + list(keys_to_multipress_times.keys())
        )

    def __call__(self, key: Key):
        if self.check_conditions(key):
            if self.args:
                self.callback(*self.args)
            else:
                self.callback()

    def check_conditions(self, key: Key):
        if self.ignore_keypad and key.is_keypad:
            return False

        if self.type == "normal":
            if self.scan_code:
                last_scan_codes = []
                for k in self.keys_to_multipress_times:
                    last_scan_code = Key.get_key(k).last_scan_code
                    if isinstance(last_scan_code, int):
                        last_scan_codes.append(last_scan_code)
                    else:
                        last_scan_codes.extend(last_scan_code)
                if not all([sc in last_scan_codes for sc in self.scan_code]):
                    return False

            case1 = all(
                [Key.get_key(k).state == v for k, v in self.keys_to_states.items()]
            )  # check if all the keys are in the correct state
            case2 = (
                any(
                    [
                        Key.get_key(k).last_update == Key.get_key(k).last_state_change
                        for k in self.keys_to_states.keys()
                    ]
                )  # check whether or not the key state was just changed
                if not self.fire_when_hold
                else True
            )
            return case1 and case2

        elif self.type == "hold":
            if self.scan_code:
                last_scan_codes = []
                for k in self.keys_to_multipress_times:
                    last_scan_code = Key.get_key(k).last_scan_code
                    if isinstance(last_scan_code, int):
                        last_scan_codes.append(last_scan_code)
                    else:
                        last_scan_codes.extend(last_scan_code)
                if not all([sc in last_scan_codes for sc in self.scan_code]):
                    return False

            _time = time()
            case1 = all(
                [
                    _time - Key.get_key(k).last_state_change >= v
                    for k, v in self.keys_to_hold_times.items()
                ]
            )  # check whether or not the key was long engough in the correct state
            case2 = (
                any(
                    [
                        Key.get_key(k).last_update == Key.get_key(k).last_state_change
                        for k in self.keys_to_hold_times.keys()
                    ]
                )  # check whether or not the key state was just changed
                if not self.fire_when_hold
                else True
            )
            case3 = not any(
                [
                    Key.get_key(k).last_state_change == 0
                    for k, v in self.keys_to_hold_times.items()
                ]
            )  # verify that the key was pressed before
            if case1 and case3:
                if (not case2 and not self.did_fire) or self.fire_when_hold:
                    self.did_fire = True
                    return True
            elif not case1:
                self.did_fire = False
            return False

        elif self.type == "multipress":
            if self.scan_code:
                last_scan_codes = []
                for k in self.keys_to_multipress_times:
                    last_scan_code = Key.get_key(k).last_scan_code
                    if isinstance(last_scan_code, int):
                        last_scan_codes.append(last_scan_code)
                    else:
                        last_scan_codes.extend(last_scan_code)
                if not all([sc in last_scan_codes for sc in self.scan_code]):
                    return False

            case1 = all(
                [
                    self.get_amount_of_states_in_time_span(
                        Key.get_key(k), v["state"], v["time_span"], self.scan_code
                    )
                    >= v["presses"]
                    for k, v in self.keys_to_multipress_times.items()
                ]
            )  # check whether every key was pressed often enough in the chosen time span
            case2 = (
                any(
                    [
                        Key.get_key(k).last_update == Key.get_key(k).last_state_change
                        for k in self.keys_to_multipress_times.keys()
                    ]
                )  # check whether or not the key state was just changed
                if not self.fire_when_hold
                else True
            )
            case3 = all(
                [
                    Key.get_key(k).state == v["state"]
                    for k, v in self.keys_to_multipress_times.items()
                ]
            )  # check whether all keys are in the correct state
            if self.did_fire and case2 and case3:
                case1 = True  # case1 is False when key is hold down -> to fire when hold down, set it to True
            if case1 and case2 and case3:
                self.did_fire = True
            else:
                self.did_fire = False
            return case1 and case2 and case3

    @staticmethod
    def get_amount_of_states_in_time_span(
        key: Key, state, time_span, scan_codes: tuple = None
    ):
        relevant = [x for x in key.history if x["state"] == state]
        if scan_codes:
            relevant = [x for x in relevant if x["last_scan_code"] in scan_codes]
        _time = time()
        in_time_span = [x for x in relevant if x["time"] >= _time - time_span]
        return len(in_time_span)


def bind_hotkey(
    keys: str,
    callback: typing.Callable,
    args: typing.Iterable = None,
    state: str = "down",
    keys_to_states: dict[str, str] = None,
    fire_when_hold: bool = False,
    send_keys: bool = False,
    scan_code: int | tuple[int] = None,
    ignore_keypad: bool = False,
):
    """Add a normal hotkey to the given keys.

    Args:
        keys (str): The keys as a string, if multiple keys seperated by '+' (+ is than plus).
        callback (typing.Callable): Your callback, which is called when all criteria are met.
        args (typing.Iterable, optional): Your arguments to be passed to the callback function. Defaults to None.
        state (str, optional): The respective state of the button, which can be either "down" or "up". Defaults to "down".
        keys_to_states (dict[str, str], optional): May be a dictionary specifiing the (single) key name and the corresponding state for this key. Defaults to None.
        fire_when_hold (bool, optional): If all criteria are met and you keep the buttons pressed, the callback is called repeatedly. Defaults to False.
        send_keys (bool, optional): Add all the keys as a list to the arguments at position 0. Defaults to False.
        scan_code (int | tuple[int], optional): If you want to differentiate between keys that have the same name but different scan code (e.g. left and right shift) you can add the scan code here. You may input multiple scan codes. Reduces the relevant history of the key to events with matching scan codes. Defaults to None.
        ignore_keypad (bool, optional): With the True setting, any input via the keyboard is ignored. Defaults to False.

    Returns:
        UUID: The id needed to remove the binding using the remove_binding function.
    """
    if not keys_to_states:
        keys_to_states = {k: state for k in Key._keys_from_string(keys)}
    if send_keys:
        key_args = [Key.get_key(k) for k in keys_to_states.keys()]
        if not args:
            args = []
        args = tuple(
            [
                key_args,
            ]
            + list(args)
        )

    binding_id = uuid.uuid4()
    binding = Binding(
        _id=binding_id,
        callback=callback,
        _type="normal",
        args=args,
        keys_to_states=keys_to_states,
        fire_when_hold=fire_when_hold,
        scan_code=scan_code,
        ignore_keypad=ignore_keypad,
    )
    for key_name in keys_to_states:
        key = Key.get_key(key_name)
        key.bindings[binding_id] = binding
    Key._general_bindings[binding_id] = binding
    return binding_id


def bind_hotkey_hold(
    keys: str,
    callback: typing.Callable,
    args: typing.Iterable = None,
    time_span: float = 1,
    keys_to_hold_times: dict[str, float] = None,
    continue_fire_when_hold: bool = False,
    send_keys: bool = False,
    scan_code: int | tuple[int] = None,
    ignore_keypad: bool = False,
):
    """Add a hotkey that requires the buttons to be held down.

    Args:
        keys (str): The keys as a string, if multiple keys seperated by '+' (+ is than plus).
        callback (typing.Callable): Your callback, which is called when all criteria are met.
        args (typing.Iterable, optional): Your arguments to be passed to the callback function. Defaults to None.
        time_span (float, optional): The period of time for which the keys have to be hold down. Defaults to 1.
        keys_to_hold_times (dict[str, float], optional): May be a dictionary specifiing the (single) key name and the minimum duration for which this key has to be hold down. Defaults to None.
        continue_fire_when_hold (bool, optional): If set to True the callback function will be called repeatedly. Defaults to False.
        send_keys (bool, optional): Add all the keys as a list to the arguments at position 0. Defaults to False.
        scan_code (int | tuple[int], optional): If you want to differentiate between keys that have the same name but different scan code (e.g. left and right shift) you can add the scan code here. You may input multiple scan codes. Reduces the relevant history of the key to events with matching scan codes. Defaults to None.
        ignore_keypad (bool, optional): With the True setting, any input via the keyboard is ignored. Defaults to False.

    Returns:
        UUID: The id needed to remove the binding using the remove_binding function.
    """
    if not keys_to_hold_times:
        keys_to_hold_times = {k: time_span for k in Key._keys_from_string(keys)}
    if send_keys:
        key_args = [Key.get_key(k) for k in keys_to_hold_times.keys()]
        if not args:
            args = []
        args = tuple(
            [
                key_args,
            ]
            + list(args)
        )

    binding_id = uuid.uuid4()
    binding = Binding(
        _id=binding_id,
        callback=callback,
        _type="hold",
        args=args,
        keys_to_hold_times=keys_to_hold_times,
        fire_when_hold=continue_fire_when_hold,
        scan_code=scan_code,
        ignore_keypad=ignore_keypad,
    )
    for key_name in keys_to_hold_times:
        key = Key.get_key(key_name)
        key.bindings[binding_id] = binding
    Key._general_bindings[binding_id] = binding
    return binding_id


def bind_hotkey_multipress(
    keys: str,
    callback: typing.Callable,
    args: typing.Iterable = None,
    time_span: float = 0.5,
    presses: int = 3,
    state: str = "down",
    keys_to_multipress_times: dict[str, dict[str, typing.Any]] = None,
    fire_when_hold: bool = False,
    send_keys: bool = False,
    scan_code: int | tuple[int] = None,
    ignore_keypad: bool = False,
):
    """Add a hotkey that requires the keys to be pressed repeatedly.

    Args:
        keys (str): The keys as a string, if multiple keys seperated by '+' (+ is than plus).
        callback (typing.Callable): Your callback, which is called when all criteria are met.
        args (typing.Iterable, optional): Your arguments to be passed to the callback function. Defaults to None.
        time_span (float, optional): The period of time in which the presses must take place. Defaults to 0.5.
        presses (int, optional): The amount of which the key has to send the state. Defaults to 3.
        state (str, optional): The respective state of the button, which can be either "down" or "up" - if "up" only the "up" events of the history are relevant. Defaults to "down".
        keys_to_multipress_times (dict[str, dict[str, typing.Any]], optional): May be a dictionary specifiing the (single) key name and a corresponding dictionary containing "state", "time_span" and "presses" for this key. Defaults to None.
        fire_when_hold (bool, optional): If all criteria are met and you keep the buttons pressed, the callback may be called repeatedly. Defaults to False.
        send_keys (bool, optional): Add all the keys as a list to the arguments at position 0. Defaults to False.
        scan_code (int | tuple[int], optional): If you want to differentiate between keys that have the same name but different scan code (e.g. left and right shift) you can add the scan code here. You may input multiple scan codes. Reduces the relevant history of the key to events with matching scan codes. Defaults to None.
        ignore_keypad (bool, optional): With the True setting, any input via the keyboard is ignored. Defaults to False.

    Returns:
        UUID: The id needed to remove the binding using the remove_binding function.
    """
    if not keys_to_multipress_times:
        keys_to_multipress_times = {
            k: {"state": state, "time_span": time_span, "presses": presses}
            for k in Key._keys_from_string(keys)
        }
    if send_keys:
        key_args = [Key.get_key(k) for k in keys_to_multipress_times.keys()]
        if not args:
            args = []
        args = tuple(
            [
                key_args,
            ]
            + list(args)
        )

    binding_id = uuid.uuid4()
    binding = Binding(
        _id=binding_id,
        callback=callback,
        _type="multipress",
        args=args,
        keys_to_multipress_times=keys_to_multipress_times,
        fire_when_hold=fire_when_hold,
        scan_code=scan_code,
        ignore_keypad=ignore_keypad,
    )
    for key_name in keys_to_multipress_times:
        key = Key.get_key(key_name)
        key.bindings[binding_id] = binding
    Key._general_bindings[binding_id] = binding
    for key_name in keys_to_multipress_times:
        key: Key = Key.get_key(key_name)
        key.recalculate_history_length()
    return binding_id


def remove_binding(hotkey_id):
    """Remove a hotkey created using one of the following functions:
    - `bind_hotkey`
    - `bind_hotkey_hold`
    - `bind_hotkey_multipress`

    Args:
        hotkey_id (UUID): The id needed to remove the hotkey. This is the return value of the functions listed above.
    """
    binding: Binding = Key._general_bindings[hotkey_id]
    if binding.type == "multipress":
        for key_name in binding.keys:
            key: Key = Key.get_key(key_name)
            key.recalculate_history_length()
    for key_name in binding.keys:
        key: Key = Key.get_key(key_name)
        key.bindings.pop(hotkey_id)
    Key._general_bindings.pop(hotkey_id)


def remove_all_bindings():
    """Remove all hotkeys created using one of the following functions:
    - `bind_hotkey`
    - `bind_hotkey_hold`
    - `bind_hotkey_multipress`
    """
    ids = list(Key._general_bindings.keys())
    for hotkey_id in ids:
        remove_binding(hotkey_id)



