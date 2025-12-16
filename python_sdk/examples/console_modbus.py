"""
Interactive console for Modbus operations on JX1000 devices.
Separate from the Modbus API.
"""

import sys
from pathlib import Path
import json
import time
from pymodbus.client import ModbusSerialClient

repo_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(repo_root))

from jx1000.modbus import ModbusHelper

def main():
    # Load config
    with open(repo_root / "jx1000" / "config.json", "r") as f:
        config = json.load(f)["modbus"]

    # Initialize Modbus client
    port = input("Enter COM port: ")
    client = ModbusSerialClient(
        port=port,
        baudrate=config["baudrate"],
        bytesize=config["bytesize"],
        parity=config["parity"],
        stopbits=config["stopbits"],
        timeout=config["timeout"]
    )

    if not client.connect():
        print("Failed to connect to Modbus device.")
        return

    modbus = ModbusHelper(client)
    print("--Connected to Modbus device--")

    choice = input("Choose: 1) Read 2) Read mapped 3) Write 4) Test: ").strip()

    if choice == "1":
        start = int(input("Enter register address: "))
        count = int(input("Number of registers: "))
        values, err = modbus.read_single_register(start, count)
        if err:
            print(err)
        else:
            for i, v in enumerate(values):
                print(f"[{start + i}] = {v}")

    elif choice == "2":
        start = int(input("Enter register address (1000-1499): "))
        num_pairs = int(input("Number of pairs to read: "))
        results, err = modbus.read_mapped_pair(start, num_pairs)
        if err:
            print(err)
        else:
            for entry in results:
                a, b = entry["mapped_registers"]
                v1, v2 = entry["values"]
                voltage = modbus.registers_to_float(v1, v2)
                print(f"[{entry['input_target']}] > {a},{b} = {v1},{v2} | Voltage: {voltage}V")

    elif choice == "3":
        addr = int(input("Enter register address: "))
        val = int(input("Value: "))
        success, err = modbus.write_register(addr, val)
        if err:
            print(err)
        else:
            print(f"Wrote {val} to register {addr}")

    elif choice == "4":
        trigger_addr = 20
        result_addr = 23
        modbus.write_register(trigger_addr, 1)
        time.sleep(0.001)
        result, err = modbus.read_single_register(result_addr, 1)
        if err:
            print(err)
        else:
            outcome = {0: "Not tested", 1: "PASS", 2: "NG"}.get(result[0], "Unknown")
            print(f"Test result: {outcome}")

    client.close()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Exiting...")
    except Exception as e:
        print(f"Error: {e}")
