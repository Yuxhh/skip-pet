"""THROWAWAY: native Qt raster/region experiment for the frozen approved V5.

Run .venv/Scripts/python.exe .scratch/sukuna-pet/prototypes/native-v5/preview.py
No installed application, preferences or production modules are modified.
"""
import json
import math
import re
import sys
from pathlib import Path
from time import perf_counter

from PySide6.QtCore import QEvent, QPoint, QPointF, QRect, QRectF, Qt, QTimer
from PySide6.QtGui import QColor, QImage, QLinearGradient, QPainter, QPainterPath, QPen, QPolygonF, QRegion, QTransform
from PySide6.QtQml import QJSEngine
from PySide6.QtWidgets import QApplication, QComboBox, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

ROOT = Path(__file__).resolve().parent
FROZEN = ROOT / 'frozen'
PARAMS = json.loads((FROZEN / 'motion-parameters.json').read_text())
# Source-space viewport: fixed for every pose, including restarted pulses.
# The selected height is the entire fixed canvas, preserving the confirmed
# maximum window height of 320 DIP even when the head extends upward.
VIEW = QRectF(90, -110, 1250, 1220)


def image(w=1419, h=1108):
    result = QImage(w, h, QImage.Format.Format_ARGB32_Premultiplied)
    result.fill(Qt.GlobalColor.transparent)
    return result


def path(start, commands):
    p = QPainterPath(QPointF(*start))
    for c in commands:
        if len(c) == 2:
            p.lineTo(*c)
        else:
            p.cubicTo(*c)
    p.closeSubpath()
    return p


HEAD = path((0, 0), [(1419, 0), (1419, 390), (938, 390), (939,425,933,476,899,513), (882,535), (857,592,820,634,780,652), (662,655), (624,633,596,604,579,567), (565,544), (534,532,508,507,496,474), (486,450,487,424,491,412), (465,390), (0,390)])
FRONT = path((454,606), [(600,671,828,663,998,598), (975,757), (882,824), (532,823)])
REAR = path((454,610), [(470,550,570,500,700,500), (835,500,960,540,998,600), (975,705), (465,710)])
SOCKETS = [path((600,469), [(623,471,646,472,654,476), (663,480,666,484,664,486), (648,489,630,490,621,486), (611,480,605,475,600,469)]), path((776,467), [(793,460,819,455,838,451), (833,465,829,471,817,474), (801,479,788,480,774,478), (776,467)])]
KEYS = [(0,0,0),(8,-10,-5),(13,-20,-9),(20,-28,-8),(24,-29,-7),(27,-27,-6),(31,-20,3),(34,-15,7),(38,-5,6),(41,0,0)]


def painter(im):
    p = QPainter(im)
    p.setRenderHints(QPainter.RenderHint.Antialiasing | QPainter.RenderHint.SmoothPixmapTransform)
    return p


class Model:
    """Execute the unchanged approved JS state machine in Qt, without a browser."""
    def __init__(self):
        self.js = QJSEngine()
        source = (FROZEN / 'eyes.js').read_text() + '\n' + (FROZEN / 'rig.js').read_text()
        # Qt's JS parser lacks object spread; this is the equivalent shallow copy.
        source = source.replace('s={...s}', 's=Object.assign({},s)')
        result = self.js.evaluate(source + '\nthis.Motion=Motion;this.Rig=Rig;var s=Motion.initial();')
        if result.isError():
            raise RuntimeError(result.toString())

    def run(self, code):
        result = self.js.evaluate(code)
        if result.isError():
            raise RuntimeError(result.toString())
        return result

    def state(self):
        return json.loads(self.run('JSON.stringify(s)').toString())

    def tick(self, dt):
        self.run(f'{{let left={dt};while(left>0){{let n=Math.min(left,4);s=Motion.tick(s,n);left-=n}}}}')

    def next(self):
        self.run('s=Motion.next(s)')

    def mode(self, mode):
        self.run('s=Motion.mode(s,' + json.dumps(mode) + ')')

    def pose(self, phase):
        return self.run('Rig.sample(' + str(phase) + ',' + json.dumps(PARAMS['components']) + ')').toVariant()


