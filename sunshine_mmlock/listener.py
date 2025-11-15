import logging
import time
from typing import Callable, Optional, Tuple
from .mapper import get_monitor_from_xy, get_monitor_from_xy_sunshine
from .executor import KeystrokeExecutor
from .config import config


class MousePoller:
    """
    Polls the mouse position at a regular interval to determine the active
    monitor and trigger hotkeys. The poller is stoppable and accepts an
    injectable mouse position provider for testability.
    """
    def __init__(self, executor: Optional[KeystrokeExecutor] = None,
                 mouse_position_provider: Optional[Callable[[], Tuple[int, int]]] = None,
                 use_sunshine_mapping: bool = True):
        self._executor = executor if executor is not None else KeystrokeExecutor()
        self._last_monitor_index: int = -1
        self._last_position: Optional[Tuple[int, int]] = None
        # Use a dedicated poll interval and a separate debounce interval
        self._poll_interval: float = float(config.poll_interval)
        self._debounce_seconds: float = float(config.debounce_seconds)
        self._debug = config.debug
        self._move_threshold: float = float(config.poll_move_threshold)
        self._use_sunshine_mapping = use_sunshine_mapping
        self._running = False
        # Resolve a mouse position provider if not supplied. 
        # Priority: injected > Hyprland native > mouseinfo > pynput > evdev fallback
        if mouse_position_provider is not None:
            self._mouse_position_provider = mouse_position_provider
        else:
            # Try Hyprland native first (most accurate on Hyprland/Wayland)
            try:
                from .hyprland_mouse import HyprlandMouseReader, is_hyprland_available
                
                if is_hyprland_available():
                    reader = HyprlandMouseReader()
                    self._mouse_position_provider = reader.position
                    logging.info("Using Hyprland native mouse position reader")
                else:
                    raise RuntimeError("Hyprland not available")
            except Exception as e_hyprland:
                # try mouseinfo
                try:
                    import mouseinfo

                    self._mouse_position_provider = mouseinfo.position
                    logging.info("Using mouseinfo for mouse position")
                except Exception as e_mouseinfo:
                    # try pynput.Controller().position
                    try:
                        from pynput.mouse import Controller as _Controller

                        _ctl = _Controller()

                        def _pynput_pos():
                            return _ctl.position

                        self._mouse_position_provider = _pynput_pos
                        logging.info("Using pynput for mouse position")
                    except Exception as e_pynput:
                        # As a last resort try evdev-based relative reader (best-effort)
                        try:
                            from .input_reader import EvdevMouseReader
                            # Try to pick a sensible initial origin: center of primary monitor
                            initial = (0, 0)
                            try:
                                from screeninfo import get_monitors
                                monitors = list(get_monitors())
                                # Prefer an explicitly marked primary monitor if available
                                m0 = None
                                for m in monitors:
                                    if getattr(m, 'is_primary', False) or getattr(m, 'primary', False):
                                        m0 = m
                                        break
                                # Fallback: pick the monitor whose center is closest to the origin
                                if m0 is None and monitors:
                                    def center_dist(m):
                                        cx = m.x + m.width // 2
                                        cy = m.y + m.height // 2
                                        return abs(cx) + abs(cy)

                                    m0 = min(monitors, key=center_dist)
                                if m0:
                                    initial = (m0.x + m0.width // 2, m0.y + m0.height // 2)
                            except Exception:
                                # ignore monitor detection failures here; use default origin
                                pass

                            reader = EvdevMouseReader()
                            reader.start(initial=initial)
                            self._evdev_reader = reader
                            self._mouse_position_provider = reader.position
                            logging.info("Using evdev fallback mouse reader")
                        except Exception as e_ev:
                            logging.warning("All mouse position providers failed - hyprland: %s, mouseinfo: %s, pynput: %s, evdev: %s", 
                                          e_hyprland, e_mouseinfo, e_pynput, e_ev)
                            raise RuntimeError("No mouse position provider available; please install 'mouseinfo' or 'pynput', or ensure hyprctl is available, or grant read access to /dev/input for evdev fallback")

    def start(self):
        """Starts the polling loop and blocks until interrupted."""
        logging.info("Starting mouse poller with a %.3f second poll interval...", self._poll_interval)
        self._running = True

        # Get initial position
        try:
            x, y = self._mouse_position_provider()
            if self._use_sunshine_mapping:
                self._last_monitor_index = get_monitor_from_xy_sunshine(x, y)
            else:
                self._last_monitor_index = get_monitor_from_xy(x, y)
            self._last_position = (x, y)
            logging.info("Started on monitor: %s at (%s, %s)", self._last_monitor_index, x, y)
        except Exception as e:
            logging.error("Could not determine initial mouse position: %s", e, exc_info=True)
            self._last_monitor_index = -1
            self._last_position = None

        last_switch_time = 0.0

        while self._running:
            try:
                x, y = self._mouse_position_provider()

                # Determine which monitor (if any) the current coordinates map to.
                if self._use_sunshine_mapping:
                    monitor_index = get_monitor_from_xy_sunshine(x, y)
                else:
                    monitor_index = get_monitor_from_xy(x, y)

                if self._debug:
                    logging.debug("Polling mouse at: (%s, %s) -> monitor: %s", x, y, monitor_index if monitor_index is not None else 'unknown')
                # Movement threshold: ignore tiny/irrelevant motion to reduce noise.
                if self._last_position is not None:
                    dx = x - self._last_position[0]
                    dy = y - self._last_position[1]
                    dist_sq = dx * dx + dy * dy
                    if dist_sq < (self._move_threshold * self._move_threshold):
                        # Uncomment the lines below if you like noisy debug logs!
                        #if self._debug:
                            #logging.debug("Ignored small mouse movement (dx=%s, dy=%s, thr=%s)", dx, dy, self._move_threshold)
                        time.sleep(self._poll_interval)
                        continue

                # Update last_position only when movement is significant
                self._last_position = (x, y)

                now = time.time()
                if monitor_index is None:
                    # Position doesn't map to known monitors — do not spam logs; handled silently unless debug needs it.
                    pass
                elif monitor_index != self._last_monitor_index and (now - last_switch_time) >= self._debounce_seconds:
                    logging.info("Monitor switch: %s -> %s at (%s, %s) (debounce=%.2fs)", self._last_monitor_index, monitor_index, x, y, self._debounce_seconds)
                    try:
                        self._executor.execute_for_monitor(monitor_index)
                    except Exception:
                        logging.exception("Executor failed to execute hotkey for monitor %s", monitor_index)
                    self._last_monitor_index = monitor_index
                    last_switch_time = now

                time.sleep(self._poll_interval)

            except Exception as e:
                logging.error("An error occurred during polling: %s", e, exc_info=True)
                # Wait a bit longer before retrying to avoid spamming errors
                time.sleep(1)

    def stop(self):
        """Stops the mouse poller."""
        logging.info("Stopping mouse poller...")
        self._running = False