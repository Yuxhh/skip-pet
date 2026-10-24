from pathlib import Path
from PIL import Image, ImageDraw
import numpy as np
import json, hashlib
root=Path(__file__).parent
frames=np.fromfile(root/'frames.rgb',dtype=np.uint8).reshape(-1,1280,576,3)
folder=Path('C:/Users/xing/xwechat_files/wxid_nh9m3kwg5q8b12_c2f1/temp/RWTemp/2026-10/2deeae0a3d59df6882cf0e266551d6c1')
files=['ad4db39030f59fdc42582ecd984ca557.jpg','aa9e00dd9f025394953c0e2e64254620.jpg','f61d5bcc935e81725882fc3d3ff2ce95.jpg','11118587af6c856bb9eeba40a35a23d3.jpg']
sheet=Image.new('RGB',(576*4,620),'#ddd')
meta=[]
for i,f in enumerate(files):
    im=Image.open(folder/f).convert('RGB').resize((576,1280))
    crop=im.crop((0,305,576,885))
    sheet.paste(crop,(i*576,40));ImageDraw.Draw(sheet).text((i*576+10,8),f'Stage {i} / user keyframe',fill='black')
    crop.save(root/f'key-{i}.jpg',quality=95)
    # Nearest entire-video crop for context, no geometric assumption.
    a=np.asarray(im)[320:880,30:550].astype(float)[::4,::4]
    errs=[np.mean((a-fr[320:880,30:550][::4,::4].astype(float))**2) for fr in frames]
    n=int(np.argmin(errs));meta.append({'stage':i,'screenshot':str(folder/f),'nearest_frame':n,'time_s':n/24,'mse':errs[n]})
sheet.save(root/'user-keyframes.jpg',quality=93)
contact=Image.new('RGB',(240*8,260*4),'#eee');d=ImageDraw.Draw(contact)
for j,n in enumerate(range(0,len(frames),3)):
    tile=Image.fromarray(frames[n]).crop((0,305,576,885)).resize((240,242))
    x=j%8*240;y=j//8*260;contact.paste(tile,(x,y+18));d.text((x+4,y+2),f'f{n:03} {n/24:.3f}s',fill='black')
contact.save(root/'video-contact.jpg',quality=92)
(root/'keyframe-matches.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(meta,ensure_ascii=False))
