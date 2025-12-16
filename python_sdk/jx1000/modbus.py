"""
Author: Neriton Pacarizi
Modbus API helper for JX1000 devices.
"""

from pymodbus.client import ModbusSerialClient
from pymodbus.exceptions import ModbusException, ModbusIOException
import struct

class ModbusHelper:
    
    def __init__(self, client: ModbusSerialClient):
        """Initialize with an active pymodbus client"""
        self.client = client

    # ------------------------
    # SAFE CALL WRAPPER
    # ------------------------
    def _safe_call(self, func, *args, **kwargs):
        """Executes a Modbus client function safely."""
        try:
            result = func(*args, **kwargs)
            if hasattr(result, "isError") and result.isError():
                return None, f"Error from device: {result}"
            return result, None
        except ModbusIOException:
            return None, "No response from device (ModbusIOException)"
        except ModbusException as e:
            return None, f"Modbus protocol error: {e}"
        except Exception as e:
            return None, f"Unknown error: {e}"

    # ------------------------
    # READ FUNCTIONS
    # ------------------------
    def read_single_register(self, start, count=1):
        """Read N consecutive registers starting at 'start'."""
        result, err = self._safe_call(self.client.read_holding_registers, start, count)
        if result is not None:
            return result.registers, None
        return None, err

    def read_mapped_pair(self, start, num_pairs):
        """Read mapped register pairs (1000-1499)."""
        if not (1000 <= start <= 1499):
            return None, "Mapped read requires 1000-1499 input"
        max_last = start + num_pairs - 1
        if max_last > 1499:
            return None, "Requested range exceeds 1499"

        results = []
        for src in range(start, start + num_pairs):
            base = 1000 + (src - 1000) * 2
            regs, err = self._safe_call(self.client.read_holding_registers, base, 2)
            if err:
                return None, f"Error reading mapped pair at {src}: {err}"
            results.append({
                "input_target": src,
                "mapped_registers": [base, base + 1],
                "values": regs.registers
            })
        return results, None

    # ------------------------
    # WRITE FUNCTIONS
    # ------------------------
    def write_register(self, address, value):
        """Write a single holding register."""
        result, err = self._safe_call(self.client.write_register, address, value)
        if result is not None:
            return True, None
        return None, err

    # ------------------------
    # UTILITY
    # ------------------------
    @staticmethod
    def registers_to_float(reg1, reg2, wordorder="big"):
        """Convert two 16-bit registers to a float."""
        if wordorder == "big":
            raw_bytes = reg1.to_bytes(2, 'big') + reg2.to_bytes(2, 'big')
        else:
            raw_bytes = reg2.to_bytes(2, 'big') + reg1.to_bytes(2, 'big')
        return struct.unpack('>f', raw_bytes)[0]
