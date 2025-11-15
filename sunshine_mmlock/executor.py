import logging
import time
from .config import config
from typing import List


class KeystrokeExecutor:
    """Handles the simulation of keyboard shortcuts.

    This implementation delays importing the keyboard backend (pynput) and
    gracefully falls back to a logging-only mode if the backend cannot be
    initialized (for example when DISPLAY/Xauthority is not available, or on
    unsupported Wayland setups).
    """
    def __init__(self):
        self._debug = config.debug
        self._base_keys = config.hotkey_base_keys
        self._modifiers = []
        self._available = False
        self._backend_name = None

        # Try to import and initialize the keyboard backend lazily. Any error
        # (ImportError or backend-specific initialization error) should not
        # crash the whole program.
        try:
            from pynput import keyboard

            # Save references we need
            self._keyboard_backend = keyboard
            self._keyboard = keyboard.Controller()

            # Map configured modifier names to backend keys when available
            MODIFIER_MAP = {
                'ctrl': keyboard.Key.ctrl,
                'alt': keyboard.Key.alt,
                'shift': keyboard.Key.shift,
                'cmd': keyboard.Key.cmd,
            }
            self._modifiers = [MODIFIER_MAP[mod] for mod in config.hotkey_modifiers if mod in MODIFIER_MAP]
            self._available = True
            self._backend_name = 'pynput'

        except Exception as e:
            # Log the reason for fallback and continue in logging-only mode.
            logging.warning("Keyboard backend unavailable, hotkey execution will be simulated (logged) instead: %s", e)
            self._keyboard = None
            # Attempt to initialize an evdev UInput backend (works on Wayland and X11
            # at the kernel level) if evdev is available and we have permission.
            try:
                from evdev import UInput, ecodes

                # Build a capability set containing common keys we will use.
                caps = {ecodes.EV_KEY: []}

                # helper to resolve key names to ecodes
                def _resolve_key(name: str):
                    lname = name.lower()
                    keyname = name.upper()
                    # modifiers mapping by lower-case name
                    mapping = {
                        'ctrl': 'KEY_LEFTCTRL',
                        'alt': 'KEY_LEFTALT',
                        'shift': 'KEY_LEFTSHIFT',
                        'cmd': 'KEY_LEFTMETA',
                        'super': 'KEY_LEFTMETA',
                    }
                    if lname in mapping:
                        return getattr(ecodes, mapping[lname], None)

                    # function keys like f1 -> KEY_F1
                    if keyname.startswith('F') and keyname[1:].isdigit():
                        return getattr(ecodes, 'KEY_' + keyname, None)

                    # single letters
                    if len(keyname) == 1 and keyname.isalpha():
                        return getattr(ecodes, 'KEY_' + keyname, None)

                    # fallback: try generic KEY_<NAME>
                    return getattr(ecodes, 'KEY_' + keyname, None)

                # collect keys from config
                for k in self._base_keys:
                    code = _resolve_key(k)
                    if code and code not in caps[ecodes.EV_KEY]:
                        caps[ecodes.EV_KEY].append(code)

                for mod in config.hotkey_modifiers:
                    code = _resolve_key(mod)
                    if code and code not in caps[ecodes.EV_KEY]:
                        caps[ecodes.EV_KEY].append(code)

                # ensure some basic keys are present
                for extra in ('KEY_ENTER', 'KEY_SPACE'):
                    code = getattr(ecodes, extra, None)
                    if code and code not in caps[ecodes.EV_KEY]:
                        caps[ecodes.EV_KEY].append(code)

                # Try to create UInput device
                try:
                    self._uinput = UInput(caps)
                    self._evdev = ecodes
                    # Precompute modifier codes for faster emit
                    self._evdev_modifiers = []
                    for mod in config.hotkey_modifiers:
                        code = _resolve_key(mod)
                        if code:
                            self._evdev_modifiers.append(code)
                    self._available = True
                    self._backend_name = 'evdev_uinput'
                    logging.info('Initialized evdev UInput backend for keystrokes')
                except Exception as ue:
                    logging.info('evdev UInput backend unavailable: %s', ue)
                    self._uinput = None
            except Exception as ev_e:
                logging.info('evdev not available: %s', ev_e)

    def execute_for_monitor(self, monitor_index: int):
        """Presses the configured key combination for the given monitor index.

        If the keyboard backend is unavailable the action will be logged rather
        than actually injected.
        """
        if not (0 <= monitor_index < len(self._base_keys)):
            logging.warning("Monitor index %s is out of range for configured hotkeys.", monitor_index)
            return

        target_key_str = self._base_keys[monitor_index]

        # If backend is not available, log the intended action and return.
        if not self._available:
            logging.info("[SIMULATION] Would execute hotkey for monitor %s: %s + %s", monitor_index, "+".join(config.hotkey_modifiers), target_key_str)
            return

        if self._backend_name == 'evdev_uinput' and getattr(self, '_uinput', None) is not None:
            # Use evdev UInput to emit key events at kernel level.
            try:
                codes = []
                # resolve modifier codes
                for mod in config.hotkey_modifiers:
                    c = None
                    try:
                        c = getattr(self._evdev, {
                            'ctrl': 'KEY_LEFTCTRL',
                            'alt': 'KEY_LEFTALT',
                            'shift': 'KEY_LEFTSHIFT',
                            'cmd': 'KEY_LEFTMETA',
                        }[mod])
                    except Exception:
                        # try generic
                        c = getattr(self._evdev, 'KEY_' + mod.upper(), None)
                    if c:
                        codes.append(c)

                # resolve base key
                base_code = None
                keyname = target_key_str.upper()
                if keyname.startswith('F') and keyname[1:].isdigit():
                    base_code = getattr(self._evdev, 'KEY_' + keyname, None)
                elif len(keyname) == 1 and keyname.isalpha():
                    base_code = getattr(self._evdev, 'KEY_' + keyname, None)
                else:
                    base_code = getattr(self._evdev, 'KEY_' + keyname, None)

                # Press modifiers
                for c in codes:
                    self._uinput.write(self._evdev.EV_KEY, c, 1)
                self._uinput.syn()

                # press base
                if base_code:
                    self._uinput.write(self._evdev.EV_KEY, base_code, 1)
                    self._uinput.syn()
                    time.sleep(0.02)
                    self._uinput.write(self._evdev.EV_KEY, base_code, 0)
                    self._uinput.syn()
                else:
                    logging.error('evdev: could not resolve base key %s', target_key_str)

                # release modifiers
                for c in reversed(codes):
                    self._uinput.write(self._evdev.EV_KEY, c, 0)
                self._uinput.syn()
                
                # Log the keystroke that was sent
                logging.info('Sent keystroke: %s+%s', '+'.join(config.hotkey_modifiers), target_key_str)
            except Exception as e:
                logging.error('evdev_uinput failed to emit keys: %s', e, exc_info=True)
            return

        # Resolve target key from backend if possible (pynput path)
        try:
            target_key = getattr(self._keyboard_backend.Key, target_key_str, None)
        except Exception:
            target_key = None

        if self._debug:
            logging.debug("Executing hotkey for monitor %s: %s + %s", monitor_index, "+".join(config.hotkey_modifiers), target_key_str)

        try:
            # Press all modifier keys
            for mod in self._modifiers:
                self._keyboard.press(mod)

            # Tap the base key (use backend Key object when available)
            if target_key is not None:
                self._keyboard.tap(target_key)
            else:
                # Fallback: try tapping by string (some backends allow this)
                try:
                    self._keyboard.tap(target_key_str)
                except Exception:
                    logging.error("Unable to tap target key '%s' with backend", target_key_str)

            # Release all modifier keys in reverse order
            for mod in reversed(self._modifiers):
                self._keyboard.release(mod)
        except Exception as e:
            logging.error("Error executing keystroke: %s", e, exc_info=True)


if __name__ == '__main__':
    # Quick import-time test to ensure module loads without crashing.
    logging.basicConfig(level=logging.DEBUG)
    logging.info("KeystrokeExecutor module imported successfully (no backend crash)")
