### DLL Contents  
  
```powershell
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
```

### DLL path and reference

```python
DLL_PATH = r"path to DLL"  
clr.AddReference(DLL_PATH)  
from JX1000 import JX1000_API, EVENT_CODE  
```

### create API instance

```
jx = JX1000_API()   
```

### create and handle events
```python
RcvDelegate = JX1000_API.RcvDealDelegate

def on_event(code, value): 
    print(f"[EVENT] {code} -> {value}") 

jx.RcvDealHandler = RcvDelegate(on_event) 
```

### commands

```python
port = "COMx or /dev/tty/x"

jx.OpenPort(port)  
jx.ClosePort()   
jx.TestStart()   
jx.TestStop()   

com = "Board index >= 1"
ch = "Channel index 1-8"
addr = "Memory address"
from System import Single
data = Single(0)
val = "Write value"
path = "path to rules .jx1000 file"

jx.DevRead(com, ch, addr, 100, data)  
jx.DevWrite(com, ch, addr, val)  
  
jx.DownloadRules(path)  
```