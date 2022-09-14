from queue import Queue
from threading import Thread
from time import sleep, time
from typing import Callable, Iterable

from keyboard import *


class Key:
    """An instance of this class allows to bind functions to keyboard actions.

    Args:
        name (str): Name of the key. Names are already assigned by the keyboard module and refer to a scan code.
        state (str, optional): Current state of the key. Can be "up" or "down". Defaults to "up".
        last_up_time (float, optional): Last time the key state was "up". Defaults to None.
        last_down_time (float, optional): Last time the key state was "down". Defaults to None.
        is_keypad (bool, optional): Wether the key is on the keypad. Defaults to None.
        scan_code (int, optional): The scan code. Will be determined with when pressed by the name. Defaults to None.
        active_modifiers (list, optional): Modifiers. Defaults to [].

    Returns:
        Key: Instance of Key for keyboard bound functions.
    """

    all_keys = []
    name_self_dict = {}
    standard_modifiers = frozenset(
        [
            "alt",
            "linke windows",
            "rechte windows",
            "strg",
            "umschalt",
            "feststell",
            "tab",
            "strg",
            "anwendung",
        ]
    )
    aliase = {
        "windows": ["linke windows", "rechte windows"],
        "end": ["ende"],
        "ctrl": ["strg"],
        "right ctrl": ["strg-rechts"],
        "enter": ["eingabe"],
        "shift": ["umschalt"],
        "capslock": ["feststell"],
        "caps lock": ["feststell"],
    }

    aliase_di = {}
    for k, v in aliase.items():
        for c in v:
            aliase_di[c] = k
    scancode_self_dict = {}
    # last_200 = []

    time_to_clicks_standard = {
        0.5: 9,
        1.0: 24,
        1.5: 39,
        2.0: 54,
        2.5: 69,
        3.0: 84,
        3.5: 99,
        4.0: 115,
        4.5: 130,
        5.0: 145,
        5.5: 160,
        6.0: 175,
        6.5: 190,
        7.0: 206,
        7.5: 221,
        8.0: 235,
        8.5: 251,
        9.0: 266,
        9.5: 281,
        10.0: 296,
        10.5: 312,
        11.0: 327,
        11.5: 342,
        12.0: 357,
        12.5: 372,
        13.0: 387,
        13.5: 403,
        14.0: 418,
        14.5: 433,
        15.0: 448,
        15.5: 463,
        16.0: 478,
        16.5: 493,
        17.0: 509,
        17.5: 524,
        18.0: 539,
        18.5: 554,
        19.0: 569,
        19.5: 584,
        20.0: 599,
        20.5: 614,
        21.0: 630,
        21.5: 645,
        22.0: 660,
        22.5: 675,
        23.0: 690,
        23.5: 706,
        24.0: 721,
        24.5: 736,
        25.0: 751,
        25.5: 766,
        26.0: 781,
        26.5: 796,
        27.0: 812,
        27.5: 827,
        28.0: 842,
        28.5: 857,
        29.0: 872,
        29.5: 887,
        30.0: 903,
    }

    time_to_clicks_upper_f = {
        0.5: 2,
        1.0: 17,
        1.5: 34,
        2.0: 51,
        2.5: 67,
        3.0: 84,
        3.5: 101,
        4.0: 117,
        4.5: 134,
        5.0: 151,
        5.5: 167,
        6.0: 184,
        6.5: 201,
        7.0: 217,
        7.5: 234,
        8.0: 250,
        8.5: 267,
        9.0: 284,
        9.5: 300,
        10.0: 317,
        10.5: 334,
        11.0: 350,
        11.5: 367,
        12.0: 384,
        12.5: 401,
        13.0: 417,
        13.5: 434,
        14.0: 451,
        14.5: 467,
        15.0: 484,
        15.5: 501,
        16.0: 517,
        16.5: 534,
        17.0: 551,
        17.5: 567,
        18.0: 584,
        18.5: 601,
        19.0: 617,
        19.5: 634,
        20.0: 651,
        20.5: 667,
        21.0: 684,
        21.5: 701,
        22.0: 717,
        22.5: 734,
        23.0: 751,
        23.5: 767,
        24.0: 784,
        24.5: 801,
        25.0: 817,
        25.5: 834,
        26.0: 851,
        26.5: 867,
        27.0: 884,
        27.5: 901,
        28.0: 917,
        28.5: 934,
        29.0: 951,
        29.5: 967,
        30.0: 984,
    }

    def __init__(
        self,
        name: str,
        state: str = "up",
        last_up_time: float = None,
        last_down_time: float = None,
        is_keypad: bool = None,
        scan_code: int = None,
        active_modifiers: list = [],
    ) -> None:

        self._name = name
        self._state = state
        self._last_state = "up"
        self.last_up_time = last_up_time
        self.last_down_time = last_down_time
        self.up_time = 1
        self.down_time = 0
        self.is_keypad = is_keypad
        self.scan_code = scan_code
        self._callbacks_up = []
        self._callbacks_down = []
        self.active_modifiers = active_modifiers
        self.queue = Queue()
        Key.all_keys.append(self)
        Key.name_self_dict[name] = self
        Key.scancode_self_dict[scan_code] = self
        self._alias_bound_timed_functions = {}
        self.key_chains = []
        upper_f = (
            "f13",
            "f14",
            "f15",
            "f16",
            "f17",
            "f18",
            "f19",
            "f20",
            "f21",
            "f22",
            "f23",
            "f24",
        )
        if name in upper_f:
            self.timer_to_pressed_counter = Key.time_to_clicks_upper_f
        else:
            self.timer_to_pressed_counter = Key.time_to_clicks_standard
        self.last_2000 = []

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, value):
        print(f"The value for the attribute name of this Key object is immutable!")

    @property
    def state(self):
        return self._state

    @state.setter
    def state(self, value):
        if value != "up" and value != "down":
            raise ValueError

        self.active_modifiers = [
            x
            for x in list(Key.standard_modifiers)
            if Key.name_self_dict[x].state == "down"
        ]

        self._state = value
        if value == "up":
            for c, args, send_self in self._callbacks_up:
                if send_self:
                    if args != None:
                        c(self, *args)
                    else:
                        c(self)
                else:
                    if args != None:
                        c(*args)
                    else:
                        c()
        elif value == "down":
            for c, args, send_self in self._callbacks_down:
                if send_self:
                    if args != None:
                        c(self, *args)
                    else:
                        c(self)
                else:
                    if args != None:
                        c(*args)
                    else:
                        c()

    def bind(
        self,
        callback: Callable,
        args: Iterable = None,
        state: str = "down",
        send_self: bool = False,
    ):
        """
        callback should be a function
        """
        if state == "up":
            self._callbacks_up.append((callback, args, send_self))
        elif state == "down":
            self._callbacks_down.append((callback, args, send_self))
        else:
            raise ValueError

    def unbind(self, callback: Callable, state: str = "down"):
        to_remove = []
        if state == "up":
            for (callback_, args, send_self) in self._callbacks_up:
                if callback == callback_:
                    to_remove.append((callback, args, send_self))
            for n in to_remove:
                self._callbacks_up.remove(n)
        elif state == "down":
            for (callback_, args, send_self) in self._callbacks_down:
                if callback == callback_:
                    to_remove.append((callback, args, send_self))
            for n in to_remove:
                self._callbacks_down.remove(n)
        else:
            raise ValueError

        try:
            for keyname in Key.aliase[self._name]:
                key = Key.name_self_dict[keyname]
                key.unbind(callback, state)
                for f, cs in self._alias_bound_timed_functions.items():
                    try:
                        if callback == f:
                            try:
                                key.unbind(cs[0], "down")
                            except:
                                pass
                            try:
                                key.unbind(cs[1], "down")
                            except:
                                pass
                            try:
                                key.unbind(cs[0], "up")
                            except:
                                pass
                            try:
                                key.unbind(cs[1], "up")
                            except:
                                pass
                    except:
                        pass
        except:
            pass

    def unbind_all(self):
        self._callbacks_up = []
        self._callbacks_down = []

        try:
            for keyname in Key.aliase[self._name]:
                key = Key.name_self_dict[keyname]
                key._callbacks_up = []
                key._callbacks_down = []
        except:
            pass

    def timed_hotkey(
        self,
        callback: Callable,
        timer: float = 3,
        args: Iterable = None,
        send_self: bool = False,
        sleep_after_execution: float = 0,
    ):
        class HotkeyTimer:
            def __init__(t, timer) -> None:
                t.up_time = 1
                t.down_time = 0
                t.fired = False
                t.timer = timer
                t.q = Queue()

        def wait_for_call():
            while True:
                v = t.q.get()
                if send_self:
                    if args != None:
                        callback(self, *args)
                    else:
                        callback(self)
                else:
                    if args != None:
                        callback(*args)
                    else:
                        callback()
                t.q = Queue()
                t.fired = False

        t = HotkeyTimer(timer)
        Thread(target=wait_for_call, daemon=True).start()

        def timed_hotkey_caller():
            if (
                time() - self.down_time > t.timer
                and not t.fired
                and self.state == "down"
            ):
                t.fired = True
                self.down_time = time()
                t.q.put(0)
                sleep(sleep_after_execution)
            # else: print(time()-self.down_time)

        def timed_hotkey_thread_canceler():
            t.up_time = time()
            t.down_time = 0

        self.bind(timed_hotkey_caller, state="down")
        self.bind(timed_hotkey_thread_canceler, state="up")

        return timed_hotkey_caller, timed_hotkey_thread_canceler

    def key_chain_binding(self, key_chain: str, callback: Callable):
        hotkeys = key_chain.split("+")
        key_chain = key_chain.replace(" ", "")
        parts = key_chain.split(",")
        last_key = parts[-1]
        last_key: Key
        last_key.bind(last_key._check_key_chain)
        key_chain = [get_Key(k) for k in parts]
        get_Key(last_key).key_chains.append((key_chain, callback))

        def remove_key_chain(self, key_chain: str, callback: Callable):
            key_chain = key_chain.replace(" ", "")
            parts = key_chain.split(",")
            last_key = parts[-1]
            last_key: Key
            last_key.unbind(last_key._check_key_chain)
            key_chain = [get_Key(k) for k in parts]
            get_Key(last_key).key_chains.remove((key_chain, callback))

        def _check_key_chain(self):
            for key_chain, callback in self.key_chains:
                len_chain = len(key_chain)
                if Key.last_200[-1 * len_chain :] == key_chain:
                    callback()

    def timed_hotkey_clickrate_based(
        self,
        callback: Callable,
        timer: float = 3,
        args: Iterable = None,
        send_self: bool = False,
        sleep_after_execution: float = 1,
    ):
        try:
            self.timer_to_pressed_counter[round(float(timer), 1)]
        except:
            raise ValueError(
                "timer of <Key object>.timed_hotkey_clickrate_based needs to be a multiple of 0.5 but may not exceed 30."
            )

        def check_pressed(
            callback: Callable,
            timer: float = 3,
            args: Iterable = None,
            send_self: bool = False,
            sleep_after_execution: float = 0,
        ):
            timer = round(float(timer), 1)
            soll_anzahl_clicks = int(self.timer_to_pressed_counter[timer] * 0.95)
            try:
                event = self.last_2000[-soll_anzahl_clicks]
                latest_event = self.last_2000[-1]
                if (
                    round(latest_event.time - event.time, 1) <= timer
                    and round(time() - event.time, 1) <= timer
                    and round(time() - latest_event.time, 1) <= 0.2
                ):
                    if args != None:
                        if send_self:
                            callback(self, *args)
                        else:
                            callback(*args)
                    else:
                        if send_self:
                            callback(self)
                        else:
                            callback()
                    sleep(sleep_after_execution)
                else:
                    pass  # print(round(time() - event.time, 1), timer)
            except Exception as e:
                pass  # print(e)

        self.bind(
            check_pressed,
            args=[callback, timer, args, send_self, sleep_after_execution],
        )


