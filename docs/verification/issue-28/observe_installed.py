import argparse, ctypes, json, sys
from ctypes import wintypes
from pathlib import Path
from hashlib import sha256
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QImage,QPainter,QColor
from sukuna_pet.playback import PetApplication
from sukuna_pet.rendering import CharacterRenderer
p=argparse.ArgumentParser(); p.add_argument('name'); p.add_argument('--clicks',type=int,default=None); p.add_argument('--height',type=int,default=320); p.add_argument('--background',default='light'); a=p.parse_args()
app=QApplication([])
u=ctypes.windll.user32; g=ctypes.windll.gdi32
u.GetWindowRect.argtypes=[wintypes.HWND,ctypes.POINTER(wintypes.RECT)]
u.GetWindowThreadProcessId.argtypes=[wintypes.HWND,ctypes.POINTER(wintypes.DWORD)]
u.GetWindowTextW.argtypes=[wintypes.HWND,wintypes.LPWSTR,ctypes.c_int]
u.IsWindowVisible.argtypes=[wintypes.HWND]
u.GetWindowRgn.argtypes=[wintypes.HWND,wintypes.HANDLE]
u.GetWindowLongPtrW.argtypes=[wintypes.HWND,ctypes.c_int];u.GetWindowLongPtrW.restype=ctypes.c_ssize_t
u.WindowFromPoint.argtypes=[wintypes.POINT];u.WindowFromPoint.restype=wintypes.HWND
g.CreateRectRgn.argtypes=[ctypes.c_int]*4;g.CreateRectRgn.restype=wintypes.HANDLE
g.GetRgnBox.argtypes=[wintypes.HANDLE,ctypes.POINTER(wintypes.RECT)]
g.PtInRegion.argtypes=[wintypes.HANDLE,ctypes.c_int,ctypes.c_int]
g.DeleteObject.argtypes=[wintypes.HANDLE]
windows=[]
@ctypes.WINFUNCTYPE(wintypes.BOOL,wintypes.HWND,wintypes.LPARAM)
def enum(hwnd,_):
    t=ctypes.create_unicode_buffer(256);u.GetWindowTextW(hwnd,t,256)
    if t.value=='宿傩桌宠' and u.IsWindowVisible(hwnd): windows.append(hwnd)
    return True
u.EnumWindows(enum,0)
assert len(windows)==1,windows
hwnd=windows[0];pid=wintypes.DWORD();u.GetWindowThreadProcessId(hwnd,ctypes.byref(pid))
r=wintypes.RECT();u.GetWindowRect(hwnd,ctypes.byref(r));w,h=r.right-r.left,r.bottom-r.top
region=g.CreateRectRgn(0,0,0,0);u.GetWindowRgn(hwnd,region);b=wintypes.RECT();g.GetRgnBox(region,ctypes.byref(b))
screen=app.primaryScreen();shot=screen.grabWindow(0,r.left,r.top,w,h).toImage().convertToFormat(QImage.Format.Format_RGBA8888)
out=Path('docs/verification/issue-28/installed');out.mkdir(exist_ok=True)
shot.save(str(out/f'{a.name}.png'))
points=[]
for x,y in [(2,2),((b.left+b.right)//2,(b.top+b.bottom)//2),(b.left+2,b.bottom-2)]:
    points.append({'local':[x,y],'in_region':bool(g.PtInRegion(region,x,y)),'hit_hwnd':int(u.WindowFromPoint(wintypes.POINT(r.left+x,r.top+y)) or 0)})
pet=PetApplication()
for _ in range(a.clicks or 0):pet.click();pet.advance(1000)
expected=CharacterRenderer().render(pet.view,a.height,1)
reference='current production renderer; static opaque pixels only'
if a.clicks==1:
    expected=QImage(f'tests/fixtures/bounce-native/first_recovered-{a.height}-1.png')
    reference='frozen native 4ecb85c8a087ca89fb99a3a2125c826801b53e1c, first_recovered at 220ms; opaque pixels only'
background=QImage(w,h,QImage.Format.Format_RGBA8888);background.fill(QColor('#263347' if a.background=='dark' else '#f3f2ee'))
painter=QPainter(background)
if a.background=='texture':
    # Receiver paints 18px squares relative to its client origin; compare foreground only.
    pass
painter.drawImage(0,0,expected);painter.end()
actual=bytes(shot.constBits());want=bytes(background.constBits());rgba=expected.convertToFormat(QImage.Format.Format_RGBA8888);alpha=bytes(rgba.constBits())
compared=[]
for y in range(min(h,expected.height())):
    for x in range(min(w,expected.width())):
        i=y*rgba.bytesPerLine()+x*4
        if alpha[i+3]==255:
            j=y*shot.bytesPerLine()+x*4;k=y*background.bytesPerLine()+x*4
            compared.append(max(abs(actual[j+c]-want[k+c]) for c in range(3)))
record={'name':a.name,'hwnd':int(hwnd),'pid':pid.value,'window':[r.left,r.top,w,h],'region_bounds':[b.left,b.top,b.right-b.left,b.bottom-b.top],'topmost':bool(u.GetWindowLongPtrW(hwnd,-20)&8),'points':points,'expected_stage_clicks':a.clicks,'expected_height':a.height,'opaque_pixel_comparison':{'pixels':len(compared),'max_channel_difference':max(compared,default=0),'different_pixels':sum(d>0 for d in compared)},'screenshot_sha256':sha256((out/f'{a.name}.png').read_bytes()).hexdigest()}
record['reference']=reference
if a.clicks is None:
    record.pop('opaque_pixel_comparison');record.pop('expected_stage_clicks');record['scope']='Uncontrolled pose; geometry and OS hit observation only, no fixed-stage pixel comparison'
(out/f'{a.name}.json').write_text(json.dumps(record,indent=2),encoding='utf8');print(json.dumps(record,indent=2));g.DeleteObject(region)
