"""Read installed-window geometry without injecting input; single-screen samples only."""
import ctypes
from ctypes import wintypes
import json
from pathlib import Path
import sys
from time import perf_counter, sleep
from PySide6.QtWidgets import QApplication
app=QApplication([])
user32=ctypes.windll.user32;gdi32=ctypes.windll.gdi32
user32.GetWindowTextW.argtypes=[wintypes.HWND,wintypes.LPWSTR,ctypes.c_int]
user32.IsWindowVisible.argtypes=[wintypes.HWND]
user32.GetWindowRect.argtypes=[wintypes.HWND,ctypes.POINTER(wintypes.RECT)]
user32.GetWindowRgn.argtypes=[wintypes.HWND,wintypes.HANDLE]
gdi32.CreateRectRgn.argtypes=[ctypes.c_int]*4;gdi32.CreateRectRgn.restype=wintypes.HANDLE
gdi32.GetRgnBox.argtypes=[wintypes.HANDLE,ctypes.POINTER(wintypes.RECT)]
gdi32.DeleteObject.argtypes=[wintypes.HANDLE]
windows=[]
@ctypes.WINFUNCTYPE(wintypes.BOOL,wintypes.HWND,wintypes.LPARAM)
def collect_window(hwnd,unused):
    title=ctypes.create_unicode_buffer(256);user32.GetWindowTextW(hwnd,title,256)
    if title.value=='宿傩桌宠' and user32.IsWindowVisible(hwnd):windows.append(hwnd)
    return True
user32.EnumWindows(collect_window,0)
assert len(windows)==1,windows
hwnd=windows[0];area=app.primaryScreen().availableGeometry();region=gdi32.CreateRectRgn(0,0,0,0)
samples=[];start=perf_counter()
for index in range(120):
    window_rect=wintypes.RECT();bounds=wintypes.RECT()
    user32.GetWindowRect(hwnd,ctypes.byref(window_rect));user32.GetWindowRgn(hwnd,region);gdi32.GetRgnBox(region,ctypes.byref(bounds))
    after_rect=wintypes.RECT();after_bounds=wintypes.RECT()
    user32.GetWindowRect(hwnd,ctypes.byref(after_rect));user32.GetWindowRgn(hwnd,region);gdi32.GetRgnBox(region,ctypes.byref(after_bounds))
    consistent=bytes(window_rect)==bytes(after_rect) and bytes(bounds)==bytes(after_bounds)
    visible=[window_rect.left+bounds.left,window_rect.top+bounds.top,window_rect.left+bounds.right,window_rect.top+bounds.bottom]
    contacts=[name for name,condition in [('left',visible[0]==area.left()),('top',visible[1]==area.top()),('right',visible[2]==area.right()+1),('bottom',visible[3]==area.bottom()+1)] if condition]
    samples.append({'elapsed_ms':(perf_counter()-start)*1000,'window':[window_rect.left,window_rect.top,window_rect.right-window_rect.left,window_rect.bottom-window_rect.top],'visible_exclusive':visible,'contacts':contacts,'consistent_double_read':consistent,'inside':visible[0]>=area.left() and visible[1]>=area.top() and visible[2]<=area.right()+1 and visible[3]<=area.bottom()+1})
    sleep(.05)
gdi32.DeleteObject(region)
report={'scope':'Installed binary, read-only OS samples, one real screen DPR1.0; not all continuous time or multi-screen proof. Window and region read sequentially, not atomically.','work_area':area.getRect(),'samples':samples,'all_inside':all(s['inside'] for s in samples),'consistent_samples':sum(s['consistent_double_read'] for s in samples),'consistent_violations':sum(s['consistent_double_read'] and not s['inside'] for s in samples),'common_contacts':sorted(set.intersection(*(set(s['contacts']) for s in samples))),'different_window_positions':len({tuple(s['window'][:2]) for s in samples}),'different_visible_rectangles':len({tuple(s['visible_exclusive']) for s in samples})}
Path(sys.argv[1]).write_text(json.dumps(report,indent=2),encoding='utf8')
print(json.dumps({k:v for k,v in report.items() if k!='samples'},indent=2))