def get_Key(
    name: str,
    state: str = "up",
    last_up_time: float = None,
    last_down_time: float = None,
    is_keypad: bool = None,
    scan_code: int = None,
    active_modifiers: list = [],
) -> Key:
    """Get's the instance of Key if the name exists. Else a new instance will be returned. (same as getKey function)

    Args:
        name (str): Name of the key. Names are already assigned by the keyboard module and refer to a scan code.
        state (str, optional): Current state of the key. Can be "up" or "down". Defaults to "up".
        last_up_time (float, optional): Last time the key state was "up". Defaults to None.
        last_down_time (float, optional): Last time the key state was "down". Defaults to None.
        is_keypad (bool, optional): Wether the key is on the keypad. Defaults to None.
        scan_code (int, optional): The scan code. Will be determined with when pressed by the name. Defaults to None.
        active_modifiers (list, optional): Modifiers. Defaults to [].

    Returns:
        Key: Instance of Key for keyboard bound functions.
    """
    try:
        return Key.name_self_dict[name]
    except:
        return Key(
            name,
            state,
            last_up_time,
            last_down_time,
            is_keypad,
            scan_code,
            active_modifiers,
        )


def getKey(
    name: str,
    state: str = "up",
    last_up_time: float = None,
    last_down_time: float = None,
    is_keypad: bool = None,
    scan_code: int = None,
    active_modifiers: list = [],
) -> Key:
    """Get's the instance of Key if the name exists. Else a new instance will be returned. (same as get_Key function)

    Args:
        name (str): Name of the key. Names are already assigned by the keyboard module and refer to a scan code.
        state (str, optional): Current state of the key. Can be "up" or "down". Defaults to "up".
        last_up_time (float, optional): Last time the key state was "up". Defaults to None.
        last_down_time (float, optional): Last time the key state was "down". Defaults to None.
        is_keypad (bool, optional): Wether the key is on the keypad. Defaults to None.
        scan_code (int, optional): The scan code. Will be determined with when pressed by the name. Defaults to None.
        active_modifiers (list, optional): Modifiers. Defaults to [].

    Returns:
        Key: Instance of Key for keyboard bound functions.
    """
    return get_Key(
        name,
        state,
        last_up_time,
        last_down_time,
        is_keypad,
        scan_code,
        active_modifiers,
    )


