"""
Author: Neriton Pacarizi
Modbus API helper for JX1000 devices.
"""

from pymodbus.client import ModbusSerialClient
from pymodbus.exceptions import ModbusException, ModbusIOException
from serial.tools import list_ports
import struct
import time
from typing import Optional, List, Tuple


class ModbusHelper:

    def __init__(self, client: ModbusSerialClient, port: Optional[str] = None):
        if client is None:
            raise ValueError("ModbusHelper initialized with None client")
        self.client = client
        self.port = port
        
    # ------------------------
    # CONNECT / CLOSE
    # ------------------------
    def connect(self) -> bool:
        return self.client.connect()

    def close(self):
        self.client.close()

    # ------------------------
    # SAFE CALL WRAPPER
    # ------------------------
    def _safe_call(self, func, *args, **kwargs):
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
        result, err = self._safe_call(
            self.client.read_holding_registers,
            address=start,
            count=count,
        )
        if result is not None:
            return result.registers, None
        return None, err

    def read_mapped_pair(self, start, num_pairs=1):
        if not (1000 <= start <= 1499):
            return None, "Mapped read requires 1000-1499 input"
        
        max_last = start + num_pairs - 1
        if max_last > 1499:
            return None, "Requested range exceeds 1499"

        results = []

        for src in range(start, start + num_pairs):
            base = 1000 + (src - 1000) * 2

            regs, err = self._safe_call(
                self.client.read_holding_registers,
                address=base,
                count=2,
            )

            if err:
                return None, f"Error reading mapped pair at {src}: {err}"

            results.append({
                "input_target": src,
                "mapped_registers": [base, base + 1],
                "values": regs.registers,
            })

        return results, None

    # ------------------------
    # WRITE FUNCTIONS
    # ------------------------
    def write_register(self, address, value):
        result, err = self._safe_call(
            self.client.write_register,
            address=address,
            value=value,
        )
        if result is not None:
            return True, None
        return None, err

    # ------------------------
    # UTILITY
    # ------------------------
    @staticmethod
    def registers_to_float(reg1, reg2, wordorder="big"):
        if wordorder == "big":
            raw_bytes = reg1.to_bytes(2, "big") + reg2.to_bytes(2, "big")
        else:
            raw_bytes = reg2.to_bytes(2, "big") + reg1.to_bytes(2, "big")
        return struct.unpack(">f", raw_bytes)[0]

    # ------------------------
    # PORT DISCOVERY
    # ------------------------
    @staticmethod
    def probe_modbus_ports(
        baudrate=9600,
        bytesize=8,
        parity="N",
        stopbits=1,
        timeout=1,
        test_register=1000,
    ) -> List[str]:
        valid_ports = []
        
        for port in list_ports.comports():
            client = None
            try:
                client = ModbusSerialClient(
                    port=port.device,
                    baudrate=baudrate,
                    bytesize=bytesize,
                    parity=parity,
                    stopbits=stopbits,
                    timeout=timeout,
                )

                if not client.connect():
                    continue
                
                time.sleep(0.05)

                # simple probe to verify connection
                result = client.read_holding_registers(
                    address=test_register,
                    count=1,
                )

                if result and not result.isError():
                    valid_ports.append(port.device)

            except Exception:
                pass
            finally:
                if client:
                    client.close()

        return valid_ports

    # ------------------------
    # AUTO-CONNECT TO MODBUS PORT
    # ------------------------
    @staticmethod
    def auto_connect(
        baudrate=9600,
        bytesize=8,
        parity="N",
        stopbits=1,
        timeout=1,
        test_register=1000,
    ) -> Tuple[Optional["ModbusHelper"], Optional[str]]:

        ports = [p.device for p in list_ports.comports()]

        for port in ports:
            client = ModbusSerialClient(
                port=port,
                baudrate=baudrate,
                bytesize=bytesize,
                parity=parity,
                stopbits=stopbits,
                timeout=timeout,
            )

            try:
                if not client.connect():
                    continue
                try:
                    result = client.read_holding_registers(address=test_register, count=1)
                    if result is None or result.isError():
                        client.close()
                        continue
                except Exception:
                    client.close()
                    continue
                return ModbusHelper(client, port=port), port

            except Exception:
                if client:
                    client.close()
                continue
            
        return None, None
