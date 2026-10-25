"""Reproducible experiment log, not production tests or human approval.

Native window routing is read with WindowFromPoint; Qt gestures are sent to
real widgets. Synthetic DPR renders are explicitly distinct from real monitors.
"""
import ctypes
from ctypes import wintypes
import hashlib
import json
import statistics
from time import perf_counter

from PySide6.QtCore import QPoint, QRectF, Qt
from PySide6.QtGui import QPainter, QColor, QImage
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QWidget

from preview import ROOT, FROZEN, VIEW, Pet, Model, Renderer, alpha_region, image

app=QApplication([])
assert app.platformName()=='windows'
OUT=ROOT/'evidence'; OUT.mkdir(exist_ok=True)
pet=Pet(); pet.timer.stop()
receiver=QWidget(); receiver.setWindowTitle('V5 temporary native hit receiver')
receiver.setGeometry(700,200,500,500); receiver.show()
pet.move(740,240); pet.show(); app.processEvents()

user32=ctypes.windll.user32
user32.WindowFromPoint.argtypes=[wintypes.POINT]
user32.WindowFromPoint.restype=wintypes.HWND

def hit(local):
    q=pet.mapToGlobal(local)
    return int(user32.WindowFromPoint(wintypes.POINT(q.x(),q.y())) or 0)

record={'kind':'native Windows experiment; no human visual approval',
 'platform':app.platformName(),
 'screens':[{'name':s.name(),'geometry':s.geometry().getRect(),'work_area':s.availableGeometry().getRect(),'dpr':s.devicePixelRatio()} for s in app.screens()],
 'frozen_commit':'32c9f985d4467c1527b09c34f6868a3ccd3f85b4',
 'sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in FROZEN.iterdir()},
 'sizes':[], 'gestures':{}, 'dpr_raster_only':[],
 'limits':['Only one physical 100% monitor is present. No real cross-monitor or mixed-DPI drag has been performed.','QTest gestures are widget events; OS routing is separately read with WindowFromPoint.','Human feedback is recorded separately on the decision issue; this experiment log does not grant visual approval.']}

for size in (188,271,320):
    pet.size_px=size; pet.snap(0)
    origin=pet.pos(); entry={'height_setting':size,'canvas_dip':[pet.width(),pet.height()],'poses':[]}
    old=pet.region
    for stage in range(4):
        for peak in (False,True):
            pet.snap(stage,peak); app.processEvents()
            assert pet.pos()==origin
            assert pet.rect().contains(pet.region.boundingRect())
            bounds=pet.region.boundingRect()
            assert bounds.left()>0 and bounds.top()>0 and bounds.right()<pet.width()-1 and bounds.bottom()<pet.height()-1
            pet.frame.save(str(OUT/f'{size}-stage{stage}-{"peak" if peak else "rest"}.png'))
            corner=QPoint(2,2)
            assert hit(corner)==int(receiver.winId()),('transparent target',size,stage,peak,hit(corner))
            center=bounds.center()
            while not pet.region.contains(center): center.setY(center.y()+1)
            assert hit(center)==int(pet.winId()),('visible target',size,stage,peak)
            entry['poses'].append({'stage':stage,'peak':peak,'alpha_bounds_dip':bounds.getRect(),'region_changed':old!=pet.region,'visible_target':'pet','transparent_target':'receiver','render_and_mask_ms':round(pet.render_ms,3)})
            old=pet.region
    entry['edge_contacts']=[]
    for x,y in ((-999,-999),(9999,-999),(-999,9999),(9999,9999)):
        pet.move_visible(QPoint(x,y),pet.screen()); app.processEvents()
        area=pet.screen().availableGeometry()
        for stage in range(4):
            for peak in (False,True):
                pet.snap(stage,peak)
                visible=pet.region.boundingRect().translated(pet.pos())
                assert area.contains(visible)
                assert visible.left()==area.left() if x<0 else visible.right()==area.right()
                assert visible.top()==area.top() if y<0 else visible.bottom()==area.bottom()
        entry['edge_contacts'].append({'corner':[x<0,y<0],'all_poses_and_peaks_flush':True,'visible_bounds':visible.getRect(),'work_area':area.getRect()})
    pet.pinned_x=pet.pinned_y=None; pet.move(740,240)
    record['sizes'].append(entry)

# Fresh click stages and blink midpoint, driven by exact frozen time model.
pet.reset(); pet.frozen=True
stages=[]
for i in range(4):
    point=pet.region.boundingRect().center()
    QTest.mouseClick(pet,Qt.MouseButton.LeftButton,pos=point)
    pet.timer.stop(); pet.frozen=True
    pet.model.tick(500); pet.age=500; pet.render_frame()
    s=pet.model.state(); stages.append({'stage':s['stage'],'eye':s['eye']%41,'body':s['body']%41,'blinks':s['blinks']})
