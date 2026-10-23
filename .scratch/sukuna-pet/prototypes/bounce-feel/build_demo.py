"""THROWAWAY interaction evidence. Source video is read only. No generated pixels.
Build: python build_demo.py --workspace <original workspace> --cv-path <opencv dir>
"""
from pathlib import Path
import argparse, base64, hashlib, io, json, subprocess, sys
import numpy as np
from PIL import Image, ImageFilter

p=argparse.ArgumentParser()
p.add_argument('--workspace',type=Path,required=True)
a=p.parse_args()
root=Path(__file__).resolve().parent
source=Path(r'C:\Users\xing\xwechat_files\wxid_nh9m3kwg5q8b12_c2f1\msg\video\2026-10\76e9282daa42a701b537343bb5418979.mp4')
before=source.stat();digest=hashlib.sha256(source.read_bytes()).hexdigest()
ffmpeg=a.workspace/'.scratch/sukuna-pet/research/.tools/imageio_ffmpeg/binaries/ffmpeg-win-x86_64-v7.1.exe'
raw=subprocess.run([str(ffmpeg),'-hide_banner','-i',str(source),'-an','-f','rawvideo','-pix_fmt','rgb24','pipe:1'],capture_output=True,check=True).stdout
frames=np.frombuffer(raw,np.uint8).reshape(-1,1280,576,3)[:,415:865].copy()
previous=root.parent/'transparent-character'
ids=[0]+list(range(16,103))
seeds={i:np.array(Image.open(previous/'assets'/f'f{i:03d}-A.png'))[:,:,3] for i in (0,36,64)}
small={i:np.array(Image.fromarray(frames[i]).resize((144,112))).astype(np.float32).mean(axis=2) for i in range(103)}
def box(v,r):
    v=np.pad(v,((r,r),(r,r)),mode='edge')
    s=np.pad(v,((1,0),(1,0))).cumsum(0).cumsum(1)
    k=2*r+1
    return (s[k:,k:]-s[:-k,k:]-s[k:,:-k]+s[:-k,:-k])/(k*k)
def rough_mask(i,seed):
    # Quarter-resolution block matching; rough preview alpha only, no RGB warp.
    target=small[i]; reference=np.pad(small[seed],((16,16),(16,16)),mode='edge')
    best=np.full(target.shape,np.inf); ux=np.zeros(target.shape,np.float32);uy=ux.copy()
    for dy in range(-16,17,2):
        for dx in range(-16,17,2):
            cost=box(np.abs(target-reference[16+dy:128+dy,16+dx:160+dx]),4)+.018*(dx*dx+dy*dy)
            use=cost<best;best[use]=cost[use];ux[use]=dx;uy[use]=dy
    ux=box(ux,2);uy=box(uy,2)
    ux=np.array(Image.fromarray(ux).resize((576,450),Image.Resampling.BILINEAR))*4
    uy=np.array(Image.fromarray(uy).resize((576,450),Image.Resampling.BILINEAR))*(450/112)
    yy,xx=np.indices((450,576));xx=np.clip(np.rint(xx+ux).astype(int),0,575);yy=np.clip(np.rint(yy+uy).astype(int),0,449)
    return np.array(Image.fromarray(seeds[seed][yy,xx]).filter(ImageFilter.GaussianBlur(.5)))
alpha_sheet=Image.new('RGBA',(288*8,225*11))
source_sheet=Image.new('RGB',alpha_sheet.size)
records=[]
for slot,i in enumerate(ids):
    if i in seeds:
        mask=seeds[i].copy();seed=i
    else:
        seed=min(seeds,key=lambda j:np.abs(frames[i,60:260,180:405].astype(float)-frames[j,60:260,180:405]).mean())
        # Backward flow maps target pixels into a manually masked reference.
        mask=rough_mask(i,seed)
    mask[380:]=0
    rgba=np.dstack((frames[i],mask))
    assert np.array_equal(rgba[:,:,:3],frames[i])
    tile=Image.fromarray(rgba).resize((288,225),Image.Resampling.LANCZOS)
    alpha_sheet.paste(tile,((slot%8)*288,(slot//8)*225))
    source_sheet.paste(Image.fromarray(frames[i]).resize((288,225)),((slot%8)*288,(slot//8)*225))
    records.append({'frame':i,'mask_seed':seed,'alpha_method':'accepted static mask' if i in seeds else 'rough backward block-matching mask'})
def encoded(im,fmt,**kwargs):
    buf=io.BytesIO();im.save(buf,format=fmt,**kwargs)
    return 'data:image/'+('webp' if fmt=='WEBP' else 'png')+';base64,'+base64.b64encode(buf.getvalue()).decode()
data={'ids':ids,'character':encoded(alpha_sheet,'WEBP',lossless=True),'source':encoded(source_sheet,'WEBP',quality=92)}
template=(root/'demo.template.html').read_text(encoding='utf-8')
(root/'index.html').write_text(template.replace('/*__ASSETS__*/',json.dumps(data,separators=(',',':'))),encoding='utf-8')
manifest={'purpose':'throwaway HITL prototype; not accepted; not native desktop pet','source_sha256':digest,'source_bytes':before.st_size,'fps':24,'crop':[0,415,576,865],'alpha_cutoff_y':380,'frames':records,'candidate_ranges_inclusive':[[22,62],[32,72]],'cycle_seconds_candidate':41/24,'transition_ms_candidate':120,'settle_ms_candidate':160,'display_scale':0.5,'rgb_before_resizing_unchanged':True,'dynamic_masks':'rough block matching from nearest of accepted f0/f36/f64; not per-frame human-verified','simulated_only':['host task signals','work-area boundary','alpha hit testing'],'not_verified':['Windows topmost','native cross-app mouse pass-through','multi-monitor DPI','real host integration']}
after=source.stat();assert before.st_size==after.st_size and before.st_mtime_ns==after.st_mtime_ns
assert digest==hashlib.sha256(source.read_bytes()).hexdigest()
manifest['source_unchanged']=True
(root/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
alpha_sheet.resize((1152,1237)).save(root/'mask-overview.png')
print(json.dumps({'file':str(root/'index.html'),'bytes':(root/'index.html').stat().st_size,'frames':len(ids),'source_unchanged':True}))
