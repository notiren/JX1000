import sys
from pathlib import Path

repo_root = Path(__file__).resolve().parents[1]  # points to jx1000_python/
sys.path.insert(0, str(repo_root))

from jx1000.api import JX1000

# -----------------------------
# Helper functions
# -----------------------------
def clear_line():
    print("\r\x1b[2K", end="", flush=True)

def prompt(text: str) -> str:
    clear_line()
    return input(text)

# -----------------------------
# Event printing 
# (if need for custom printing otherwise use flag print_events=True)
# -----------------------------
def event_printer(code, value):
    if isinstance(value, dict):
        value_str = ", ".join(f"{k}={v}" for k, v in value.items())
    else:
        value_str = str(value)
    print(f"\r\x1b[2K[EVENT] {code} -> {value_str}")
    print(">> ", end="", flush=True)

# -----------------------------
# Menu actions
# -----------------------------
def open_port(jx: JX1000):
    port = prompt("Enter COM port: ").strip()
    jx.connect(port=port)
    
def close_port(jx: JX1000):
    jx.disconnect()

def read_board(jx: JX1000):
    try:
        com = int(prompt("Board index (≥1): "))
        ch = int(prompt("Channel index (1–8): "))
        addr = int(prompt("Memory address: "))
        ret = jx.read_memory(com, ch, addr)
    except Exception as e:
        print("Read error:", e)

def write_board(jx: JX1000):
    try:
        com = int(prompt("Board index (≥1): "))
        ch = int(prompt("Channel index (1–8): "))
        addr = int(prompt("Memory address: "))
        val = float(prompt("Value to write: "))
        success = jx.write_memory(com, ch, addr, val)
    except Exception as e:
        print("Write error:", e)

def download_rules(jx: JX1000):
    path = prompt("Enter path to .jx1000 rules file: ").strip().strip('"').strip("'")
    jx.download_rules_from_file(path)
    print("Rule download started...")

def start_test(jx: JX1000):
    jx.start_test()

def stop_test(jx: JX1000):
    jx.stop_test()

# -----------------------------
# Menu
# -----------------------------
def print_menu():
    print("1. Open Port")
    print("2. Close Port")
    print("3. Read Board Memory")
    print("4. Write Board Memory")
    print("5. Download rules file")
    print("6. Start Test")
    print("7. Stop Test")
    print("m. Show menu")
    print("q. Quit\n")

# -----------------------------
# Main loop
# -----------------------------
def main():
    jx = JX1000(event_mode="raw", print_events=True)
    # jx.on_event = event_printer

    actions = {
        "1": lambda: open_port(jx),
        "2": lambda: close_port(jx),
        "3": lambda: read_board(jx),
        "4": lambda: write_board(jx),
        "5": lambda: download_rules(jx),
        "6": lambda: start_test(jx),
        "7": lambda: stop_test(jx),
    }

    print("=== JX1000 Console ===")
    print("Type 'm' to show menu at any time. Type 'q' to exit.\n")
    print_menu()

    while True:
        choice = prompt(">> ").strip().lower()
        if choice == "q":
            break
        elif choice == "m":
            print()
            print_menu()
        elif choice in actions:
            actions[choice]()
        else:
            print("Invalid selection. Type 'm' to show menu.")

    jx.disconnect()
    print("\r\x1b[2KConsole exit.")

# -----------------------------
# Entry point
# -----------------------------
if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\r\x1b[2KConsole exit.")
        exit(0)
    except Exception as e:
        print(f"Unexpected error: {e}")
        exit(0)