assert [s['stage'] for s in stages]==[1,2,3,0]
assert stages[1]['blinks']==0 and stages[2]['blinks']==1
pet.snap(2); pet.model.next(); pet.model.tick(119)
before=pet.model.state(); pet.model.tick(1); midpoint=pet.model.state(); pet.model.tick(120); after=pet.model.state()
assert before['eye']%41==24 and midpoint['eye']%41==34 and after['body']%41==34

# Drag while the head and pulse are moving; release never advances the stage.
pet.reset(); pet.model.next(); pet.age=55; pet.model.tick(55); pet.render_frame(); pet.frozen=True
s=pet.model.state(); point=pet.region.boundingRect().center()
QTest.mousePress(pet,Qt.MouseButton.LeftButton,pos=point)
QTest.mouseMove(pet,point+QPoint(130,70),delay=1)
pet.model.tick(80); pet.age+=80; pet.render_frame()
QTest.mouseRelease(pet,Qt.MouseButton.LeftButton,pos=point+QPoint(130,70))
assert pet.model.state()['clicks']==s['clicks'] and pet.drag_count==1
dragpos=pet.pos(); pet.model.tick(500); pet.age=1000; pet.render_frame()
assert pet.pos()==dragpos
record['gestures']['four_clicks']=stages
record['gestures']['blink']={'before_120ms':before,'at_120ms':midpoint,'at_240ms':after}
record['gestures']['animated_drag']={'click_count_unchanged':True,'drag_count':pet.drag_count,'position_after_release_stable':True}

pet.reset()
for i in range(5):
    pet.model.next(); pet.model.tick(45); pet.age=45
pet.model.tick(1500)
assert pet.model.state()['clicks']==5 and pet.model.state()['stage']==1
record['gestures']['rapid_five']=pet.model.state()

pet.reset(); pet.select_mode('always')
starts=[]; count=pet.model.state()['clicks']
for ms in range(0,5000,10):
    pet.advance_elapsed(10)
    now=pet.model.state()['clicks']
    if now!=count: starts.append(ms+10); count=now
assert pet.model.state()['cycles']>=1 and count>=6
assert min(b-a for a,b in zip(starts,starts[1:]))>=660
record['gestures']['continuous_v5_5000ms']={'state':pet.model.state(),'automatic_action_times_ms':starts,'pulse_restarts':True,'wait_after_busy_ms':450}
pet.select_mode('click')
for i in range(150): pet.advance_elapsed(10)
settled=pet.model.state()
for i in range(50): pet.advance_elapsed(10)
assert pet.model.state()['eye']==settled['eye'] and pet.model.state()['body']==settled['body']
record['gestures']['switch_to_click_hold']=settled

model=Model(); renderer=Renderer()
for dpr in (1,1.25,1.5,2):
    im=renderer.render(model,model.state(),110,320,dpr)
    region=alpha_region(im)
    record['dpr_raster_only'].append({'dpr':dpr,'physical_pixels':[im.width(),im.height()],'logical_region':region.boundingRect().getRect()})
    im.save(str(OUT/f'synthetic-dpr-{dpr}.png'))

# Sample all head phases and both extremal pulse widths, then check margins.
geometry=[]; durations=[]
for i in range(165):
    phase=i*41/164
    model.run(f's.eye=s.body={phase}')
    for age in (10000,110):
        start=perf_counter(); im=renderer.render(model,model.state(),age,320)
        region=alpha_region(im); durations.append((perf_counter()-start)*1000)
        b=region.boundingRect()
        assert b.left()>0 and b.top()>0 and b.right()<im.width()-1 and b.bottom()<im.height()-1
        geometry.append((b.left(),b.top(),b.right(),b.bottom()))
record['sampling']={'phase_samples':165,'pulse_extrema':2,'raster_render_count':330,'union_bounds_dip':[min(b[0] for b in geometry),min(b[1] for b in geometry),max(b[2] for b in geometry),max(b[3] for b in geometry)],'render_plus_region_median_ms':statistics.median(durations),'render_plus_region_p95_ms':sorted(durations)[int(len(durations)*.95)],'all_samples_inside_canvas':True,'note':'Dense raster samples, not an analytic proof of all continuous poses.'}

# A contact sheet of actual native raster output, on a neutral background.
sheet=image(4*300,2*350); sheet.fill(QColor('#e7e9e2'))
p=QPainter(sheet)
for stage in range(4):
    for peak in (False,True):
        im=QImage(str(OUT/f'320-stage{stage}-{"peak" if peak else "rest"}.png'))
        p.drawImage(QRectF(stage*300,(1 if peak else 0)*350,300,292),im)
        p.setPen(QColor('#26372c')); p.drawText(stage*300+10,(1 if peak else 0)*350+320,f'Stage {stage} / {"peak" if peak else "rest"}')
p.end(); sheet.save(str(OUT/'native-contact-sheet.png'))
(OUT/'observations.json').write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'sizes':len(record['sizes']),'sampling':record['sampling'],'limits':record['limits']},ensure_ascii=False))
pet.close(); receiver.close()
