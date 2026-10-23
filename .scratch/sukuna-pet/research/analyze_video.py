"""Diagnostic analysis only; creates no transparent/production character assets.
Usage: python analyze_video.py --ffmpeg PATH [--source PATH] [--out DIR]
Requires numpy and Pillow. Frame numbers are zero-based decoded presentation order.
"""
from pathlib import Path
import argparse, csv, hashlib, json, subprocess, re
import sys
import numpy as np
from PIL import Image, ImageDraw

p=argparse.ArgumentParser()
p.add_argument('--ffmpeg', required=True)
p.add_argument('--source', default=r'C:\Users\xing\xwechat_files\wxid_nh9m3kwg5q8b12_c2f1\msg\video\2026-10\76e9282daa42a701b537343bb5418979.mp4')
p.add_argument('--out', default=str(Path(__file__).parent/'diagnostics'))
a=p.parse_args(); out=Path(a.out); out.mkdir(parents=True,exist_ok=True)
source=Path(a.source); before_stat=source.stat(); before=hashlib.sha256(source.read_bytes()).hexdigest()
proc=subprocess.run([a.ffmpeg,'-hide_banner','-i',str(source),'-an','-f','rawvideo','-pix_fmt','rgb24','pipe:1'],capture_output=True,check=True)
frames=np.frombuffer(proc.stdout,dtype=np.uint8).reshape(-1,1280,576,3)
(out/'decode-log.txt').write_text(proc.stderr.decode('utf-8',errors='replace'),encoding='utf-8')
probe=subprocess.run([a.ffmpeg,'-hide_banner','-i',str(source),'-vf','showinfo','-an','-f','null','-'],capture_output=True,check=True)
pts=re.findall(r'\bn:\s*(\d+)\s+pts:\s*(-?\d+)\s+pts_time:([\d.]+)',probe.stderr.decode('utf-8',errors='replace'))
with (out/'presentation-times.csv').open('w',newline='',encoding='utf-8') as f:
    w=csv.writer(f);w.writerow(['frame','pts','pts_time_seconds']);w.writerows(pts)
