import serial
import struct
import threading
import time
from typing import Optional, Callable, Union

FRAME_H = 0xA5
FRAME_L = 0x5E

class EFRAME:
    Info = 0x01
    RuleDown = 0x02
    DevRead = 0x21
    DevWrite = 0x22
    RES = 0xFE
    LOG = 0xFF

EFRAME_NAMES = {
    EFRAME.Info:      "INFO",
    EFRAME.RuleDown:  "RULE",
    EFRAME.DevRead:   "READ",
    EFRAME.DevWrite:  "WRITE",
    EFRAME.RES:       "RES",
    EFRAME.LOG:       "LOG",
}


class JX1000Driver:
    """
    Low-level serial driver for JX1000 devices.
    Handles frame construction, parsing, and event dispatch.
    """

    def __init__(self, port: Optional[str] = None, baud: int = 115200,
                 event_mode: str = "pretty", print_events: bool = True):
        self.port_name = port
        self.baud = baud
        self.s: Optional[serial.Serial] = None
        self.buffer = bytearray()
        self._running = False
        self._reader_thread: Optional[threading.Thread] = None
        self._last_read: Optional[float] = None
        self._write_ack: Optional[bool] = None
        self._rule_ack: Optional[bool] = None

        # Event system
        self.event_mode = event_mode  # "pretty" or "raw"
        self.print_events = print_events
        self.on_event: Optional[Callable[[Union[int, str], object], None]] = None
        self._event_queue = []
        self._print_lock = threading.Lock()

    # -------------------------
    # Port management
    # -------------------------
    def open_port(self) -> bool:
        if not self.port_name:
            raise ValueError("Port name not specified")
        if self.s and getattr(self.s, "is_open", False):
            self._dispatch_event(EFRAME.RES, f"Port {self.port_name} already open")
            return True
        try:
            self.s = serial.Serial(self.port_name, self.baud, timeout=0.05)
        except Exception as e:
            self._dispatch_event(EFRAME.RES, f"Failed to open port: {e}")
            return False

        self._running = True
        self._reader_thread = threading.Thread(target=self._reader, daemon=True)
        self._reader_thread.start()
        self._dispatch_event(EFRAME.RES, f"Port {self.port_name} opened")
        self.request_info()
        return True

    def close_port(self):
        self._running = False
        if self.s and getattr(self.s, "is_open", False):
            try:
                self.s.close()
            except Exception:
                pass
            self._dispatch_event(EFRAME.RES, f"Port {self.port_name} closed")
        self.s = None

    def is_open(self) -> bool:
        return self.s is not None and getattr(self.s, "is_open", False)

    # -------------------------
    # Frame handling
    # -------------------------
    def checksum(self, data: bytes) -> int:
        return sum(data) & 0xFF

    def send_frame(self, cmd: int, payload: bytes = b"") -> bool:
        if not self.is_open():
            self._dispatch_event(EFRAME.RES, "Port not open")
            return False
        frame = bytearray([FRAME_H, FRAME_L, len(payload), cmd]) + payload
        frame.append(self.checksum(frame))
        try:
            self.s.write(frame)
            return True
        except Exception as e:
            self._dispatch_event(EFRAME.RES, f"Serial write error: {e}")
            return False

    # -------------------------
    # High-level commands
    # -------------------------
    def read(self, com: int, ch: int, addr: int, timeout: int = 300) -> Optional[float]:
        self._last_read = None
        payload = struct.pack("<BBHf", com & 0xFF, ch & 0xFF, addr & 0xFFFF, 0.0)
        if not self.send_frame(EFRAME.DevRead, payload):
            return None

        start_time = time.time()
        while time.time() - start_time < timeout * 0.001:
            if self._last_read is not None:
                val = self._last_read
                self._last_read = None
                return val
            time.sleep(0.001)
        self._dispatch_event(EFRAME.RES, "Read timed out")
        return None

    def write(self, com: int, ch: int, addr: int, value: float, timeout: int = 300) -> bool:
        self._write_ack = None
        payload = struct.pack("<BBHf", com & 0xFF, ch & 0xFF, addr & 0xFFFF, float(value))
        if not self.send_frame(EFRAME.DevWrite, payload):
            return False

        start_time = time.time()
        while time.time() - start_time < timeout * 0.001:
            if self._write_ack is not None:
                ack = self._write_ack
                self._write_ack = None
                return ack
            time.sleep(0.001)
        self._dispatch_event(EFRAME.RES, "Write timed out")
        return False

    def request_info(self):
        self.send_frame(EFRAME.Info, b"\x00\x00")

    def download_rules(self, buf: bytes):
        if not self.is_open():
            self._dispatch_event(EFRAME.RuleDown, "Port not open")
            return
        if not buf or len(buf) < 10:
            self._dispatch_event(EFRAME.RuleDown, "Invalid rules buffer")
            return

        chunk_size = 156
        total_len = len(buf)
        offset = 0

        def worker():
            nonlocal offset
            self.request_info()
            time.sleep(0.05)

            while offset < total_len:
                end = min(offset + chunk_size, total_len)
                chunk = buf[offset:end]
                hdr = struct.pack("<B H B", 1, offset & 0xFFFF, len(chunk) & 0xFF)
                self._rule_ack = None
                if not self.send_frame(EFRAME.RuleDown, hdr + chunk):
                    self._dispatch_event(EFRAME.RuleDown, "error-send")
                    return

                waited = 0
                while waited < 2000:
                    if self._rule_ack is not None:
                        break
                    time.sleep(0.01)
                    waited += 10
                if self._rule_ack is False:
                    self._dispatch_event(EFRAME.RuleDown, "chunk-failed")
                    return

                offset = end
                pct = int(offset * 100 / total_len)
                if self._rule_ack is not None:
                    status = 'OK' if self._rule_ack else 'FAIL'
                else:
                    status = 'Unknown'

                self._dispatch_event(EFRAME.RuleDown, f"{pct}% - {status}")

            final_hdr = struct.pack("<B H B", 2, 0, 1)
            self.send_frame(EFRAME.RuleDown, final_hdr + b"\x00")
            self._dispatch_event(EFRAME.RuleDown, "Done")

        threading.Thread(target=worker, daemon=True).start()
    
    def test_start(self):
        payload = b'cmd_EnableExec()\r\n' 
        return self.send_frame(EFRAME.LOG, payload) 

    def test_stop(self):
        payload = b'cmd_ExitExec()\r\n' 
        return self.send_frame(EFRAME.LOG, payload) 

    # -------------------------
    # Frame parser
    # -------------------------
    def _reader(self):
        while self._running:
            if not self.is_open():
                time.sleep(0.05)
                continue
            try:
                chunk = self.s.read(256)
            except Exception:
                break
            if chunk:
                self.buffer.extend(chunk)
                self._process_buffer()

    def _process_buffer(self):
        while len(self.buffer) >= 5:
            if self.buffer[0] != FRAME_H or self.buffer[1] != FRAME_L:
                self.buffer.pop(0)
                continue
            length = self.buffer[2]
            total = length + 5
            if len(self.buffer) < total:
                return
            frame = bytes(self.buffer[:total])
            del self.buffer[:total]
            if self.checksum(frame[:-1]) != frame[-1]:
                continue
            cmd = frame[3]
            data = frame[4:-1]
            self._handle_frame(cmd, data)

    def _handle_frame(self, cmd: int, data: bytes):
        try:
            # DEV_READ
            if cmd == EFRAME.DevRead:
                if len(data) >= 9:
                    com, ch, res, addr, val = struct.unpack("<BBBHf", data[:9])
                    self._last_read = float(val)
                    self._dispatch_event(EFRAME.DevRead, {"com":com,"ch":ch,"addr":addr,"result":res,"value":val})
                else:
                    self._dispatch_event(EFRAME.DevRead, data)
            # DEV_WRITE
            elif cmd == EFRAME.DevWrite:
                if len(data) >= 9:
                    try:
                        com, ch, res, addr, val = struct.unpack("<BBBHf", data[:9])
                        self._write_ack = True
                        self._dispatch_event(EFRAME.DevWrite, {"com": com,"ch": ch,"addr": addr,"result": res,"value": val})
                    except struct.error:
                        self._write_ack = True
                        self._dispatch_event(EFRAME.DevWrite, data)
                else:
                    self._write_ack = True
                    self._dispatch_event(EFRAME.DevWrite, data)
            # INFO
            elif cmd == EFRAME.Info:
                if len(data) >= 6:
                    hard, ver, comnum, model, cmdbytes = struct.unpack("<BBBBH", data[:6])
                    info_dict = {"HardType": hard, "Version": f"{ver/10:.1f}", "ComNumber": comnum, "BoardCount": model}
                    self._dispatch_event(EFRAME.Info, info_dict)
                else:
                    self._dispatch_event(EFRAME.Info, data)
            # RULE download
            elif cmd == EFRAME.RuleDown:
                if len(data) >= 1:
                    ok = data[0] == 1
                    self._rule_ack = ok
                    self._dispatch_event(EFRAME.RuleDown)
                else:
                    self._dispatch_event(EFRAME.RuleDown, "No ACK byte")
            # RES
            elif cmd == EFRAME.RES:
                try:
                    text = data.decode("utf-8", errors="ignore").strip()
                except Exception:
                    text = data
                if text.startswith("{ED,") and text.endswith("}"):
                    parts = text[1:-1].split(",")   # remove {}
                    if len(parts) >= 2:
                        result_flag = parts[1].strip()
                        self._last_test_result = "{PASS}" if result_flag == "1" else "FAIL"
                        self._dispatch_event(cmd, self._last_test_result)
                    return
                self._dispatch_event(cmd, text)
            # LOG
            elif cmd == EFRAME.LOG:
                try:
                    text = data.decode("utf-8", errors="ignore").strip()
                except Exception:
                    text = data
                if text == ("cmd_EnableExec."):
                    self._dispatch_event(cmd, "Starting test...")
                    return
                if text.startswith("cmd") and text.endswith("Start..."):
                    self._dispatch_event(cmd, "Test Start")
                    return
                if text.startswith("cmd") and text.endswith("End..."):
                    self._dispatch_event(cmd, "Test End")
                    return
                self._dispatch_event(cmd, text)
            else:
                self._dispatch_event(cmd, data)
        except Exception as e:
            if self.print_events:
                self._safe_print(f"Exception in handle(): cmd={cmd}, data={data}, error={e}")
    
    def build_frame(cmd_id, ascii_text):
        payload = ascii_text.encode("ascii")
        length = len(payload)
        frame = bytearray([0xA5, 0x5E, length, cmd_id])
        frame.extend(payload)
        checksum = sum(frame[2:]) & 0xFF
        frame.append(checksum)
        return bytes(frame)

    # -------------------------
    # Event system
    # -------------------------
    def _safe_print(self, message: str):
        with self._print_lock:
            print("\r\x1b[2K" + message)
            print(">> ", end="", flush=True)

    def _format_event(self, cmd: int, value) -> str:
        if cmd in EFRAME_NAMES:
            name = EFRAME_NAMES[cmd]
        else:
            name = str(cmd)
        if cmd == EFRAME.RES and value in ("PASS", "FAIL"):
            return f"[RES] {value}"

        return f"[{name}] {value}"

    def _dispatch_event(self, cmd: Union[int, str], value):
        """Dispatch event to console if print_events=True and to callback if provided."""
        if self.print_events:
            pretty = self._format_event(cmd, value)
            self._safe_print(pretty)
        if callable(self.on_event):
            try:
                self.on_event(cmd, value)
            except Exception:
                pass