import clr
import sys
import System
from System.Reflection import Assembly

dll_path = r"C:\Users\NeritonPaçarizi\Documents\Scripts\JX1000_modbus\DLL\JX1000API.dll"
asm = Assembly.LoadFile(dll_path)

print("Loaded:", asm.FullName)
print("\n=== DLL CONTENTS ===")

for type_ in asm.GetTypes():
    print(type_.FullName)
    
    
clr.AddReference(dll_path)
import JX1000

# List all members of a class or module
print(dir(JX1000.JX1000_API))
print(dir(JX1000.EVENT_CODE))
print(dir(JX1000.TRcvData))
print(dir(JX1000))