# All 156 active-image crops at half source resolution; no silhouette extraction.
for start in range(0,len(frames),40):
    canvas=Image.new('RGB',(288*8,249*5),(35,35,35)); d=ImageDraw.Draw(canvas)
    for k,i in enumerate(range(start,min(start+40,len(frames)))):
        x=(k%8)*288;y=(k//8)*249
        im=Image.fromarray(frames[i]).crop((0,415,576,865)).resize((288,225))
        canvas.paste(im,(x,y+24)); d.text((x+4,y+5),f'f{i:03d}  {i/24:.4f}s',fill='white')
    canvas.save(out/f'all-frames-{start:03d}-{min(start+39,len(frames)-1):03d}.jpg',quality=95)
# Whole recording samples retain black bars and UI as evidence.
ids=[0,24,48,72,96,120,155]; canvas=Image.new('RGB',(2304,664),'#222222'); d=ImageDraw.Draw(canvas)
for k,i in enumerate(ids):
    canvas.paste(Image.fromarray(frames[i]).resize((288,640)),(k*288,24)); d.text((k*288+4,5),f'f{i}',fill='white')
canvas.save(out/'whole-frame-samples.jpg',quality=95)
# Fixed head/face region avoids the watermark and lower image cut.
regions={'head':(160,450,410,730),'face':(210,530,355,670),'active':(0,415,576,865)}
lagrows=[]
for name,(x0,y0,x1,y1) in regions.items():
    r=frames[:,y0:y1:2,x0:x1:2].astype(np.float32)
    for lag in range(1,121):
        dif=np.abs(r[lag:]-r[:-lag]).mean(axis=(1,2,3))
        lagrows.append({'region':name,'lag_frames':lag,'seconds':lag/24,'mean_MAE_0_255':float(dif.mean()),'median_MAE_0_255':float(np.median(dif)),'pair_count':len(dif)})
with (out/'lag-errors.csv').open('w',newline='',encoding='utf-8') as f:
    w=csv.DictWriter(f,fieldnames=list(lagrows[0]));w.writeheader();w.writerows(lagrows)
# Bright face pixels as a limited proxy for pose translation. Fixed ROI explicitly
# excludes most bright background; inspect crops before interpreting this signal.
rows=[]
for i,fr in enumerate(frames):
    crop=fr[500:680,205:360].astype(float); gray=crop.mean(axis=2)
    yy,xx=np.where(gray>150)
    rows.append({'frame':i,'seconds':i/24,'face_bright_x':float(xx.mean()+205),'face_bright_y':float(yy.mean()+500),'bright_count':len(xx)})
with (out/'face-proxy.csv').open('w',newline='',encoding='utf-8') as f:
    w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
after=hashlib.sha256(source.read_bytes()).hexdigest()
pairrows=[]
r=frames[:,450:730:2,160:410:2].astype(np.float32)
for lag in range(8,65):
    # Only pairs wholly inside moving material, preceding the closing crossfade.
    starts=range(16,103-lag)
    vals=[float(np.abs(r[i+lag]-r[i]).mean()) for i in starts]
    if vals: pairrows.append({'lag_frames':lag,'seconds':lag/24,'mean_head_MAE':float(np.mean(vals)),'pairs':len(vals)})
with (out/'moving-lag-errors.csv').open('w',newline='',encoding='utf-8') as f:
    w=csv.DictWriter(f,fieldnames=list(pairrows[0]));w.writeheader();w.writerows(pairrows)
print('moving-material best lags',sorted(pairrows,key=lambda r:r['mean_head_MAE'])[:15])
pairids=[(16,56),(20,60),(24,64),(28,68),(32,72),(36,76),(40,80),(44,84),(48,88),(52,92),(56,96),(60,100)]
canvas=Image.new('RGB',(576*4,474*6),'#222222');d=ImageDraw.Draw(canvas)
for k,pair in enumerate(pairids):
    for j,i in enumerate(pair):
        x=(k%2)*1152+j*576;y=(k//2)*474
        canvas.paste(Image.fromarray(frames[i]).crop((0,415,576,865)),(x,y+24));d.text((x+4,y+5),f'f{i}  {i/24:.4f}s',fill='white')
canvas.save(out/'forty-frame-comparison.jpg',quality=95)
ids=[0,15,16,20,24,32,36,40,50,51,52,56,62,63,64,100,102,103,104,106,108,110,155]
for i in ids:
    Image.fromarray(frames[i]).crop((0,415,576,865)).save(out/f'spot-{i:03d}.png')
import PIL
summary={'source':str(source),'source_bytes':source.stat().st_size,'source_mtime_ns':source.stat().st_mtime_ns,'size_unchanged':before_stat.st_size==source.stat().st_size,'mtime_unchanged':before_stat.st_mtime_ns==source.stat().st_mtime_ns,'sha256_before':before,'sha256_after':after,'frame_count':len(frames),'fps':24,'frame_indexing':'zero-based','active_diagnostic_crop_xyxy':[0,415,576,865],'regions_xyxy':regions,'python':sys.version,'numpy':np.__version__,'pillow':PIL.__version__}
(out/'summary.json').write_text(json.dumps(summary,indent=2,ensure_ascii=False),encoding='utf-8')
print(json.dumps(summary,ensure_ascii=False))
for name in regions:
    rs=[r for r in lagrows if r['region']==name and r['lag_frames']>=8]
    print(name,sorted(rs,key=lambda r:r['mean_MAE_0_255'])[:12])
# Candidate 41-frame passage: f22..62, boundary f62->22. Not a loop asset.
ids=[20,21,22,23,60,61,62,63,64,65,31,32,72,73,40,41,80,81,50,51,90,91]
canvas=Image.new('RGB',(576*4,474*6),'#222222');d=ImageDraw.Draw(canvas)
for k,i in enumerate(ids):
    x=(k%4)*576;y=(k//4)*474
    canvas.paste(Image.fromarray(frames[i]).crop((0,415,576,865)),(x,y+24));d.text((x+4,y+5),f'f{i}  {i/24:.4f}s',fill='white')
canvas.save(out/'phase-and-boundary-comparison.jpg',quality=95)
edgepairs=[(61,62),(62,63),(63,64),(21,22),(22,23),(62,22),(63,23),(0,155),(15,16),(109,110),(31,32),(32,33),(71,72),(72,73),(73,74),(72,32),(73,32)]
edgerows=[]
for i,j in edgepairs:
    edgerows.append({'metric_type':'frame_pixel_difference','from':i,'to':j,'head_MAE':float(np.abs(r[j]-r[i]).mean())})
# Finite difference velocity in RGB space: ||(next-current)-(current-prev)||.
for prev,cur,nxt in [(61,62,63),(61,62,22),(62,22,23),(21,22,23),(62,63,64),(71,72,73),(71,72,32),(72,32,33)]:
    edgerows.append({'metric_type':'temporal_difference_change','from':f'{prev},{cur}','to':f'{cur},{nxt}','head_MAE':float(np.abs((r[nxt]-r[cur])-(r[cur]-r[prev])).mean())})
with (out/'boundary-errors.csv').open('w',newline='',encoding='utf-8') as f:
    w=csv.DictWriter(f,fieldnames=list(edgerows[0]));w.writeheader();w.writerows(edgerows)
print('edges',edgerows)
pairrows=[]
for lag in [20,21,40,41,42,44]:
    for i in range(16,103-lag):
        pairrows.append({'from':i,'to':i+lag,'lag':lag,'head_MAE':float(np.abs(r[i+lag]-r[i]).mean())})
with (out/'per-pair-errors.csv').open('w',newline='',encoding='utf-8') as f:
    w=csv.DictWriter(f,fieldnames=list(pairrows[0]));w.writeheader();w.writerows(pairrows)
# Plot without an extra plotting dependency; colors denote full vs moving scan.
can=Image.new('RGB',(1000,460),'white');d=ImageDraw.Draw(can)
d.text((35,12),'Mean RGB head-region MAE vs lag (pixel scale 0..255); lower is closer',fill='black')
for lag in range(0,121,10):
    x=60+lag*7.2;d.line((x,50,x,400),fill='#dddddd');d.text((x-8,410),str(lag),fill='black')
for val in range(0,71,10):
    y=400-val*5;d.line((60,y,924,y),fill='#dddddd');d.text((25,y-5),str(val),fill='black')
full=[r0 for r0 in lagrows if r0['region']=='head']
moving=[]
with (out/'moving-lag-errors.csv').open(encoding='utf-8') as f:
    moving=list(csv.DictReader(f))
d.line([(60+r0['lag_frames']*7.2,400-r0['mean_MAE_0_255']*5) for r0 in full],fill='#777777',width=2)
d.line([(60+int(r0['lag_frames'])*7.2,400-float(r0['mean_head_MAE'])*5) for r0 in moving],fill='#0077cc',width=3)
d.text((620,28),'gray: all frames; blue: f16..102',fill='black');d.text((430,437),'lag (frames at 24 fps)',fill='black')
can.save(out/'recurrence-plot.png')
