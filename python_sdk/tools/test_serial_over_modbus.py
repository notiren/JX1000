import serial
import time

# Configure serial port
ser = serial.Serial(
    port='COM6',           
    baudrate=9600,
    bytesize=serial.EIGHTBITS,
    parity=serial.PARITY_NONE,
    stopbits=serial.STOPBITS_ONE,
    timeout=1
)

# CRC16 Modbus calculation
def crc16(data: bytes):
    crc = 0xFFFF
    for b in data:
        crc ^= b
        for _ in range(8):
            if crc & 0x0001:
                crc >>= 1
                crc ^= 0xA001
            else:
                crc >>= 1
    return crc.to_bytes(2, byteorder='little')

# Write Single Register Request (FC 0x06)
slave_id = 1
register = 100     # 0-based Modbus address
value = 0x0001     # Value to write

request = bytes([
    slave_id,
    0x06,                     # Write Single Register
    (register >> 8) & 0xFF,
    register & 0xFF,
    (value >> 8) & 0xFF, 
    value & 0xFF
])

request += crc16(request)
print("TX:", request.hex(" "))

# Send request
ser.write(request)
time.sleep(0.2) 

# Read response
response = ser.read(8)
print("RX:", response.hex(" ") if response else "no response")

# Validate response
if len(response) == 8:
    rx_crc = response[-2:]
    calc_crc = crc16(response[:-2])

    if rx_crc == calc_crc:
        print(f"Successfully wrote {value} to register {register}")
    else:
        print("CRC mismatch! Bad response.")
else:
    print("No response or incomplete data received.")

ser.close()