def unbind_all_hotkeys():
    for k in Key.name_self_dict.values():
        try:
            k.unbind_all()
        except:
            pass


keys = [
    "linke windows",
    "rechte windows",
    "strg",
    "umschalt",
    "feststell",
    "strg",
    "anwendung",
    "ende",
    "\t",
    "\n",
    "\r",
    " ",
    "!",
    '"',
    "#",
    "$",
    "%",
    "&",
    "'",
    "(",
    ")",
    "*",
    "+",
    ",",
    "-",
    ".",
    "/",
    "0",
    "1",
    "2",
    "3",
    "4",
    "5",
    "6",
    "7",
    "8",
    "9",
    ":",
    ";",
    "<",
    "=",
    ">",
    "?",
    "@",
    "[",
    "\\",
    "]",
    "^",
    "_",
    "`",
    "a",
    "b",
    "c",
    "d",
    "e",
    "f",
    "g",
    "h",
    "i",
    "j",
    "k",
    "l",
    "m",
    "n",
    "o",
    "p",
    "q",
    "r",
    "s",
    "t",
    "u",
    "v",
    "w",
    "x",
    "y",
    "z",
    "{",
    "|",
    "}",
    "~",
    "add",
    "alt",
    "apps",
    "backspace",
    "capslock",
    "clear",
    "numlock",
    "pagedown",
    "pageup",
    "pause",
    "pgup",
    "print",
    "return",
    "right",
    "select",
    "separator",
    "shift",
    "sleep",
    "space",
    "subtract",
    "tab",
    "up",
    "win",
    "command",
    "option",
]

