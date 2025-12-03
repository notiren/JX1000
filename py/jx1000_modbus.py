"""
Author: Neriton Pacarizi

"""

from pymodbus.client import ModbusSerialClient
from pymodbus.exceptions import ModbusException, ModbusIOException
import time
import struct
import json

# Helpers

def read_single_register(client, start, count):
    """Read N consecutive single registers."""
    try:
        response = client.read_holding_registers(start, count=count)
        if response.isError():
            return None, f"Error reading: {response}"
        return response.registers, None

    except ModbusIOException:
        return None, "No response from device (ModbusIOException)"
    except ModbusException as e:
        return None, f"Modbus protocol error: {e}"
    except Exception as e:
        return None, f"Unknown error: {e}"


def read_mapped_pair(client, start, num_pairs):
    """
    Mapping:
    Input range: 1000-1499
    Each input maps to 2 registers:
        1000 > 1000,1001
        1001 > 1002,1003
        ...
        1499 > 1998,1999
    """
    
    if not (1000 <= start <= 1499):
        return None, "Mapped read requires 1000-1499 input"
    max_last = start + num_pairs - 1
    if max_last > 1499:
        return None, f"Requested range exceeds 1499 (max allowed end is {1499})"
    
    results = []
    try:
        for src in range(start, start + num_pairs):

            base = 1000 + (src - 1000) * 2

            response = client.read_holding_registers(address=base, count=2)

            if response.isError():
                return None, f"Error reading mapped pair at {src}: {response}"

            results.append({
                "input_target": src,
                "mapped_registers": [base, base + 1],
                "values": response.registers
            })
        return results, None

    except ModbusIOException:
        return None, "No response from device (ModbusIOException)"
    except ModbusException as e:
        return None, f"Modbus protocol error: {e}"
    except Exception as e:
        return None, f"Unknown error: {e}"


def write_register(client, address, value):
    """Write a single holding register."""
    try:
        response = client.write_register(address, value)
        if response.isError():
            return None, f"Error writing: {response}"
        return True, None

    except ModbusIOException:
        return None, "No response from device (ModbusIOException)"
    except ModbusException as e:
        return None, f"Modbus protocol error: {e}"
    except Exception as e:
        return None, f"Unknown error: {e}"
        

def registers_to_float(reg1, reg2, wordorder="big"):
    if wordorder == "big":
        raw_bytes = reg1.to_bytes(2, byteorder='big') + reg2.to_bytes(2, byteorder='big')
    else:
        raw_bytes = reg2.to_bytes(2, byteorder='big') + reg1.to_bytes(2, byteorder='big')
    
    return struct.unpack('>f', raw_bytes)[0]


# MAIN #

def main():
    # Load config
    with open("config.json", "r") as f:
        load_config = json.load(f)
    config = load_config["modbus"]

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
    client.target = config["target"]

    if not client.connect():
        print("Failed to connect to Modbus device.")
        return

    print("--Connected to Modbus device--")
    print("Choose an option:")
    print("1. Read single register(s)")
    print("2. Read mapped pair(s) (mapping 1000–1499)")
    print("3. Write int register")
    print("4. Start Test sequence")

    choice = input("Enter 1-4: ").strip()

    # Option 1 - Read single register(s)
    if choice == "1":
        start = int(input("Enter register address: "))
        count = int(input("Number of registers:  "))
        values, err = read_single_register(client, start, count)
        if err:
            print(err)
        else:
            for i, v in enumerate(values):
                print(f"[{start + i}] = {v}")

    # Option 2 - Read mapped pairs
    elif choice == "2":
        start = int(input("Enter register address (1000–1499): "))
        num_pairs = int(input("Number of pairs to read: "))
        results, err = read_mapped_pair(client, start, num_pairs)
        if err:
            print(err)
        else:
            for entry in results:
                a, b = entry["mapped_registers"]
                v1, v2 = entry["values"]
                voltage = registers_to_float(v1, v2, wordorder="big")
                print(f"[{entry['input_target']}] > {a}, {b} = {v1}, {v2}")
                print(f"Voltage: {voltage}V")

    # Option 3 - Write registers
    elif choice == "3":
        address = int(input("Enter register address to write: "))
        value = int(input("Enter value to write: "))

        # Output 1
        if address == 120 and value == 1:
            ok, err = write_register(client, 121, 0)
            ok, err = write_register(client, 120, 1)
        elif address == 120 and value == 0:
            ok, err = write_register(client, 120, 0)
            ok, err = write_register(client, 121, 1)
        # Output 2
        elif address == 130 and value == 1:
            ok, err = write_register(client, 131, 0)
            ok, err = write_register(client, 130, 1)
        elif address == 130 and value == 0:
            ok, err = write_register(client, 130, 0)
            ok, err = write_register(client, 131, 1)
        else:
            ok, err = write_register(client, address, value)

        if err:
            print(err)
        else:
            print(f"Successfully wrote {value} to register {address}")

    # Option 4 - Test sequence
    elif choice == "4":
        trigger_address = 20
        result_address = 23
        write_register(client, trigger_address, 1)
        time.sleep(0.001)
        test_result, err = read_single_register(client, result_address, 1)
        result = [{0: "Not tested", 1: "PASS", 2: "NG"}.get(x, "Unknown") for x in test_result][0]
        if err:
            print(err)
        else:
            print(f"Test result: {result}")

    else:
        print("Invalid choice.")

    client.close()

#
# Entry point
# 
if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        exit(0)
    except Exception as e:
        exit(0)
    