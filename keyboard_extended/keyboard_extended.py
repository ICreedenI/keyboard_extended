import typing
import uuid
from time import time

from keyboard import *


event_keys = []
user_keys = []
user_to_event_keys = {}


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
        key = self._get_user_key_from_event(event)
        key.update(event)
        key.check_for_callbacks()

    def _get_user_key_from_event(self, event: KeyboardEvent):
        def get_key_from_event(event: KeyboardEvent):
            reduced = [(n, s, kp) for (n, s, kp, k) in event_keys]
            keys = [k for (n, s, kp, k) in event_keys]
            try:
                index = reduced.index((event.name, event.scan_code, event.is_keypad))
                key = keys[index]
            except:
                key = Key._from_event(event)
            return key

        for entry in user_keys:
            name, scan_codes, is_keypad, key = entry
            key: Key
            if event.is_keypad == is_keypad:
                if event.name == name or event.scan_code in scan_codes:
                    break
        else:
            key = get_key_from_event(event)
        return key


class Key:
    keys: dict = {}
    keys_by_scan_codes: dict = {}
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

        Key.keys[name] = self

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
        )
        event_keys.append((self.name, self.scan_code, self.is_keypad, self))
        return self

    @classmethod
    def _from_name(cls, name: str, is_keypad: bool = False):
        name = name
        scan_codes = key_to_scan_codes(name)
        self = cls(
            name,
            scan_codes,
            is_keypad=is_keypad,
        )

        def find_key_in_event_keys(scan_codes, is_keypad) -> Key | None:
            reduced = [(s, kp) for (n, s, kp, k) in event_keys]
            keys = [k for (n, s, kp, k) in event_keys]
            matches = []
            for sc in scan_codes:
                try:
                    index = reduced.index((sc, is_keypad))
                    key = keys[index]
                    matches.append(key)
                except:
                    pass
            if len(matches) > 0:
                return matches[0]

        evnt = find_key_in_event_keys(scan_codes, is_keypad)

        if evnt:
            self.last_scan_code = evnt.last_scan_code
            self.state = evnt.state
            self.modifiers = evnt.modifiers
            self.last_state_change = evnt.last_state_change
            self.last_update = evnt.last_update
            self.device = evnt.device
            self.history = evnt.history
            self.history_length = evnt.history_length
            self.history_length_factor = evnt.history_length_factor

        user_keys.append((name, scan_codes, is_keypad, self))
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
    def get_key(name: str, is_keypad: bool = False):
        key = Key.keys.get(name)
        try:
            kpd = key.is_keypad
        except:
            kpd = None
        if not key or kpd != is_keypad:
            key = Key._from_name(name, is_keypad)
        return key

    def recalculate_history_length(self):
        binds = [bind for bind in self.bindings.values() if bind.type == "multipress"]
        if len(binds) == 0:
            self.history_length = 0
        else:
            presses = []
            for bind in binds:
                for key, multi_dict in bind.keys_to_multipress_times.items():
                    if key == self:
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
        max_delay: float = 0.01,
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
        self.max_delay = max_delay
        self.did_fire = False
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
        if not time() - key.last_update < self.max_delay: return False
        if self.type == "normal":
            case1 = all(
                [k.state == v for k, v in self.keys_to_states.items()]
            )  # check if all the keys are in the correct state

            case2 = (
                any(
                    [
                        round(time(), 1) == round(k.last_state_change, 1)
                        for k in self.keys_to_states.keys()
                    ]
                )  # check whether or not the key state was just changed - prior case2 has buggy behavior, where k.last_update == k.last_state_change is True since holding multiple keys doesn't trigger all the keys to update
                if not self.fire_when_hold
                else True
            )

            case3 = all([time() - k.last_update < self.max_delay for k in self.keys_to_states.keys()])

            return case1 and case2 and case3

        elif self.type == "hold":
            _time = time()
            case1 = all(
                [
                    _time - k.last_state_change >= v
                    for k, v in self.keys_to_hold_times.items()
                ]
            )  # check whether or not the key was long engough in the correct state
            case2 = (
                any(
                    [
                        round(time(), 1) == round(k.last_state_change, 1)
                        for k in self.keys_to_hold_times.keys()
                    ]
                )  # check whether or not the key state was just changed - case2 has buggy behavior
                if not self.fire_when_hold
                else True
            )
            case3 = not any(
                [k.last_state_change == 0 for k, v in self.keys_to_hold_times.items()]
            )  # verify that the key was pressed before

            case4 = all([time() - k.last_update < self.max_delay for k in self.keys_to_hold_times.keys()])

            if case1 and case3 and case4:
                if (not case2 and not self.did_fire) or self.fire_when_hold:
                    self.did_fire = True
                    return True
            elif not case1:
                self.did_fire = False
            return False

        elif self.type == "multipress":
            case1 = all(
                [
                    self.get_amount_of_states_in_time_span(
                        k, v["state"], v["time_span"]
                    )
                    >= v["presses"]
                    for k, v in self.keys_to_multipress_times.items()
                ]
            )  # check whether every key was pressed often enough in the chosen time span
            case2 = (
                any(
                    [
                        round(time(), 1) == round(k.last_state_change, 1)
                        for k in self.keys_to_multipress_times.keys()
                    ]
                )  # check whether or not the key state was just changed - case2 has buggy behavior
                if not self.fire_when_hold
                else True
            )
            case3 = all(
                [
                    k.state == v["state"]
                    for k, v in self.keys_to_multipress_times.items()
                ]
            )  # check whether all keys are in the correct state

            case4 = all([time() - k.last_update < self.max_delay for k in self.keys_to_multipress_times.keys()])

            if self.did_fire and case2 and case3:
                case1 = True  # case1 is False when key is hold down -> to fire when hold down, set it to True
            if case1 and case2 and case3:
                self.did_fire = True
            else:
                self.did_fire = False
            return case1 and case2 and case3 and case4

    @staticmethod
    def get_amount_of_states_in_time_span(
        key: Key,
        state,
        time_span,
    ):
        relevant = [x for x in key.history if x["state"] == state]
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
    is_keypad: bool = False,
    max_delay: float = 0.01
):
    """Add a normal hotkey to the given keys.

    Args:
        keys (str): The keys as a string, if multiple keys seperated by '+' (+ is than plus).
        callback (typing.Callable): Your callback, which is called when all criteria are met.
        args (typing.Iterable, optional): Your arguments to be passed to the callback function. Defaults to None.
        state (str, optional): The respective state of the button, which can be either "down" or "up". Defaults to "down".
        keys_to_states (dict[str, str], optional): May be a dictionary specifiing the (single) key name and the corresponding state for this key. The state may be a tuple containing not only the state but also the is_keypad option for this key. Defaults to None.
        fire_when_hold (bool, optional): If all criteria are met and you keep the buttons pressed, the callback is called repeatedly. Defaults to False.
        send_keys (bool, optional): Add all the keys as a list to the arguments at position 0. Defaults to False.
        is_keypad (bool, optional): All buttons on the keypad are only active if this option is set to True, but this also deactivates all buttons that are not part of the keypad. Defaults to False.
        max_delay (float, optional): The maximum delay in seconds between the keyboard event and the trigger of the callback. Defaults to 0.01.

    Returns:
        UUID: The id needed to remove the binding using the remove_binding function.
    """
    if not keys_to_states:
        keys_to_states = {k: state for k in Key._keys_from_string(keys)}
    _keys_to_states = {}
    for k, state in keys_to_states.items():
        if isinstance(state, str):
            key = Key.get_key(k, is_keypad)
            _keys_to_states[key] = state
        else:
            key = Key.get_key(k, state[1])
            _keys_to_states[key] = state[0]
    keys_to_states = _keys_to_states.copy()
    if send_keys:
        key_args = [k for k in keys_to_states.keys()]
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
        max_delay=max_delay,
    )
    for key in keys_to_states:
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
    is_keypad: bool = False,
    max_delay: float = 0.01
):
    """Add a hotkey that requires the buttons to be held down.

    Args:
        keys (str): The keys as a string, if multiple keys seperated by '+' (+ is than plus).
        callback (typing.Callable): Your callback, which is called when all criteria are met.
        args (typing.Iterable, optional): Your arguments to be passed to the callback function. Defaults to None.
        time_span (float, optional): The period of time for which the keys have to be hold down. Defaults to 1.
        keys_to_hold_times (dict[str, float], optional): May be a dictionary specifiing the (single) key name and the minimum duration for which this key has to be hold down. The duration may be a tuple containing not only the state but also the is_keypad option for this key. Defaults to None.
        continue_fire_when_hold (bool, optional): If set to True the callback function will be called repeatedly. Defaults to False.
        send_keys (bool, optional): Add all the keys as a list to the arguments at position 0. Defaults to False.
        is_keypad (bool, optional): All buttons on the keypad are only active if this option is set to True, but this also deactivates all buttons that are not part of the keypad. Defaults to False.
        max_delay (float, optional): The maximum delay in seconds between the keyboard event and the trigger of the callback. Defaults to 0.01.

    Returns:
        UUID: The id needed to remove the binding using the remove_binding function.
    """
    if not keys_to_hold_times:
        keys_to_hold_times = {k: time_span for k in Key._keys_from_string(keys)}
    _keys_to_hold_times = {}
    for k, v in keys_to_hold_times.items():
        if isinstance(v, float) or isinstance(v, int):
            key = Key.get_key(k, is_keypad)
            _keys_to_hold_times[key] = v
        else:
            key = Key.get_key(k, v[1])
            _keys_to_hold_times[key] = v[0]
    keys_to_hold_times = _keys_to_hold_times.copy()
    if send_keys:
        key_args = [k for k in keys_to_hold_times.keys()]
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
        max_delay=max_delay,
    )
    for key in keys_to_hold_times:
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
    is_keypad: bool = False,
    max_delay: float = 0.01
):
    """Add a hotkey that requires the keys to be pressed repeatedly.

    Args:
        keys (str): The keys as a string, if multiple keys seperated by '+' (+ is than plus).
        callback (typing.Callable): Your callback, which is called when all criteria are met.
        args (typing.Iterable, optional): Your arguments to be passed to the callback function. Defaults to None.
        time_span (float, optional): The period of time in which the presses must take place. Defaults to 0.5.
        presses (int, optional): The amount of which the key has to send the state. Defaults to 3.
        state (str, optional): The respective state of the button, which can be either "down" or "up" - if "up" only the "up" events of the history are relevant. Defaults to "down".
        keys_to_multipress_times (dict[str, dict[str, typing.Any]], optional): May be a dictionary specifiing the (single) key name and a corresponding dictionary containing "state", "time_span", "presses" and "is_keypad" for this key. Defaults to None.
        fire_when_hold (bool, optional): If all criteria are met and you keep the buttons pressed, the callback may be called repeatedly. Defaults to False.
        send_keys (bool, optional): Add all the keys as a list to the arguments at position 0. Defaults to False.
        is_keypad (bool, optional): All buttons on the keypad are only active if this option is set to True, but this also deactivates all buttons that are not part of the keypad. Defaults to False.
        max_delay (float, optional): The maximum delay in seconds between the keyboard event and the trigger of the callback. Defaults to 0.01.

    Returns:
        UUID: The id needed to remove the binding using the remove_binding function.
    """
    if not keys_to_multipress_times:
        keys_to_multipress_times = {
            k: {"state": state, "time_span": time_span, "presses": presses}
            for k in Key._keys_from_string(keys)
        }
    _keys_to_multipress_times = {}
    for k, v in keys_to_multipress_times.items():
        kpad = v.get("is_keypad")
        if kpad != None:
            key = Key.get_key(k, v["is_keypad"])
            _keys_to_multipress_times[key] = v
        else:
            key = Key.get_key(k, is_keypad)
            _keys_to_multipress_times[key] = v
    keys_to_multipress_times = _keys_to_multipress_times.copy()
    if send_keys:
        key_args = [k for k in keys_to_multipress_times.keys()]
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
        max_delay=max_delay,
    )
    for key in keys_to_multipress_times:
        key.bindings[binding_id] = binding
    Key._general_bindings[binding_id] = binding
    for key in keys_to_multipress_times:
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
        for key in binding.keys:
            key.recalculate_history_length()
    for key in binding.keys:
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