for k in keys:
    Key(k, scan_code=key_to_scan_codes(k))


def keyboard_hook_callback(event: KeyboardEvent):
    """
    Attribute: name, device, event_type, is_keypad, modifiers, scan_code, time
    Reguläre: name, event_type, is_keypad
    """

    if round(time() - event.time, 2) < 0.1:

        # try: key = Key.name_self_dict[event.name]
        # except: key = Key(event.name, scan_code=event.scan_code)

        keys = []
        try:
            key = Key.name_self_dict[event.name]
            keys.append(key)
        except:
            key = Key(event.name, scan_code=event.scan_code)
            keys.append(key)

        try:
            try:
                name = Key.aliase_di[event.name]
            except:
                name = Key.aliase[event.name]
            key = Key.name_self_dict[name]
            keys.append(key)
        except:
            pass

        for key in keys:
            key: Key
            if event.event_type == "up" and key._last_state != event.event_type:
                key.up_time = event.time
            elif event.event_type == "down" and key._last_state != event.event_type:
                key.down_time = event.time
            if event.event_type == "up":
                key.last_up_time = event.time
            elif event.event_type == "down":
                key.last_down_time = event.time
            else:
                print(event.event_type, "war nicht vorhergesehen")
            key.state = event.event_type
            key.is_keypad = event.is_keypad
            key._last_state = event.event_type
            key.last_2000.append(event)
            if len(key.last_2000) > 2000:
                key.last_2000.pop(0)


