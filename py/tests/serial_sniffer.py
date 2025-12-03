
import serial
import time
import binascii

# Configure COM11
PORT = "COM11"
BAUD = 9600  # Adjust to match your device settings
TIMEOUT = 0.1  # Non-blocking read

def hex_ascii_line(data: bytes, width: int = 16) -> str:
    """Format bytes into HEX and ASCII columns."""
    lines = []
    for i in range(0, len(data), width):
        chunk = data[i:i+width]
        hex_part = binascii.hexlify(chunk).decode("ascii")
        hex_spaced = " ".join(hex_part[j:j+2] for j in range(0, len(hex_part), 2))
        ascii_part = "".join(chr(b) if 32 <= b <= 126 else "." for b in chunk)
        lines.append(f"{hex_spaced:<{width*3}} | {ascii_part}")
    return "\n".join(lines)

# Open COM11
ser = serial.Serial(PORT, BAUD, timeout=TIMEOUT)
print(f"[+] Sniffing {PORT} at {BAUD} baud. Press Ctrl+C to stop.")

try:
    while True:
        data = ser.read(ser.in_waiting or 1)
        if data:
            ts = time.strftime("%Y-%m-%d %H:%M:%S")
            print(f"\n[{ts}] {len(data)} byte(s) received:")
            print(hex_ascii_line(data))
        else:
            time.sleep(0.01)  # Reduce CPU usage when idle
except KeyboardInterrupt:
    print("\n[+] Stopped sniffing.")
finally:
    ser.close()