class Renderer:
    def __init__(self):
        self.base = QImage(str(FROZEN / 'character.png'))
        self.repair = QImage(str(FROZEN / 'head-neck-repair.png'))
        self.rear = image()
        p = painter(self.rear)
        p.setClipPath(REAR)
        p.drawImage(QRectF(0,0,1419,1108), QImage(str(FROZEN / 'rear-collar-complete.png')))
        p.end()
        self.body = self.base.copy()
        p = painter(self.body)
        p.setCompositionMode(QPainter.CompositionMode.CompositionMode_Clear)
        p.fillRect(0,0,1419,660,Qt.GlobalColor.transparent)
        p.end()
        self.front = image()
        p = painter(self.front)
        p.setClipPath(FRONT)
        p.drawImage(0,0,self.base)
        p.end()

    def head(self, phase, closure):
        head = image()
        p = painter(head)
        p.setClipPath(HEAD)
        p.drawImage(0,0,self.base)
        phase %= 41
        for a,b in zip(KEYS,KEYS[1:]):
            if a[0] <= phase <= b[0]:
                t = (phase-a[0])/(b[0]-a[0])
                dx,dy = [a[k]+(b[k]-a[k])*t for k in (1,2)]
                break
        w = (phase-13)/11 if 13<=phase<=24 else (34-phase)/10 if 24<phase<34 else 0
        for i in range(2):
            cx = (652 if i==0 else 818) + dx*(.65 if i==0 else 1) - (12*w if i==0 else 0)
            cy = (476 if i==0 else 465) + dy
            p.save()
            p.setClipPath(SOCKETS[i],Qt.ClipOperation.IntersectClip)
            p.setPen(QPen(QColor('#25181a'),2)); p.setBrush(QColor('#652d2d'))
            p.drawEllipse(QPointF(cx,cy),15,17)
            p.setPen(Qt.PenStyle.NoPen); p.setBrush(QColor('#130e11'))
            p.drawEllipse(QPointF(cx,cy-1),7,11)
            p.setBrush(QColor('#dfcac7')); p.drawEllipse(QPointF(cx-4,cy-5),2,3)
            if closure>0:
                xl,xr = (590,680) if i==0 else (765,847)
                yl = (463 if i==0 else 466)+closure*(33 if i==0 else 25)
                yr = (473 if i==0 else 447)+closure*(33 if i==0 else 30)
                lid = path((xl,430),[(xr,430),(xr,yr),(xl,yl)])
                p.fillPath(lid,QColor('#a19595' if i==0 else '#ecdcd4'))
                p.setPen(QPen(QColor('#251d21'),3)); p.drawLine(QPointF(xl,yl),QPointF(xr,yr))
            p.restore()
        p.setClipping(False)
        g = QLinearGradient(0,634,0,658)
        g.setColorAt(0,QColor(0,0,0,255)); g.setColorAt(1,QColor(0,0,0,0))
        p.setCompositionMode(QPainter.CompositionMode.CompositionMode_DestinationIn)
        p.fillRect(head.rect(),g)
        p.end()
        joint = image()
        p = painter(joint)
        p.save(); p.setClipRect(QRectF(400,590,650,200))
        a = PARAMS['head_plate_alignment']
        p.drawImage(QRectF(a['x'],a['y'],a['width'],a['height']),self.repair)
        p.restore(); p.drawImage(0,0,head); p.end()
        return joint

    @staticmethod
    def point(x,y,m):
        a,b,c,d,tx,ty = m
        X,Y = 710+tx+a*(x-710)+c*(y-650),650+ty+b*(x-710)+d*(y-650)
        u = max(0,min(1,(y-700)/80)); w = 1-u*u*(3-2*u)
        return x+(X-x)*w,y+(Y-y)*w

    def warp(self,p,im,m):
        rows = list(range(700,780,8))+[780,1108]
        cols = list(range(400,1041,40))
        for y,Y in zip(rows,rows[1:]):
            for x,X in zip(cols,cols[1:]):
                for S in [[(x,y),(X,y),(X,Y)],[(x,y),(X,Y),(x,Y)]]:
                    D = [self.point(*q,m) for q in S]
                    (sx,sy),(s1,s2),(s3,s4) = S
                    (dx,dy),(d1,d2),(d3,d4) = D
                    x1,y1,x2,y2 = s1-sx,s2-sy,s3-sx,s4-sy
                    det = x1*y2-x2*y1
                    a,b = ((d1-dx)*y2-(d3-dx)*y1)/det,((d2-dy)*y2-(d4-dy)*y1)/det
                    c,d = ((d3-dx)*x1-(d1-dx)*x2)/det,((d4-dy)*x1-(d2-dy)*x2)/det
                    mx,my = sum(q[0] for q in D)/3,sum(q[1] for q in D)/3
                    grown = []
                    for xx,yy in D:
                        r = math.hypot(xx-mx,yy-my) or 1
                        grown.append(QPointF(xx+(xx-mx)/r*.35,yy+(yy-my)/r*.35))
                    clip = QPainterPath(); clip.addPolygon(QPolygonF(grown)); clip.closeSubpath()
                    p.save(); p.setClipPath(clip,Qt.ClipOperation.IntersectClip)
                    p.setTransform(QTransform(a,b,c,d,dx-a*sx-c*sy,dy-b*sx-d*sy),True)
                    # The affine map is unchanged; bound sampling to this source
                    # triangle instead of resampling the entire 1419px texture.
                    source=QRectF(x-1,y-1,X-x+2,Y-y+2)
                    p.drawImage(source,im,source); p.restore()
        a,b,c,d,tx,ty = m
        p.save(); p.translate(710+tx,650+ty)
        p.setTransform(QTransform(a,b,c,d,0,0),True); p.translate(-710,-650)
        p.drawImage(QRectF(0,0,1419,701),im,QRectF(0,0,1419,701)); p.restore()

    def render(self,model,state,age,height,dpr=1):
        scale = height/VIEW.height()
        width,hh = math.ceil(VIEW.width()*scale),math.ceil(VIEW.height()*scale)
        result = image(math.ceil(width*dpr),math.ceil(hh*dpr))
        result.setDevicePixelRatio(dpr)
        p = painter(result)
        p.scale(scale,scale); p.translate(-VIEW.x(),-VIEW.y())
        pulse = math.sin(math.pi*age/220) if 0<=age<220 else 0
        p.translate(709.5,1108); p.scale(1+.1*pulse,1-.15*pulse); p.translate(-709.5,-1108)
        p.drawImage(0,0,self.rear); p.drawImage(0,0,self.body)
        blink = state['blinkAge']
        closure = .5-.5*math.cos(2*math.pi*blink/240) if blink is not None and blink<240 else 0
        self.warp(p,self.head(state['eye'],closure),model.pose(state['body']))
        p.drawImage(0,0,self.front); p.end()
        return result