def keyboard_hook_callback_with_callbacks_queued(event: KeyboardEvent):
    """
    Attribute: name, device, event_type, is_keypad, modifiers, scan_code, time
    Reguläre: name, event_type, is_keypad
    """
    keys = []
    try:
        key = Key.name_self_dict[event.name]
        keys.append(key)
    except:
        key = Key(event.name, scan_code=event.scan_code)
        keys.append(key)

    try:
        name = Key.aliase_di[event.name]
        key = Key.name_self_dict[name]
        keys.append(key)
    except:
        pass

    for key in keys:
        key: Key
        if event.event_type == "up" and key.up_time < key.down_time:
            key.up_time = event.time
        elif event.event_type == "down" and key.up_time > key.down_time:
            key.down_time = event.time
        if event.event_type == "up":
            key.last_up_time = event.time
        elif event.event_type == "down":
            key.last_down_time = event.time
        else:
            print(event.event_type, "war nicht vorhergesehen")
        key.state = event.event_type
        key.is_keypad = event.is_keypad


def keyboard_hook_callback_with_callbacks_queued():
    unhook(keyboard_hook_callback)
    hook(keyboard_hook_callback_with_callbacks_queued, on_remove=on_unhook)


def on_unhook():
    print("Keyboard unhooked")


def init():
    try:
        unhook(keyboard_hook_callback_with_callbacks_queued)
    except:
        pass
    hook(keyboard_hook_callback, on_remove=on_unhook)


init()


if __name__ == "__main__":
    from decimal import Decimal

    from colorama import Fore
    from colorama import init as coloinit
    from icecream import ic

    coloinit(True)

    def test(key):
        print(
            Fore.BLACK + "call by",
            f"'{Fore.YELLOW}{key.name}'",
            Fore.BLACK + "with current state:",
            f"'{Fore.YELLOW}{key.state}'",
            Fore.BLACK + "and current time:",
            time(),
        )
        sleep(0.4)

    start = None
    clicks = 0
    numbs = []
    for i in range(1, 61):
        n = Decimal(f"{i}.0") / Decimal("2")
        numbs.append(n)
    dones = []
    # ic(numbs[0:10])

    time_to_clicks = {}

    def get_rate():
        global start, clicks, c1, c2, c3, c4, c5
        if start == None:
            start = time()
            c1 = c2 = c3 = c4 = c5 = True
        clicks += 1

        t = round(time() - start, 1)
        for n in numbs:
            if t == n and n not in dones:
                print(f"\r{n} -> {clicks} Clicks mit {round(clicks/n, 2)} cps", end="")
                dones.append(n)
                time_to_clicks[float(n)] = clicks

    f22 = get_Key("f22")
    # f22.bind(get_rate)

    f22.timed_hotkey_clickrate_based(test, send_self=True)

    wait("esc")

    print()
