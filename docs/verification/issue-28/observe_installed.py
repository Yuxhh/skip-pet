"""Read-only installed-window evidence capture; run from the source root.

No OS input is injected. --clicks selects a known stationary reference only;
omit it for continuous playback or an unknown pose.
"""

import argparse
import ctypes
import json
from ctypes import wintypes
from pathlib import Path
from hashlib import sha256
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QImage,QPainter,QColor
from sukuna_pet.playback import PetApplication
from sukuna_pet.rendering import CharacterRenderer
parser=argparse.ArgumentParser(); parser.add_argument('name'); parser.add_argument('--clicks',type=int,default=None); parser.add_argument('--height',type=int,default=320); parser.add_argument('--background',default='light'); args=parser.parse_args()
app=QApplication([])
user32=ctypes.windll.user32; gdi32=ctypes.windll.gdi32
user32.GetWindowRect.argtypes=[wintypes.HWND,ctypes.POINTER(wintypes.RECT)]
user32.GetWindowThreadProcessId.argtypes=[wintypes.HWND,ctypes.POINTER(wintypes.DWORD)]
user32.GetWindowTextW.argtypes=[wintypes.HWND,wintypes.LPWSTR,ctypes.c_int]
user32.IsWindowVisible.argtypes=[wintypes.HWND]
user32.GetWindowRgn.argtypes=[wintypes.HWND,wintypes.HANDLE]
user32.GetWindowLongPtrW.argtypes=[wintypes.HWND,ctypes.c_int];user32.GetWindowLongPtrW.restype=ctypes.c_ssize_t
user32.WindowFromPoint.argtypes=[wintypes.POINT];user32.WindowFromPoint.restype=wintypes.HWND
gdi32.CreateRectRgn.argtypes=[ctypes.c_int]*4;gdi32.CreateRectRgn.restype=wintypes.HANDLE
gdi32.GetRgnBox.argtypes=[wintypes.HANDLE,ctypes.POINTER(wintypes.RECT)]
gdi32.PtInRegion.argtypes=[wintypes.HANDLE,ctypes.c_int,ctypes.c_int]
gdi32.DeleteObject.argtypes=[wintypes.HANDLE]
windows=[]
@ctypes.WINFUNCTYPE(wintypes.BOOL,wintypes.HWND,wintypes.LPARAM)
def enum(hwnd,_):
    title=ctypes.create_unicode_buffer(256);user32.GetWindowTextW(hwnd,title,256)
    if title.value=='宿傩桌宠' and user32.IsWindowVisible(hwnd): windows.append(hwnd)
    return True
user32.EnumWindows(enum,0)
assert len(windows)==1,windows
hwnd=windows[0];pid=wintypes.DWORD();user32.GetWindowThreadProcessId(hwnd,ctypes.byref(pid))
window_rect=wintypes.RECT();user32.GetWindowRect(hwnd,ctypes.byref(window_rect));width,height=window_rect.right-window_rect.left,window_rect.bottom-window_rect.top
region=gdi32.CreateRectRgn(0,0,0,0);user32.GetWindowRgn(hwnd,region);region_bounds=wintypes.RECT();gdi32.GetRgnBox(region,ctypes.byref(region_bounds))
screen=app.primaryScreen();captured_frame=screen.grabWindow(0,window_rect.left,window_rect.top,width,height).toImage().convertToFormat(QImage.Format.Format_RGBA8888)
output=Path('docs/verification/issue-28/installed');output.mkdir(exist_ok=True)
captured_frame.save(str(output/f'{args.name}.png'))
points=[]
for x,y in [(2,2),((region_bounds.left+region_bounds.right)//2,(region_bounds.top+region_bounds.bottom)//2),(region_bounds.left+2,region_bounds.bottom-2)]:
    points.append({'local':[x,y],'in_region':bool(gdi32.PtInRegion(region,x,y)),'hit_hwnd':int(user32.WindowFromPoint(wintypes.POINT(window_rect.left+x,window_rect.top+y)) or 0)})
pet=PetApplication()
for _ in range(args.clicks or 0):pet.click();pet.advance(1000)
expected=CharacterRenderer().render(pet.view,args.height,1)
reference='current production renderer; static opaque pixels only'
if args.clicks==1:
    expected=QImage(f'tests/fixtures/bounce-native/first_recovered-{args.height}-1.png')
    reference='frozen native 4ecb85c8a087ca89fb99a3a2125c826801b53e1c, first_recovered at 220ms; opaque pixels only'
background=QImage(width,height,QImage.Format.Format_RGBA8888);background.fill(QColor('#263347' if args.background=='dark' else '#f3f2ee'))
painter=QPainter(background)
if args.background=='texture':
    # Receiver paints 18px squares relative to its client origin; compare foreground only.
    pass
painter.drawImage(0,0,expected);painter.end()
actual=bytes(captured_frame.constBits());want=bytes(background.constBits());rgba=expected.convertToFormat(QImage.Format.Format_RGBA8888);alpha=bytes(rgba.constBits())
compared=[]
for y in range(min(height,expected.height())):
    for x in range(min(width,expected.width())):
        i=y*rgba.bytesPerLine()+x*4
        if alpha[i+3]==255:
            j=y*captured_frame.bytesPerLine()+x*4;k=y*background.bytesPerLine()+x*4
            compared.append(max(abs(actual[j+c]-want[k+c]) for c in range(3)))
record={'name':args.name,'hwnd':int(hwnd),'pid':pid.value,'window':[window_rect.left,window_rect.top,width,height],'region_bounds':[region_bounds.left,region_bounds.top,region_bounds.right-region_bounds.left,region_bounds.bottom-region_bounds.top],'topmost':bool(user32.GetWindowLongPtrW(hwnd,-20)&8),'points':points,'expected_stage_clicks':args.clicks,'expected_height':args.height,'opaque_pixel_comparison':{'pixels':len(compared),'max_channel_difference':max(compared,default=0),'different_pixels':sum(d>0 for d in compared)},'screenshot_sha256':sha256((output/f'{args.name}.png').read_bytes()).hexdigest()}
record['reference']=reference
if args.clicks is None:
    record.pop('opaque_pixel_comparison');record.pop('expected_stage_clicks');record['scope']='Uncontrolled pose; geometry and OS hit observation only, no fixed-stage pixel comparison'
(output/f'{args.name}.json').write_text(json.dumps(record,indent=2),encoding='utf8');print(json.dumps(record,indent=2));gdi32.DeleteObject(region)
