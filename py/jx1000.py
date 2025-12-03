from typing import Optional, Callable
from jx1000_driver import JX1000Driver, EFRAME


class JX1000:
    """
    High-level API wrapper for the JX1000 driver.
    """

    def __init__(self, port: Optional[str] = None, baud: int = 115200,
                 event_mode: str = "pretty", print_events: bool = True):

        self.driver = JX1000Driver(port=port, baud=baud,
                                   event_mode=event_mode,
                                   print_events=print_events)
        
        self.on_event: Optional[Callable[[str, object], None]] = None
        self.driver.on_event = self._handle_driver_event

    # ------------------------------------------------------------------
    # High-level event dispatch
    # ------------------------------------------------------------------
    def _handle_driver_event(self, code, value):
        """
        Converts low-level driver events to high-level API events.
        Fires the user-defined callback if set.
        """
        if self.on_event:
            try:
                self.on_event(code, value)
            except Exception:
                pass

    # ------------------------------------------------------------------
    # Connection management
    # ------------------------------------------------------------------
    def connect(self, port: str = None) -> bool:
        if port:
            self.driver.port_name = port
        return self.driver.open_port()

    def disconnect(self):
        self.driver.close_port()

    def is_connected(self) -> bool:
        return self.driver.is_open()

    # ------------------------------------------------------------------
    # Memory access
    # ------------------------------------------------------------------
    def read_memory(self, com: int, ch: int, addr: int):
        """
        Read a float value from device memory.
        """
        return self.driver.read(com, ch, addr)

    def write_memory(self, com: int, ch: int, addr: int, value: float):
        """
        Write a float value to device memory.
        """
        return self.driver.write(com, ch, addr, value)

    # ------------------------------------------------------------------
    # Rule download
    # ------------------------------------------------------------------
    def download_rules_from_file(self, path: str):
        try:
            with open(path, "rb") as f:
                data = f.read()
        except Exception as e:
            if self.on_event:
                self.on_event("RuleLoadError", f"Failed to read file: {e}")
            return
        self.driver.download_rules(data)

    # ------------------------------------------------------------------
    # Test control
    # ------------------------------------------------------------------
    def start_test(self):
        return self.driver.test_start()

    def stop_test(self):
        return self.driver.test_stop()
