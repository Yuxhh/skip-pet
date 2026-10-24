"""Pack the stage prototype; does not redraw or modify generated image pixels."""
from pathlib import Path
import base64,csv,json,re,hashlib,argparse
from PIL import Image

p=argparse.ArgumentParser();p.add_argument('--workspace',type=Path,required=True);a=p.parse_args()
root=Path(__file__).resolve().parent
old=(root/'index.html').read_text(encoding='utf-8-sig')
assets=json.loads(re.search(r'<script id="assets" type="application/json">(.*?)</script>',old,re.S).group(1))
image=root/'assets/sukuna-eye-base-v3.png'
assets['redrawn']='data:image/png;base64,'+base64.b64encode(image.read_bytes()).decode()
im=Image.open(image);assets['redrawnBounds']=im.getchannel('A').point(lambda v:255 if v>16 else 0).getbbox()
rows=list(csv.DictReader((a.workspace/'.scratch/sukuna-pet/research/diagnostics/face-proxy.csv').open()))
base=rows[22];bx=float(base['face_bright_x']);by=float(base['face_bright_y']);bc=float(base['bright_count'])
angles={22:0,29:-1,32:-4,35:-12,37:-12,42:-10,46:-8,49:-6,51:-3,53:-5,56:-4,58:-1,61:1,63:0}
def angle(i):
    ks=sorted(angles)
    lo=max(k for k in ks if k<=i);hi=min(k for k in ks if k>=i)
    return angles[lo] if hi==lo else angles[lo]+(angles[hi]-angles[lo])*(i-lo)/(hi-lo)
poses=[]
for i in range(22,64):
    r=rows[i];x=(float(r['face_bright_x'])-bx)*.65;y=(float(r['face_bright_y'])-by)*.65
    scale=1+((float(r['bright_count'])/bc)**.5-1)*.24
    value=[x,y,angle(i),scale]
    if i>=59:
        # Close only the redraw's transform track without alpha crossfading.
        w=(63-i)/4;value=[x*w,y*w,angle(i)*w,1+(scale-1)*w]
    poses.append(value)
assets['poses']=poses
assets['boundaries']=[0,13,24,34,41]
assets['sourceStart']=22
assets['eyeKeys']=[[0,0,0],[8,-10,-5],[13,-20,-9],[20,-28,-8],[24,-29,-7],[27,-27,-6],[31,-20,3],[34,-15,7],[38,-5,6],[41,0,0]]
assets['eyeCrops']=[[ (float(rows[i]['face_bright_x'])-16-85)/2,(float(rows[i]['face_bright_y'])-30-415)/2,85,30] for i in range(22,64)]
html=(root/'stage.template.html').read_text(encoding='utf-8')
(root/'index.html').write_text(html.replace('/*__ASSETS__*/',json.dumps(assets,separators=(',',':'))),encoding='utf-8')
manifest={'version':3,'user_confirmed':['click advances one eye-direction stage','play short eye-turn to next stage','hold that stage until next click','eye directions follow source video order','redraw authorized due to rough edges'],
 'candidate_boundaries_source_frames':[22,35,46,56,63],'candidate_fps':24,'candidate_total_seconds':41/24,
 'redrawn_asset':'assets/sukuna-eye-base-v3.png','asset_sha256':hashlib.sha256(image.read_bytes()).hexdigest(),'image_mode':im.mode,'alpha_extrema':im.getchannel('A').getextrema(),'draw_bounds':assets['redrawnBounds'],
 'method':'built-in imagegen redraw and blank-sclera edit; clipped Canvas irises; offsets manually estimated from f22-f63 eye detail contact; source order, not a prescribed cardinal-direction loop; optional auxiliary body motion is off by default',
 'not_equivalent_to':'source pixel animation or exact reconstructed source pose',
 'rapid_click_candidate':'replace forward stage target; at most one cycle of forward travel remains, no unbounded multi-cycle queue',
 'automatic_modes':'existing simulated comparison; click precedence still candidate',
 'eye_offset_status':'manual interpretation of compressed source; eye opening and exact gaze extrema require human side-by-side validation',
 'blink':'once on crossing into stage 3; 240ms close/open; no repeat during hold',
 'acceptance':'pending human feedback; old whole-cycle-per-click and body-only stage prototypes rejected'}
(root/'stage-manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'version':3,'html_bytes':(root/'index.html').stat().st_size,'bounds':assets['redrawnBounds'],'poses':len(poses)}))
