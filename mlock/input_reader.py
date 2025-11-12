import threading
import logging
from typing import Optional, Tuple

try:
    from evdev import InputDevice, list_devices, ecodes
except Exception:
    InputDevice = None
    list_devices = None
    ecodes = None


class EvdevMouseReader:
    """Reads relative mouse movements from an evdev device and accumulates
    an approximate absolute position. This is a best-effort fallback when
    higher-level APIs (X11/Wayland helpers) are not available.

    Notes:
    - Requires read access to /dev/input/event* (input group or root).
    - Position starts at (0,0) by default; caller may choose an initial
      origin (e.g., center of primary monitor) after creation.
    """
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self._device = None
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self.x = 0
        self.y = 0

        if InputDevice is None:
            raise RuntimeError("evdev not available")

        # find a suitable device with relative X/Y
        for path in list_devices():
            try:
                dev = InputDevice(path)
                caps = dev.capabilities()
                if ecodes.EV_REL in caps and ecodes.REL_X in caps[ecodes.EV_REL] and ecodes.REL_Y in caps[ecodes.EV_REL]:
                    self._device = dev
                    self.logger.info("Evdev mouse reader using %s (%s)", dev.path, dev.name)
                    break
            except Exception:
                continue

        if self._device is None:
            raise RuntimeError("No evdev mouse device found or permission denied")

    def start(self, initial: Optional[Tuple[int, int]] = None):
        if initial is not None:
            self.x, self.y = initial
        self._running = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=1.0)

    def _run(self):
        try:
            for event in self._device.read_loop():
                if not self._running:
                    break
                if event.type == ecodes.EV_REL:
                    if event.code == ecodes.REL_X:
                        self.x += event.value
                    elif event.code == ecodes.REL_Y:
                        self.y += event.value
        except Exception as e:
            self.logger.exception("Evdev mouse reader stopped: %s", e)

    def position(self) -> Tuple[int, int]:
        return int(self.x), int(self.y)
