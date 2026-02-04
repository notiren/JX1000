import time
import serial
import serial.tools.list_ports

# Modbus RTU CRC16 (IBM / 0xA001)

def crc16_modbus(data: bytes) -> int:
    """
    Calculate Modbus RTU CRC16.

    Returns:
        int: 16-bit CRC value
    """
    crc = 0xFFFF
    for b in data:
        crc ^= b
        for _ in range(8):
            if crc & 0x0001:
                crc = (crc >> 1) ^ 0xA001
            else:
                crc >>= 1
    return crc


# ModbusRTU

class ModbusRTU:
    def __init__(self, port, baudrate=9600, timeout=1):
        self.ser = serial.Serial(
            port=port,
            baudrate=baudrate,
            bytesize=8,
            parity="N",
            stopbits=1,
            timeout=timeout
        )

    # ------------------------
    # Auto-connect FTDI RS485
    # ------------------------
    @classmethod
    def auto_connect(cls, baudrate=9600, timeout=1):
        for p in serial.tools.list_ports.comports():
            desc = (p.description or "").lower()
            if "ftdi" in desc:
                return cls(p.device, baudrate, timeout)
        raise RuntimeError("No FTDI RS485 adapter found")

    def close(self):
        if self.ser and self.ser.is_open:
            self.ser.close()

    # ------------------------
    # Low-level send / receive
    # ------------------------
    def _send_frame(self, frame: bytes, response_length: int) -> bytes:
        self.ser.reset_input_buffer()
        self.ser.write(frame)
        self.ser.flush()
        time.sleep(0.05)

        resp = self.ser.read(response_length)
        if len(resp) != response_length:
            raise RuntimeError("Timeout or incomplete Modbus response")
        return resp

    # ------------------------
    # Read Holding Registers (0x03)
    # ------------------------
    def read_holding_registers(self, slave: int, address: int, count: int):
        frame = bytes([
            slave,
            0x03,
            (address >> 8) & 0xFF,
            address & 0xFF,
            (count >> 8) & 0xFF,
            count & 0xFF
        ])

        crc = crc16_modbus(frame)
        frame += crc.to_bytes(2, "little")

        # Response: slave + func + byte_count + data + crc
        response_len = 5 + count * 2
        resp = self._send_frame(frame, response_len)

        data, recv_crc = resp[:-2], resp[-2:]
        if crc16_modbus(data).to_bytes(2, "little") != recv_crc:
            raise RuntimeError("CRC mismatch")

        byte_count = resp[2]
        values = []
        for i in range(0, byte_count, 2):
            hi = resp[3 + i]
            lo = resp[4 + i]
            values.append((hi << 8) | lo)

        return values

    # ------------------------
    # Write Single Register (0x06)
    # ------------------------
    def write_single_register(self, slave: int, address: int, value: int):
        frame = bytes([
            slave,
            0x06,
            (address >> 8) & 0xFF,
            address & 0xFF,
            (value >> 8) & 0xFF,
            value & 0xFF
        ])

        crc = crc16_modbus(frame)
        frame += crc.to_bytes(2, "little")

        resp = self._send_frame(frame, 8)

        data, recv_crc = resp[:-2], resp[-2:]
        if crc16_modbus(data).to_bytes(2, "little") != recv_crc:
            raise RuntimeError("CRC mismatch")

        return True
