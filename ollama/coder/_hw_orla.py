import subprocess, json, sys
try:
    import winreg
except ImportError:
    winreg = None

ps = r"""
$cpu = (Get-CimInstance Win32_Processor).Name
$bb = Get-CimInstance Win32_BaseBoard
$cs = Get-CimInstance Win32_ComputerSystem
$gpu = (Get-CimInstance Win32_VideoController | ForEach-Object { $_.Name }) -join '; '
[pscustomobject]@{
  CPU = $cpu
  MoboMaker = $bb.Manufacturer
  MoboProduct = $bb.Product
  RAM_GB = [math]::Round($cs.TotalPhysicalMemory/1GB,1)
  GPU = $gpu
  Maker = $cs.Manufacturer
  Model = $cs.Model
} | ConvertTo-Json
"""
r = subprocess.run(["powershell","-NoProfile","-Command", ps], capture_output=True, text=True)
print("STDOUT:", r.stdout)
print("STDERR:", r.stderr)
print("CODE:", r.returncode)