def alpha_region(im):
    """Physical-pixel alpha, then conservative coverage to logical mouse region."""
    dpr = im.devicePixelRatio()
    alpha = im.convertToFormat(QImage.Format.Format_RGBA8888)
    buf = bytes(alpha.constBits())
    region = QRegion()
    for y in range(im.height()):
        row = buf[y*alpha.bytesPerLine()+3:y*alpha.bytesPerLine()+im.width()*4:4]
        for run in re.finditer(b'[^\x00]+',row):
            l,t = math.floor(run.start()/dpr),math.floor(y/dpr)
            r,b = math.ceil(run.end()/dpr),math.ceil((y+1)/dpr)
            region |= QRegion(l,t,r-l,b-t)
    return region


class Pet(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('宿傩 V5 原生隔离预览')
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint|Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.model = Model(); self.renderer = Renderer()
        self.size_px = 320; self.age = 10000; self.frozen = False
        self.demo = False; self.wait = 0
        self.pinned_x = None; self.pinned_y = None
        self.press = None; self.dragging = False
        self.drag_count = 0; self.render_ms = 0; self.frame_count = 0
        self.last = perf_counter(); self.render_frame()
        self.envelope = QRegion(0,0,self.width(),self.height())
        self.move(700,300)
        self.timer = QTimer(self); self.timer.setInterval(16); self.timer.timeout.connect(self.tick); self.timer.start()

    def render_frame(self):
        begin=perf_counter()
        im = self.renderer.render(self.model,self.model.state(),self.age,self.size_px,self.devicePixelRatioF())
        logical = (math.ceil(VIEW.width()*self.size_px/VIEW.height()),self.size_px)
        self.setFixedSize(*logical)
        self.frame = im; self.region = alpha_region(im)
        self.setMask(self.region)
        if self.isVisible(): self.move_visible(self.pos(),self.screen(),keep_pins=True)
        self.update(); self.frame_count+=1
        self.render_ms = (perf_counter()-begin)*1000

    def tick(self):
        now=perf_counter(); dt=(now-self.last)*1000; self.last=now
        self.advance_elapsed(dt)

    def advance_elapsed(self,dt):
        # Same frame cap as the approved requestAnimationFrame driver.
        dt=min(150,dt)
        if not self.frozen:
            before = self.model.state()
            self.model.tick(dt); self.age+=dt
            after=self.model.state()
            def draw_state(s):
                age=s['blinkAge']
                closure=.5-.5*math.cos(2*math.pi*age/240) if age is not None and age<240 else 0
                return (s['eye'],s['body'],closure)
            if draw_state(before)!=draw_state(after) or self.age-dt<220:
                self.render_frame()
            s=self.model.state()
            busy=s['moving'] or s['bodyAge']<s['bodyMs'] or (s['blinkAge'] is not None and s['blinkAge']<240) or self.age<220
            if self.demo and not busy:
                self.wait+=min(150,dt)
                if self.wait>=450: self.click_stage()

    def click_stage(self):
        self.frozen=False; self.model.next(); self.age=0; self.wait=0; self.last=perf_counter(); self.render_frame()

    def reset(self):
        self.model.run('s=Motion.initial()'); self.age=10000; self.frozen=False; self.demo=False; self.wait=0; self.render_frame()

    def snap(self,i,peak=False):
        self.reset(); self.model.run(f's.eye=s.body=s.target=Motion.bounds[{i}];s.stage={i}')
        self.age=110 if peak else 10000; self.frozen=True; self.render_frame()

    def select_mode(self,mode):
        self.tick(); self.frozen=False
        if mode=='always':
            self.demo=True
            s=self.model.state()
            busy=s['moving'] or s['bodyAge']<s['bodyMs'] or (s['blinkAge'] is not None and s['blinkAge']<240) or self.age<220
            if not busy: self.click_stage()
        else:
            # V5 auto is repeated next-stage actions, not Motion.mode('always').
            # Stop scheduling; the current head/eye/pulse transition finishes.
            self.demo=False

    def set_size(self,h):
        cx,bottom=self.x()+self.width()/2,self.y()+self.height()
        self.size_px=h; self.render_frame()
        self.move_visible(QPoint(round(cx-self.width()/2),round(bottom-self.height())),self.screen(),keep_pins=True)

    def paintEvent(self,event):
        p=QPainter(self); p.drawImage(QPoint(0,0),self.frame); p.end()

    def move_visible(self,destination,screen,keep_pins=False):
        # User-confirmed requirement: the visible character can touch an edge.
        # Transparent canvas may leave the work area. Remember only actual edge
        # contacts and follow those contacts as the silhouette animates.
        area=screen.availableGeometry()
        bounds=self.region.boundingRect()
        lo_x,hi_x=area.left()-bounds.left(),area.right()-bounds.right()
        lo_y,hi_y=area.top()-bounds.top(),area.bottom()-bounds.bottom()
        dx,dy=destination.x(),destination.y()
        if keep_pins:
            dx=lo_x if self.pinned_x=='left' else hi_x if self.pinned_x=='right' else dx
            dy=lo_y if self.pinned_y=='top' else hi_y if self.pinned_y=='bottom' else dy
        x=max(lo_x,min(dx,hi_x)); y=max(lo_y,min(dy,hi_y))
        self.pinned_x='left' if x==lo_x else 'right' if x==hi_x else None
        self.pinned_y='top' if y==lo_y else 'bottom' if y==hi_y else None
        if self.screen()!=screen: self.setScreen(screen)
        self.move(x,y)

    def mousePressEvent(self,e):
        if e.button()==Qt.MouseButton.LeftButton:
            self.press=(e.globalPosition().toPoint(),self.pos()); self.dragging=False
            e.accept()

    def mouseDoubleClickEvent(self,e): self.mousePressEvent(e)

    def mouseMoveEvent(self,e):
        if self.press:
            delta=e.globalPosition().toPoint()-self.press[0]
            if delta.manhattanLength()>=QApplication.startDragDistance(): self.dragging=True
            if self.dragging:
                screen=QApplication.screenAt(e.globalPosition().toPoint())
                if screen is None:
                    def distance(s):
                        r=s.geometry(); q=e.globalPosition().toPoint()
                        return max(r.left()-q.x(),0,q.x()-r.right())**2+max(r.top()-q.y(),0,q.y()-r.bottom())**2
                    screen=min(QApplication.screens(),key=distance)
                self.move_visible(self.press[1]+delta,screen)
        e.accept()

    def mouseReleaseEvent(self,e):
        if e.button()==Qt.MouseButton.LeftButton and self.press:
            self.mouseMoveEvent(e)
            if self.dragging: self.drag_count+=1
            else: self.click_stage()
            self.press=None; self.dragging=False; e.accept()

    def event(self,e):
        if hasattr(self,'press') and e.type() in (QEvent.Type.UngrabMouse,QEvent.Type.Hide): self.press=None
        if hasattr(self,'model') and e.type() in (QEvent.Type.DevicePixelRatioChange,QEvent.Type.ScreenChangeInternal):
            QTimer.singleShot(0,self.render_frame)
        return super().event(e)


class Panel(QWidget):
    def __init__(self,pet):
        super().__init__(); self.pet=pet
        self.setWindowTitle('V5 原生预览控制 · 可丢弃原型')
        layout=QVBoxLayout(self)
        layout.addWidget(QLabel('点击角色逐阶段推进；拖动角色移动。正式桌宠与设置均不受影响。'))
        row=QHBoxLayout(); layout.addLayout(row)
        for text,fn in [('下一阶段',pet.click_stage),('复位',pet.reset),('持续跳动（V5）',lambda:pet.select_mode('always')),('切回点击',lambda:pet.select_mode('click'))]:
            b=QPushButton(text); b.clicked.connect(fn); row.addWidget(b)
        row=QHBoxLayout(); layout.addLayout(row)
        for i in range(4):
            b=QPushButton(f'视线 {i}'); b.clicked.connect(lambda checked=False,i=i:pet.snap(i)); row.addWidget(b)
        b=QPushButton('回弹最强帧'); b.clicked.connect(lambda:pet.snap(pet.model.state()['stage'],True)); row.addWidget(b)
        row=QHBoxLayout(); layout.addLayout(row)
        for h in (188,271,320):
            b=QPushButton(f'{h}px'); b.clicked.connect(lambda checked=False,h=h:pet.set_size(h)); row.addWidget(b)
        b=QPushButton('快速五次'); b.clicked.connect(self.rapid); row.addWidget(b)
        row=QHBoxLayout(); layout.addLayout(row)
        for text,dx,dy in [('贴左边',-9999,None),('贴右边',9999,None),('贴上边',None,-9999),('贴下边',None,9999)]:
            b=QPushButton(text)
            b.clicked.connect(lambda checked=False,dx=dx,dy=dy:pet.move_visible(QPoint(pet.x() if dx is None else dx,pet.y() if dy is None else dy),pet.screen()))
            row.addWidget(b)
        self.status=QLabel(); self.status.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(self.status)
        b=QPushButton('退出隔离预览'); b.clicked.connect(QApplication.instance().quit); layout.addWidget(b)
        self.timer=QTimer(self); self.timer.setInterval(200); self.timer.timeout.connect(self.refresh); self.timer.start()
        self.move(120,120); self.refresh()

    def rapid(self):
        for ms in (0,45,90,135,180): QTimer.singleShot(ms,self.pet.click_stage)

    def refresh(self):
        s=self.pet.model.state()
        self.status.setText(f"模式 {'V5演示' if self.pet.demo else s['mode']} · 视线 {s['stage']} · 眼 {s['eye']%41:.2f} / 头 {s['body']%41:.2f}\n点击 {s['clicks']} · 眨眼 {s['blinks']} · 完整拖动 {self.pet.drag_count}\n角色档位 {self.pet.size_px}px · 画布 {self.pet.width()}×{self.pet.height()} DIP · DPR {self.pet.devicePixelRatioF():.2f}\n贴边 {self.pet.pinned_x or '—'} / {self.pet.pinned_y or '—'} · 绘制＋轮廓 {self.pet.render_ms:.1f}ms")


if __name__=='__main__':
    app=QApplication(sys.argv)
    app.setApplicationName('sukuna-v5-throwaway')
    pet=Pet(); panel=Panel(pet)
    pet.show(); panel.show()
    sys.exit(app.exec())
