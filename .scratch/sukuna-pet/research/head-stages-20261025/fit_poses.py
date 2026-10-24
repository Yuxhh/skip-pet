from pathlib import Path
import json, math
import numpy as np
from PIL import Image,ImageDraw
root=Path(__file__).parent
# Manually read fixed facial landmarks from the supplied images resized to
# 576x1280, cropped y=305..885. These are estimates, not automatic tracking.
# forehead hairline, outer left/right eye corners, nose, mouth ends, chin.
heads=np.array([
 [[302,169],[248,234],[365,223],[309,273],[281,308],[341,302],[304,332]],
 [[227,132],[188,212],[310,185],[250,235],[213,287],[304,268],[270,326]],
 [[260,151],[207,217],[341,218],[272,264],[236,305],[313,301],[275,337]],
 [[190,125],[153,215],[289,174],[222,243],[208,298],[291,274],[256,339]],
],dtype=float)
buttons=np.array([[[365,335],[421,456]],[[344,340],[404,463]],[[358,346],[411,482]],[[332,354],[399,497]]],dtype=float)
v0=buttons[0,1]-buttons[0,0];l0=np.linalg.norm(v0);a0=math.atan2(v0[1],v0[0])
rows=[];out=Image.new('RGB',(576*4,620),'#eee')
for i in range(4):
 v=buttons[i,1]-buttons[i,0];scale=l0/np.linalg.norm(v);a=a0-math.atan2(v[1],v[0])
 R=scale*np.array([[math.cos(a),-math.sin(a)],[math.sin(a),math.cos(a)]])
 t=buttons[0,0]-R@buttons[i,0]
 h=heads[i]@R.T+t
 X=np.c_[heads[0],np.ones(7)];fit=np.linalg.lstsq(X,h,rcond=None)[0]
 A=fit[:2].T;b=fit[2];pivot=heads[0,-1];shift=A@pivot+b-pivot
 rmse=float(np.sqrt(np.mean((X@fit-h)**2)))
 inv=np.linalg.inv(R);trans=-inv@t
 im=Image.open(root/f'key-{i}.jpg').transform((576,580),Image.Transform.AFFINE,(*inv[0],trans[0],*inv[1],trans[1]),Image.Resampling.BICUBIC)
 d=ImageDraw.Draw(im)
 for j,p in enumerate(h):
  x,y=p;d.ellipse((x-3,y-3,x+3,y+3),fill='#ffb65c');d.text((x+5,y),str(j),fill='white')
 for x,y in buttons[0]:d.ellipse((x-4,y-4,x+4,y+4),outline='#66ffff',width=2)
 out.paste(im,(i*576,40));ImageDraw.Draw(out).text((i*576+8,8),f'Stage {i} / body stabilized / RMSE {rmse:.1f}px',fill='black')
 rows.append({'stage':i,'body_normalization':{'scale':scale,'rotation_deg':math.degrees(a)},'head_landmarks_original':heads[i].tolist(),'head_landmarks_stabilized':h.tolist(),'affine':A.tolist(),'translation':b.tolist(),'chin_shift_reference_px':shift.tolist(),'fit_rmse_px':rmse})
out.save(root/'stabilized-keyframes.jpg',quality=94)
(root/'pose-fit.json').write_text(json.dumps({'method':'manual face landmarks; two coat buttons remove camera/body similarity; least-squares affine; stage0 reference','coordinate_system':'576x1280 screenshot, crop [0,305,576,885]','rows':rows},indent=2),encoding='utf-8')
print(json.dumps(rows,indent=2))
