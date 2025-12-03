"""
Author: Neriton Pacarizi

Loaded: JX1000API, Version=1.0.0.0, Culture=neutral, PublicKeyToken=null

=== DLL CONTENTS ===
JX1000.EVENT_CODE
JX1000.EFRAME
JX1000.TRcvData
JX1000.JX1000_API
JX1000.JX1000_API+TRULE_DOWN
JX1000.JX1000_API+TINFOR
JX1000.JX1000_API+DEV_REQUEST
JX1000.JX1000_API+DEV_RETURN
JX1000.JX1000_API+ERuleDown
JX1000.JX1000_API+RcvDealDelegate
JX1000.CBuf
JX1000.JX1000_API+<>c__DisplayClass1

"""

import sys
import clr
import queue
import threading
from System import Single

DLL_PATH = r"C:\Users\NeritonPaçarizi\Documents\Scripts\JX1000_test\dll\JX1000API.dll"
clr.AddReference(DLL_PATH)

from JX1000 import JX1000_API, EVENT_CODE

# create API instance
jx = JX1000_API()
event_queue = queue.Queue()

# Helpers
def clear():
    print("\r\x1b[2K", end="", flush=True)

def prompt(text):
    print("\r\x1b[2K" + text, end="", flush=True)
    return input()

event_code_map = {
    "PortOpen": "Port open",
    "PortClose": "Port close",
    "PortError": "Port error",
    "TesterConnSuc": "Tester connected successfully",
    "TesterData": "Tester data received",
    "TesterDownload": "Rule file downloaded",
    "TesterDownloadPro": "Download progress"
}

field_translation = {
    "类型": "Type",
    "版本": "Version",
    "接口板": "Interface board",
    "板卡数": "Board count",
    "进度": "Progress",
    "打开端口成功": "Port opened successfully",
    "端口未打开": "Port not opened",
    "打开端口失败": "Failed to open port",
    "端口已打开": "Port already opened",
    "关闭端口": "Port closed",
    "端口错误": "Port error",
}

def translate_event(code, value):
    code_text = event_code_map.get(str(code), str(code))
    translated_value = value
    for cn, en in field_translation.items():
        translated_value = translated_value.replace(cn, en)
    
    return f"[EVENT] {code_text} -> {translated_value}"


# ---------- EVENTS ----------
RcvDelegate = JX1000_API.RcvDealDelegate

def on_event(code, value):
    event_queue.put((code, value))

jx.RcvDealHandler = RcvDelegate(on_event)

# Event printer
def event_printer():
    while True:
        code, value = event_queue.get()
        event_text = translate_event(code, value)

        print("\r\x1b[2K" + event_text)
        print(">> ", end="", flush=True)

threading.Thread(target=event_printer, daemon=True).start()

# ---------- MAIN MENU ----------
def open_port():
    port = prompt("Enter COM port: ").strip()
    jx.OpenPort(port)

def close_port():
    jx.ClosePort()

def start_test():
    jx.TestStart()

def stop_test():
    print("Test stopped")
    jx.TestStop()

def read_board():
    com = int(prompt("Board index (≥ 1): "))
    ch = int(prompt("Channel index (1–8): "))
    addr = int(prompt("Memory address: "))
    data = Single(0)
    status, ret = jx.DevRead(com, ch, addr, 100, data)
    print(f"Read status = {ret}, value = {data}")

def write_board():
    com = int(prompt("Board index (≥ 1): "))
    ch = int(prompt("Channel index (1–8): "))
    addr = int(prompt("Memory address: "))
    val = float(prompt("Write value (float): "))
    status = jx.DevWrite(com, ch, addr, val)
    print(f"Write status = {status}, written = {val}")
    
def download_rules():
    path = prompt("Enter path to .jx1000 rules file: ").strip().strip('"').strip("'")
    try:
        with open(path, "rb") as f:
            buf = f.read()
            
        jx.DownloadRules(buf)
        print(f"Rules file downloaded successfully!")
    except FileNotFoundError:
        print("File not found!")
    except Exception as e:
        print("Error downloading rules:", e)

actions = {
    "1": open_port,
    "2": close_port,
    "3": start_test,
    "4": stop_test,
    "5": read_board,
    "6": write_board,
    "7": download_rules
}

def print_menu():
    print("1. Open Port")
    print("2. Close Port")
    print("3. Start Test")
    print("4. Stop Test")
    print("5. Read Board Memory")
    print("6. Write Board Memory")
    print("7. Download rules file")
    print("q. Exit")


# --- Main ---    
    
def main():
    print("=== JX1000 Console ===")
    print("Type 'm' to show menu at any time. Type 'q' to exit.")
    print_menu()
     
    while True:
        choice = prompt(">> ").strip().lower()
        if choice == "q":
            break
        elif choice == "m":
            print_menu()
        elif choice in actions:
            actions[choice]()
        else:
            print("Invalid selection.")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nUser terminated the script.")
        sys.exit(1)
    except Exception as e:
        print(f"\nAn unexpected error occurred: {e}")
        sys.exit(1)    